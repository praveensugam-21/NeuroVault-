import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base

# Import all models to ensure they are registered with the engine Base metadata
from app.models import User, Document, DocumentTag, Entity, GraphEdge, AuditLog

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="IRIS — Intelligent Retrieval and Information System",
    description="Production-grade secure personal document intelligence platform. Classify, extract, search, and query your documents with full privacy.",
    version="2.0.0"
)

# ── Configurable CORS ────────────────────────────────────────────────────────
# In production, restrict ALLOWED_ORIGINS in your .env to your actual frontend domain.
_allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:80",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"http://192\.168\..+",  # Allow local network IPs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Security Headers Middleware ──────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# ── Register API Routers ─────────────────────────────────────────────────────
from app.routers import auth, documents, chat, graph, dashboard, digest

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(dashboard.router)
app.include_router(digest.router)


def run_auto_migration():
    import time
    import logging
    from app.database import SessionLocal
    from app.models.document import Document
    from app.services.embedding_service import get_chroma_collection, EmbeddingService
    from app.services.encryption_service import EncryptionService
    
    # Wait a few seconds for startup components to initialize
    time.sleep(5)
    logger = logging.getLogger("iris.migration")
    logger.info("[Migration] Checking RAG vector index formatting...")
    
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.status == "COMPLETE").all()
        collection = get_chroma_collection()
        if collection is None:
            logger.warning("[Migration] ChromaDB unavailable. Skipping migration check.")
            return

        reindexed_count = 0
        for doc in docs:
            # Query if doc is indexed at the chunk level
            try:
                res = collection.get(where={"document_id": doc.id})
                has_chunks = len(res.get("ids", [])) > 0
            except Exception:
                has_chunks = False

            if not has_chunks:
                logger.info(f"[Migration] Legacy index detected for '{doc.name}' (ID: {doc.id}). Rebuilding...")
                ocr_text = ""
                try:
                    if doc.file_path and os.path.exists(doc.file_path):
                        if doc.file_type.upper() == "AUDIO":
                            from app.services.voice_service import VoiceService
                            ocr_text = VoiceService.transcribe_audio(doc.file_path)
                        else:
                            from app.services.ocr_service import OCRService
                            ocr_text = OCRService.extract_text_from_file(doc.file_path, doc.file_type)

                    decrypted_json_str = "{}"
                    if doc.extracted_json:
                        try:
                            decrypted_json_str = EncryptionService.decrypt(doc.extracted_json)
                        except Exception:
                            pass

                    # Build chunk-level indexing
                    indexed = EmbeddingService.add_document_chunks(
                        document_id=doc.id,
                        user_id=doc.user_id,
                        full_text=f"Summary: {doc.summary}\nContent:\n{ocr_text}\nMetadata details:\n{decrypted_json_str}",
                        category=doc.category,
                        doc_type=doc.document_type
                    )
                    if indexed:
                        reindexed_count += 1
                except Exception as e:
                    logger.error(f"[Migration] Auto-reindexing failed for {doc.id}: {e}")

        if reindexed_count > 0:
            logger.info(f"[Migration] Finished! Re-indexed {reindexed_count} documents to semantic chunk vectors.")
    except Exception as e:
        logger.error(f"[Migration] Verification run failed: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    import threading
    # Pre-load EasyOCR in a background thread to prevent first-run delay
    if settings.ENABLE_LOCAL_OCR:
        from app.services.ocr_service import get_easyocr_reader
        threading.Thread(target=get_easyocr_reader, daemon=True).start()

    # Pre-load spaCy NER in a background thread
    from app.services.document_processor import get_spacy_nlp
    threading.Thread(target=get_spacy_nlp, daemon=True).start()

    # Pre-load SentenceTransformer in a background thread to prevent first-upload index lag
    from app.services.embedding_service import get_embedding_model
    threading.Thread(target=get_embedding_model, daemon=True).start()
    
    # Run auto-migration in a daemon thread
    threading.Thread(target=run_auto_migration, daemon=True).start()


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "IRIS — Intelligent Retrieval and Information System",
        "version": "2.0.0",
        "mode": settings.ENV_MODE
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "IRIS"}
