import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Import all models to ensure they are registered with the engine Base metadata
from app.models import User, Document, DocumentTag, Entity, GraphEdge, AuditLog

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NeuroVault — Secure Personal Document Vault Engine",
    description="Production-grade secure personal document archiving & indexing engine.",
    version="1.0.0"
)

# CORS middleware mapping
# Allows all origins to connect (necessary for mobile apps and web tunnels using JWT headers).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
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
        "service": "NeuroVault AI Engine",
        "version": "1.0.0",
        "mode": settings.ENV_MODE
    }
