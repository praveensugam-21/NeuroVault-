import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
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

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts document uploads (PDF, image, audio, text).
    Creates DB record in PROCESSING state and starts async pipeline.
    """
    # Create unique local filename
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    doc_name = name or os.path.splitext(file.filename)[0]
    
    # Simple guess of broad file type
    content_type = file.content_type or ""
    if "pdf" in content_type or file_ext.lower() == ".pdf":
        file_type = "pdf"
    elif "audio" in content_type or file_ext.lower() in [".mp3", ".wav", ".m4a"]:
        file_type = "audio"
    elif "image" in content_type or file_ext.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
        file_type = "image"
    else:
        file_type = "text"

    # Save file to uploads folder
    import uuid
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    dest_path = os.path.join(settings.UPLOADS_DIR, safe_filename)
    
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Write initial DB entry
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

    # Log action
    audit = AuditLog(user_id=current_user.id, document_id=db_doc.id, action="UPLOAD")
    db.add(audit)
    db.commit()

    # Trigger async pipeline processing manager
    DocumentPipelineManager.enqueue_document_processing(db_doc.id, current_user.id)

    return {
        "message": "Document uploaded and queued for semantic processing.",
        "document_id": db_doc.id,
        "status": "PROCESSING"
    }

@router.get("/", response_model=List[DocumentBriefResponse])
def list_documents(
    category: Optional[str] = Query(None, description="Filter documents by category folder"),
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all documents belonging to the user. Supports category filtering.
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if category:
        query = query.filter(Document.category == category)
    return query.all()

@router.get("/{id}", response_model=DocumentResponse)
def get_document(
    id: str,
    pin: Optional[str] = Query(None, description="Optional PIN validation to unlock document fields"),
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed document record. If the document is locked:
    - If correct PIN is provided, returns unlocked data.
    - If correct PIN is missing/incorrect, returns document metadata but hides extracted JSON contents.
    """
    doc = db.query(Document).filter(Document.id == id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Log access attempt
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="VIEW")
    db.add(audit)
    db.commit()

    # Handle locked document checks
    if doc.is_locked:
        if not pin:
            # Hide sensitive JSON contents
            unlocked_doc = DocumentResponse(
                id=doc.id,
                name=doc.name,
                file_type=doc.file_type,
                category=doc.category,
                document_type=doc.document_type,
                confidence_score=doc.confidence_score,
                status=doc.status,
                extracted_json={"message": "Document is locked. Please enter your secondary PIN to view sensitive details."},
                summary="[LOCKED] Authenticate with your security PIN to view the document summary.",
                is_locked=True,
                created_at=doc.created_at,
                tags=doc.tags
            )
            return unlocked_doc
            
        # Verify PIN
        if not current_user.pin_hash or not SecurityService.verify_password(pin, current_user.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect security PIN. Access denied."
            )

    return doc

@router.post("/{id}/lock", status_code=status.HTTP_200_OK)
def lock_document(
    id: str,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Locks a document. Requires that the user has configured a security PIN.
    """
    if not current_user.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set up a security PIN in account settings first."
        )
        
    doc = db.query(Document).filter(Document.id == id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    doc.is_locked = True
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="LOCK")
    db.add(audit)
    db.commit()
    return {"message": "Document successfully locked."}

@router.post("/{id}/unlock", status_code=status.HTTP_200_OK)
def unlock_document(
    id: str,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Removes PIN lock on a document.
    """
    doc = db.query(Document).filter(Document.id == id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    doc.is_locked = False
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="UNLOCK")
    db.add(audit)
    db.commit()
    return {"message": "Document PIN lock disabled."}

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_document(
    id: str,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes a document from:
    1. Local disk storage
    2. Relational database
    3. ChromaDB vector database
    """
    doc = db.query(Document).filter(Document.id == id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # 1. Delete file on disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            # Log disk delete failure, but continue
            pass

    # 2. Delete index in vector database
    EmbeddingService.delete_document(doc.id)

    # 3. Log audit action
    audit = AuditLog(user_id=current_user.id, document_id=doc.id, action="DELETE")
    db.add(audit)

    # 4. Remove relational database entries
    db.delete(doc)
    db.commit()

    return {"message": "Document and all semantic memories permanently purged."}
