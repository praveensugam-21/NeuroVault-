import os
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("iris.main")

# Import all models to ensure they are registered with the engine Base metadata
from app.models import User, Document, DocumentTag, Entity, GraphEdge, AuditLog


# ── Database Setup & Migrations ──────────────────────────────────────────────

def run_schema_setup():
    """Create all tables and apply column migrations."""
    # Create tables that don't exist yet
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("users")]
    with engine.begin() as conn:
        if "oauth_provider" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50) DEFAULT 'local'"))
            logger.info("[Migration] Added oauth_provider column to users table.")
        if "oauth_id" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN oauth_id VARCHAR(255)"))
            logger.info("[Migration] Added oauth_id column to users table.")

        # Make hashed_password nullable in PostgreSQL
        db_type = "sqlite" if "sqlite" in str(engine.url) else "postgres"
        if db_type == "postgres":
            for col in inspector.get_columns("users"):
                if col["name"] == "hashed_password" and not col.get("nullable", True):
                    conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL"))
                    logger.info("[Migration] Made hashed_password nullable in PostgreSQL.")


def run_vector_index_migration():
    """Background task: Re-index any legacy documents missing chunk-level embeddings."""
    import time
    from app.database import SessionLocal
    from app.models.document import Document as DocModel
    from app.services.embedding_service import get_chroma_collection, EmbeddingService

    time.sleep(8)  # Allow services to initialise first
    logger.info("[VectorMigration] Checking RAG vector index formatting...")
    db = SessionLocal()
    try:
        docs = db.query(DocModel).filter(DocModel.status == "COMPLETE").all()
        collection = get_chroma_collection()
        if collection is None:
            logger.warning("[VectorMigration] ChromaDB unavailable. Skipping.")
            return

        reindexed = 0
        for doc in docs:
            try:
                res = collection.get(where={"document_id": doc.id})
                if len(res.get("ids", [])) > 0:
                    continue
            except Exception:
                pass

            logger.info(f"[VectorMigration] Re-indexing '{doc.name}' (ID: {doc.id})")
            try:
                if doc.file_path and os.path.exists(doc.file_path):
                    if doc.file_type.upper() == "AUDIO":
                        from app.services.voice_service import VoiceService
                        ocr_text = VoiceService.transcribe_audio(doc.file_path)
                    else:
                        from app.services.ocr_service import OCRService
                        ocr_text = OCRService.extract_text_from_file(doc.file_path, doc.file_type)
                else:
                    ocr_text = ""

                import json
                fields = doc.get_extracted_fields()
                fields_str = json.dumps(fields) if fields else "{}"
                indexed = EmbeddingService.add_document_chunks(
                    document_id=doc.id,
                    user_id=doc.user_id,
                    full_text=f"Summary: {doc.summary}\nContent:\n{ocr_text}\nMetadata:\n{fields_str}",
                    category=doc.category,
                    doc_type=doc.document_type,
                    extracted_fields=fields
                )
                if indexed:
                    reindexed += 1
            except Exception as e:
                logger.error(f"[VectorMigration] Failed for {doc.id}: {e}")

        if reindexed > 0:
            logger.info(f"[VectorMigration] Re-indexed {reindexed} documents.")
    except Exception as e:
        logger.error(f"[VectorMigration] Run failed: {e}")
    finally:
        db.close()


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: run setup on startup, cleanup on shutdown."""
    logger.info("IRIS starting up...")

    # Run schema migrations synchronously before accepting requests
    run_schema_setup()

    # Pre-load heavy ML models in background threads (non-blocking)
    if settings.ENABLE_LOCAL_OCR:
        from app.services.ocr_service import get_easyocr_reader
        threading.Thread(target=get_easyocr_reader, daemon=True, name="preload-easyocr").start()

    from app.services.document_processor import get_spacy_nlp
    threading.Thread(target=get_spacy_nlp, daemon=True, name="preload-spacy").start()

    from app.services.embedding_service import get_embedding_model
    threading.Thread(target=get_embedding_model, daemon=True, name="preload-embeddings").start()

    # Vector index migration in background thread
    threading.Thread(target=run_vector_index_migration, daemon=True, name="vector-migration").start()

    logger.info("IRIS startup complete.")
    yield

    logger.info("IRIS shutting down.")


# ── FastAPI Application ───────────────────────────────────────────────────────

app = FastAPI(
    title="IRIS — Intelligent Retrieval and Information System",
    description=(
        "Production-grade, privacy-first personal document intelligence platform. "
        "Classify, extract, search, and query your documents — all data stays on your machine."
    ),
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ── CORS Configuration ────────────────────────────────────────────────────────
# Reads from ALLOWED_ORIGINS env var in production, falls back to localhost defaults.
_env_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()] if settings.ALLOWED_ORIGINS else []
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:80",
    "http://localhost",
]
_allowed_origins = _env_origins if _env_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"http://192\.168\.\d+\.\d+(:\d+)?$",  # LAN devices
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    max_age=600,  # Cache preflight for 10 minutes
)


# ── Security Headers Middleware ───────────────────────────────────────────────

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response


# ── Request Logging Middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.now(timezone.utc)
    response = await call_next(request)
    duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.0f}ms)"
    )
    return response


# ── API Routers ───────────────────────────────────────────────────────────────

from app.routers import auth, documents, chat, graph, dashboard, digest

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(dashboard.router)
app.include_router(digest.router)


# ── Health & Root Endpoints ───────────────────────────────────────────────────

@app.get("/", tags=["Health"], include_in_schema=False)
def read_root():
    return {
        "status": "online",
        "service": "IRIS — Intelligent Retrieval and Information System",
        "version": "2.1.0",
        "mode": settings.ENV_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint used by Docker and load balancers."""
    return {
        "status": "healthy",
        "service": "IRIS",
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
