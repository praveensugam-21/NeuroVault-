# NeuroVault — System Architecture

This document explains the full system architecture of a self-hosted NeuroVault deployment.

---

## 1. The Self-Hosted Model

NeuroVault is not a SaaS platform. Every user runs their own complete, independent instance. The diagram below shows one such deployment:

```
┌──────────────────────────── Your Computer / Server ────────────────────────────┐
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                    Docker Compose Network                            │    │
│   │                                                                      │    │
│   │   Browser ──► Nginx (Port 80/443)                                   │    │
│   │                    │                                                 │    │
│   │         ┌──────────┴──────────┐                                     │    │
│   │         │                     │                                     │    │
│   │    Frontend (React)      Backend API (FastAPI)                      │    │
│   │                               │                                     │    │
│   │            ┌──────────────────┼──────────────────┐                  │    │
│   │            │                  │                  │                  │    │
│   │      PostgreSQL           ChromaDB           Uploads/               │    │
│   │    (Docker Volume)     (Docker Volume)    (Docker Volume)          │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│                    Everything stays on YOUR disk                               │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Responsibilities

| Service | Technology | Purpose |
|---|---|---|
| **Nginx** | nginx:alpine | Reverse proxy, rate limiting, HTTPS termination |
| **Frontend** | React + Vite + TypeScript | User interface, Knowledge Graph visualisation |
| **Backend** | FastAPI + Python | API, document pipeline orchestration, JWT auth |
| **PostgreSQL** | postgres:15-alpine | Relational data: users, documents, entities, logs |
| **ChromaDB** | chromadb | Vector embeddings for semantic document search |
| **Uploads** | Docker Volume | Raw uploaded files (PDFs, images, audio) |
| **Model Cache** | Docker Volume | SentenceTransformer + EasyOCR model weights |

---

## 3. Document Processing Pipeline

When a file is uploaded, it travels through a multi-stage background pipeline:

```
Upload
  │
  ▼
Save to disk (uploads/ volume)
  │
  ▼
Create DB record (status = PROCESSING)
  │
  ▼
Text Extraction
  ├── Digital PDF ──► pypdf (direct text layer)
  └── Scanned PDF / Image ──► EasyOCR (neural OCR)
  │
  ▼
Classification & Metadata Extraction
  ├── Primary: Local Ollama Model (contextual JSON)
  └── Fallback: Rule-based regex parser (offline)
  │
  ▼
AES-256 Encrypt extracted_json
  │
  ▼
Summary Card Generation
  │
  ▼
Named Entity Recognition (spaCy)
  │
  ▼
Knowledge Graph Linking (GraphEdge table)
  │
  ▼
Vector Embedding (SentenceTransformer all-MiniLM-L6-v2)
  │
  ▼
Store in ChromaDB
  │
  ▼
DB record updated (status = COMPLETE)
```

---

## 4. Authentication Flow

```
Client                 Nginx                Backend               PostgreSQL
  │                      │                     │                       │
  │── POST /api/auth/login ─────────────────► │                       │
  │                                            │── Query user ────────►│
  │                                            │◄─ User record ────────│
  │                                            │
  │                                            │ [Argon2id verify password]
  │                                            │ [Generate access_token (15 min)]
  │                                            │ [Generate refresh_token (30 days)]
  │                                            │ [Store hashed refresh_token in DB]
  │                                            │
  │◄─ {access_token, refresh_token} ──────────│
  │
  │ ... (15 minutes later)
  │
  │── POST /api/auth/refresh ───────────────► │
  │   body: {refresh_token}                    │── Verify hash ────────►│
  │                                            │◄─ Match ──────────────│
  │                                            │ [Rotate: new pair]
  │◄─ {new_access_token, new_refresh_token} ──│
```

---

## 5. Data Isolation Between Users

Even on a single NeuroVault instance shared between family members or colleagues, all data is strictly isolated:

- Every database query is filtered by `user_id`.
- ChromaDB vector searches use `where={"user_id": user_id}` metadata filters.
- Uploaded files are stored in a flat `uploads/` directory with UUID filenames — no user-identifiable paths.
- The API never returns another user's documents, entities, or audit logs.

---

## 6. Core Components

### React Frontend
- Built with TypeScript, React Router, and Zustand for state management.
- Knowledge Graph rendered using React Flow with a custom clustered layout algorithm.
- Tailwind CSS for styling.

### FastAPI Backend
- Async Python API with SQLAlchemy ORM + Alembic migrations.
- Background document pipeline managed by `DocumentPipelineManager`.
- Encryption/decryption layer via `EncryptionService` (AES-256 Fernet).

### PostgreSQL
- Full relational schema: `users`, `documents`, `document_tags`, `entities`, `graph_edges`, `audit_logs`.
- Connection pooling via SQLAlchemy `QueuePool`.
- Index-optimised queries on `user_id`, `status`, and `category`.

### ChromaDB
- Persistent local vector store at `/data/chromadb`.
- Stores 384-dimensional `all-MiniLM-L6-v2` embeddings.
- User-scoped metadata filtering ensures vector search cannot leak data across users.
