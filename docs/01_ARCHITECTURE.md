# IRIS — System Architecture

This document explains the full system architecture of a self-hosted IRIS deployment, including the LLM routing stack, document processing pipeline, and service responsibilities.

> **Last Updated:** 2026-07-17 — Updated for Gemini 2.5 Flash, OLLAMA_BASE_URL=disabled, and reextract endpoint.

---

## 1. The Self-Hosted Model

IRIS is not a SaaS platform. Every user runs their own complete, independent instance. The diagram below shows one such deployment:

```
┌──────────────────────────── Your Computer / Server ─────────────────────────────┐
│                                                                                  │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                      Docker Compose Network (iris-net)                 │    │
│   │                                                                        │    │
│   │   Browser ──► Nginx (Port 80 / 443)                                   │    │
│   │                        │                                               │    │
│   │           ┌────────────┴────────────┐                                  │    │
│   │           │                         │                                  │    │
│   │    Frontend (React/Vite)     Backend API (FastAPI)                    │    │
│   │                                     │                                  │    │
│   │         ┌───────────────────────────┼──────────────────┐               │    │
│   │         │                           │                  │               │    │
│   │   PostgreSQL                   ChromaDB           Uploads/             │    │
│   │  (Docker Volume)            (Docker Volume)    (Docker Volume)        │    │
│   │                                                                        │    │
│   │   Model Cache (Docker Volume)    Ollama (optional)                    │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│   Optional cloud call (PII-masked only):  Backend ──► Gemini 2.5 Flash API     │
│                                                                                  │
│                      All your files stay on YOUR disk                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Responsibilities

| Service | Technology | Purpose |
|---|---|---|
| **Nginx** | `nginx:alpine` | Reverse proxy, rate limiting, HTTPS termination |
| **Frontend** | React 18 + Vite + TypeScript | User interface, Knowledge Graph visualisation |
| **Backend** | FastAPI + Python 3.11 | API, document pipeline, JWT auth, LLM routing |
| **PostgreSQL** | `postgres:15-alpine` | Relational data: users, documents, entities, audit logs |
| **ChromaDB** | chromadb (embedded) | Vector embeddings for semantic document search |
| **Ollama** | `ollama/ollama:latest` | Optional local LLM inference (disabled by default) |
| **uploads** | Docker Volume | Raw uploaded files (PDFs, images) |
| **chromadb-data** | Docker Volume | ChromaDB persistent vector store |
| **model-cache** | Docker Volume | SentenceTransformer + EasyOCR weights (~1.5 GB) |
| **postgres-data** | Docker Volume | PostgreSQL data directory |

---

## 3. LLM Routing Architecture

IRIS uses a three-tier routing strategy for all AI calls (OCR correction, field extraction, chat):

```
                   ┌──────────────────────────────────────┐
                   │         LLM Router (backend)         │
                   └──────────────┬───────────────────────┘
                                  │
              ┌───────────────────▼──────────────────────┐
              │       Tier 1: Gemini 2.5 Flash           │
              │  • PII masking applied BEFORE sending     │
              │  • model: gemini-2.5-flash                │
              │  • Key prefix: AQ. (Google AI Studio)     │
              │  • Validated on first use (probe call)    │
              └───────────────────┬──────────────────────┘
                        unavailable / key absent
                                  │
              ┌───────────────────▼──────────────────────┐
              │     Tier 2: Ollama (Local LLM)           │
              │  • model: llama3.2 (or configured model) │
              │  • Disabled if OLLAMA_BASE_URL=disabled   │
              │  • Host bridge: host.docker.internal      │
              │  • Timeout: 120 seconds                   │
              └───────────────────┬──────────────────────┘
                  disabled / timeout / unavailable
                                  │
              ┌───────────────────▼──────────────────────┐
              │   Tier 3: Smart Local Rules Engine       │
              │  • Regex classifiers + keyword matching  │
              │  • Pincode → State lookup dictionary     │
              │  • Known OCR correction dictionary       │
              │  • Fuzzy string matching                 │
              │  • Always available — no network needed  │
              └──────────────────────────────────────────┘
```

### PII Masking Before Cloud Transmission

Every call to Gemini passes through the `PIIMasker` first:

```
Raw OCR Text
    │
    ▼  PIIMasker.mask_text()
Masked Text: "Name: [AADHAAR_0] DOB: ..."
    │
    ▼  GeminiService.generate_completion()
Gemini API (cloud) — sees only placeholder tokens
    │
    ▼  PIIMasker.unmask_text()  (local)
Final Response with real values restored
```

---

## 4. Document Processing Pipeline

When a file is uploaded, it travels through a multi-stage background pipeline:

```
Upload (POST /api/documents/upload)
  │
  ▼
Save to disk (uploads/ Docker volume)
  │
  ▼
Create DB record (status = PROCESSING)
  │
  ▼
Text Extraction
  ├── Digital PDF ──► pypdf (direct text layer extraction)
  └── Scanned PDF / Image ──► EasyOCR (CRAFT + ResNet/LSTM neural OCR)
  │
  ▼
OCR Correction (PostOCRCorrector — three-pass)
  ├── Pass 1: Pincode → State resolution
  ├── Pass 2: Known character confusion corrections (ee→d, hin→lim, T→J etc.)
  └── Pass 3: Fuzzy match against known Indian names dictionary
  │
  ▼
Classification & Structured Field Extraction (OCRExtractor + LLM Router)
  ├── Tier 1: Gemini 2.5 Flash (PII-masked prompt)
  ├── Tier 2: Ollama local LLM
  └── Tier 3: Regex rule-based extractor
  │
  ▼
AES-256 Encrypt extracted_json (Fernet)
  │
  ▼
Summary Card Generation
  │
  ▼
Named Entity Recognition (spaCy en_core_web_sm)
  │
  ▼
Knowledge Graph Linking (GraphEdge table)
  │
  ▼
Vector Embedding (SentenceTransformer all-MiniLM-L6-v2 → 384-dim)
  │
  ▼
Store embeddings in ChromaDB (with user_id metadata filter)
  │
  ▼
DB record updated (status = COMPLETE)
```

### Re-Extraction Endpoint

If a document was processed while no LLM was available (raw OCR output saved), it can be corrected without re-uploading:

```
POST /api/documents/{id}/reextract
  │
  ▼
Reload raw OCR text from DB
  │
  ▼
Re-run OCR Correction + LLM Extraction with currently active LLM
  │
  ▼
Update extracted_json, summary, entities, ChromaDB embeddings
  │
  ▼
status = COMPLETE
```

---

## 5. Semantic Search Pipeline (RAG)

When a user asks a question in the chat interface:

```
User Query
  │
  ▼
Embed query (all-MiniLM-L6-v2)
  │
  ▼
ChromaDB MMR Search (Maximal Marginal Relevance)
  │  • Retrieves top-20 diverse candidates
  │  • user_id metadata filter applied
  ▼
CrossEncoder Reranking (ms-marco-MiniLM-L-6-v2)
  │  • Reranks top-20 → selects top-5 most relevant
  ▼
LLM Router (Gemini → Ollama → Local Rules)
  │  • System prompt + document chunks + user question
  ▼
Cited Answer returned to user
```

---

## 6. Authentication Flow

```
Client                   Nginx               Backend              PostgreSQL
  │                        │                     │                     │
  │── POST /api/auth/login ─────────────────────►│                     │
  │                                              │── Query user ───────►│
  │                                              │◄─ User record ───────│
  │                                              │                     │
  │                                              │  [Argon2id verify password]
  │                                              │  [Generate access_token  (15 min)]
  │                                              │  [Generate refresh_token (30 days)]
  │                                              │  [Store hashed refresh_token in DB]
  │                                              │                     │
  │◄─ {access_token, refresh_token} ────────────│                     │
  │                                              │                     │
  │   ... (15 minutes later) ...                 │                     │
  │                                              │                     │
  │── POST /api/auth/refresh ───────────────────►│                     │
  │   body: {refresh_token}                      │── Verify hash ──────►│
  │                                              │◄─ Match ─────────────│
  │                                              │  [Rotate: generate new pair]
  │◄─ {new_access_token, new_refresh_token} ────│                     │
```

---

## 7. Data Isolation Between Users

Even on a single shared IRIS instance, all data is strictly isolated:

- Every database query is filtered by `user_id`.
- ChromaDB vector searches include `where={"user_id": user_id}` metadata filters.
- Uploaded files are stored with UUID filenames — no user-identifiable paths.
- The API never returns another user's documents, entities, or audit logs.

---

## 8. Core Components

### React Frontend
- Built with TypeScript, React Router, and Zustand for state management.
- Knowledge Graph rendered using React Flow with a custom clustered layout algorithm.
- Tailwind CSS for styling.
- Upload progress via 800 ms polling of `/api/documents/{id}` status endpoint.

### FastAPI Backend
- Async Python API with SQLAlchemy ORM + Alembic migrations.
- Background document pipeline managed by `DocumentPipelineManager`.
- Encryption/decryption layer via `EncryptionService` (AES-256 Fernet).
- Three-tier LLM routing via `GeminiService` → `OllamaService` → local rules.

### PostgreSQL
- Full relational schema: `users`, `documents`, `document_tags`, `entities`, `graph_edges`, `audit_logs`.
- Connection pooling via SQLAlchemy `QueuePool`.
- Index-optimised queries on `user_id`, `status`, and `category`.

### ChromaDB
- Persistent local vector store at `/data/chromadb`.
- Stores 384-dimensional `all-MiniLM-L6-v2` embeddings.
- User-scoped metadata filtering ensures vector search cannot leak data across users.
- MMR retrieval ensures result diversity (avoids returning 5 chunks from the same document).

### Model Cache Volume
- Persists HuggingFace Transformers model weights across container restarts.
- Configured via `HF_HOME=/data/model-cache/huggingface` environment variable.
- Prevents repeated 1.5 GB+ downloads on container rebuild.
