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
    title="NeuroVault AI — Core Knowledge Intelligence Engine",
    description="Production-grade personal reasoning & document semantic memory layer.",
    version="1.0.0"
)

# CORS middleware mapping
# Allows React client running on localhost:5173 to interact with FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:80",
        "http://localhost:8001",
    ],
    allow_credentials=True,
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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "NeuroVault AI Engine",
        "version": "1.0.0",
        "mode": settings.ENV_MODE
    }
