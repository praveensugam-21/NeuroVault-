import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query, BackgroundTasks, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentTag
from app.models.audit_log import AuditLog
from app.schemas.document import DocumentResponse, DocumentBriefResponse
from app.services.security import SecurityService
from app.services.embedding_service import EmbeddingService
from app.pipeline.processing_queue import DocumentPipelineManager
from app.config import settings
from typing import List, Optional
import logging

logger = logging.getLogger("iris.documents")

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# ── Upload Validation Constants ─────────────────────────────────────────────
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".mp3", ".wav", ".m4a"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/webp",
    "text/plain",
    "audio/mpeg", "audio/wav", "audio/mp4", "audio/x-m4a",
}


def _detect_file_type(content_type: str, ext: str) -> str:
    """Determine the internal file type category."""
    content_type = content_type or ""
    ext = ext.lower()
    if "pdf" in content_type or ext == ".pdf":
        return "pdf"
    elif "audio" in content_type or ext in {".mp3", ".wav", ".m4a"}:
        return "audio"
    elif "image" in content_type or ext in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image"
    return "text"


def _sanitize_name(name: str) -> str:
    """Strip dangerous characters from document names."""
    import re
    clean = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "", name).strip()
    return clean[:255] if clean else "Untitled Document"


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts document uploads (PDF, image, audio, text).
    Validates file type, size, and MIME type before accepting.
    Creates DB record in PROCESSING state and starts async pipeline.
    """
    # ─ Filename / Extension validation
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required."
        )

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file_ext}' is not supported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # ─ MIME type validation
    content_type = (file.content_type or "").split(";")[0].strip()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Upload rejected: unsupported MIME type '{content_type}' for file '{file.filename}'")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"MIME type '{content_type}' is not accepted."
        )

    # ─ Read file and enforce size limit
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {MAX_FILE_SIZE_MB} MB."
        )
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # ─ Determine file type and sanitize document name
    file_type = _detect_file_type(content_type, file_ext)
    raw_name = name or os.path.splitext(file.filename)[0]
    doc_name = _sanitize_name(raw_name)

    # ─ Save to uploads directory with UUID filename
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    dest_path = os.path.join(settings.UPLOADS_DIR, safe_filename)

    try:
        with open(dest_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file."
        )

    # ─ Create initial DB record
    db_doc = Document(
        name=doc_name,
        file_path=dest_path,
        file_type=file_type,
        user_id=current_user.id,
        status="PROCESSING"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # ─ Audit log
    audit = AuditLog(user_id=current_user.id, document_id=db_doc.id, action="UPLOAD")
    db.add(audit)
    db.commit()

    # ─ Enqueue async processing via FastAPI BackgroundTasks
    background_tasks.add_task(
        DocumentPipelineManager.run_pipeline,
        db_doc.id,
        current_user.id
    )

    logger.info(f"Document '{doc_name}' (ID: {db_doc.id}) queued for processing by user {current_user.id}")

    return {
        "message": "Document uploaded and queued for intelligent processing.",
        "document_id": db_doc.id,
        "status": "PROCESSING"
    }


@router.get("/", response_model=List[DocumentBriefResponse])
def list_documents(
    category: Optional[str] = Query(None, description="Filter documents by category folder"),
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all documents belonging to the authenticated user."""
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if category:
        query = query.filter(Document.category == category)
    return query.order_by(Document.created_at.desc()).all()


@router.get("/{id}", response_model=DocumentResponse)
def get_document(
    id: str,
    pin: Optional[str] = Query(None, description="Secondary PIN to unlock document fields"),
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves document detail. If locked, requires valid PIN to view extracted fields.
    """
    doc = db.query(Document).filter(
        Document.id == id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Audit log
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="VIEW")
    db.add(audit)
    db.commit()

    if doc.is_locked:
        if not pin:
            return DocumentResponse(
                id=doc.id,
                name=doc.name,
                file_type=doc.file_type,
                category=doc.category,
                document_type=doc.document_type,
                confidence_score=doc.confidence_score,
                status=doc.status,
                extracted_json={"message": "Document is locked. Enter your security PIN to view details."},
                summary="[LOCKED] Authenticate with your security PIN to view the document summary.",
                is_locked=True,
                created_at=doc.created_at,
                tags=doc.tags
            )
        if not current_user.pin_hash or not SecurityService.verify_password(pin, current_user.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect security PIN."
            )

    return doc


@router.post("/{id}/lock", status_code=status.HTTP_200_OK)
def lock_document(
    id: str,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """Locks a document behind the secondary security PIN."""
    if not current_user.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please configure a security PIN in Settings before locking documents."
        )
    doc = db.query(Document).filter(
        Document.id == id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc.is_locked = True
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="LOCK")
    db.add(audit)
    db.commit()
    return {"message": "Document locked successfully."}


@router.post("/{id}/unlock", status_code=status.HTTP_200_OK)
def unlock_document(
    id: str,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """Removes the PIN lock on a document."""
    doc = db.query(Document).filter(
        Document.id == id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc.is_locked = False
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="UNLOCK")
    db.add(audit)
    db.commit()
    return {"message": "Document unlocked."}


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_document(
    id: str,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes a document from disk, relational DB, and vector DB.
    """
    doc = db.query(Document).filter(
        Document.id == id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # 1. Delete physical file
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Could not remove file {doc.file_path}: {e}")

    # 2. Remove from vector store
    EmbeddingService.delete_document(doc.id)

    # 3. Audit log before deletion
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="DELETE")
    db.add(audit)

    # 4. Delete from database (cascades to tags, entities, graph edges)
    db.delete(doc)
    db.commit()

    logger.info(f"Document {id} permanently deleted by user {current_user.id}")
    return {"message": "Document and all associated data permanently deleted."}


@router.delete("/", status_code=status.HTTP_200_OK)
def wipe_vault(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes all documents, vector embeddings, graph nodes,
    and associated tags for the authenticated user in a single request.
    """
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    for doc in docs:
        # 1. Delete physical file
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.warning(f"Could not remove file {doc.file_path} during wipe: {e}")

        # 2. Remove from vector store
        try:
            EmbeddingService.delete_document(doc.id)
        except Exception as e:
            logger.warning(f"Could not delete embedding for {doc.id} during wipe: {e}")

        # 3. Delete DB record (cascades to tags, entities, graph edges)
        db.delete(doc)

    # 4. Audit log
    audit = AuditLog(user_id=current_user.id, action="WIPE_VAULT")
    db.add(audit)
    db.commit()

    logger.info(f"All documents permanently wiped for user {current_user.id}")
    return {"message": "Vault successfully wiped."}


def get_current_user_flexible(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> User:
    token_str = None
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ")[1]
    elif token:
        token_str = token

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from jose import jwt, JWTError
        payload = jwt.decode(
            token_str, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "access":
            raise JWTError()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.get("/{id}/file")
def get_document_file(
    id: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    Serves the original uploaded file for viewing or download.
    Supports JWT authorization from either headers or query parameter token.
    """
    from fastapi.responses import FileResponse
    import mimetypes

    doc = db.query(Document).filter(
        Document.id == id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file not found on server.")

    mime_type, _ = mimetypes.guess_type(doc.file_path)
    original_ext = os.path.splitext(doc.file_path)[1]
    filename = f"{doc.name}{original_ext}"

    # Audit log
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="DOWNLOAD_FILE")
    db.add(audit)
    db.commit()

    return FileResponse(
        path=doc.file_path,
        media_type=mime_type or "application/octet-stream",
        filename=filename
    )


