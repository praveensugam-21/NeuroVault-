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
