# IRIS — Intelligent Retrieval and Information System

> **Also known as NeuroVault** — your self-hosted, privacy-first AI document vault.

IRIS is a personal document intelligence platform that lets you upload, understand, and converse with your own documents — Aadhaar cards, PAN cards, resumes, bank statements, passports, and more. All data lives on **your machine**. Nothing is shared with any cloud service without your explicit consent and even then, sensitive numbers are masked before transmission.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📄 **Universal OCR** | EasyOCR + PyMuPDF extract text from scanned images and digital PDFs |
| 🔑 **Google Sign-In** | Optional Google OAuth 2.0 with secure ID-token verification + account auto-linking |
| 🧠 **Semantic Search** | ChromaDB vector DB with MMR retrieval + CrossEncoder reranking |
| 💬 **AI Chat Interface** | Ask questions in natural language; get cited answers from your documents |
| 🔒 **PII Masking** | Aadhaar, PAN, passport, DL, email, phone numbers masked locally before any cloud call |
| ⚡ **Gemini 2.5 Flash** | Primary LLM for OCR correction, field extraction, and chat via direct HTTP/1.1 REST |
| ⚙️ **Settings UI** | Dynamic custom Gemini API key configuration with live verification probe |
| 🦙 **Ollama (Optional)** | Run a fully offline LLM on your hardware; disabled by default |
| 📐 **Local Rules Engine** | Smart regex + dictionary fallback when no LLM is available |
| 🗃️ **Multi-user Vault** | Row-level user isolation — family or team members can share one instance |
| 🔐 **AES-256 Encryption** | Sensitive metadata encrypted at rest in PostgreSQL |
| 📊 **Knowledge Graph** | Automatically links entities (names, dates, orgs) across documents |

---

## 🏗️ Technology Stack

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | React + Vite + TypeScript | React 18 |
| **Styling** | Tailwind CSS | v3 |
| **State Management** | Zustand | — |
| **Graph Visualisation** | React Flow | — |
| **Backend** | FastAPI + Python | Python 3.11 |
| **ORM** | SQLAlchemy + Alembic | — |
| **Relational DB** | PostgreSQL | 15-alpine |
| **Vector DB** | ChromaDB | local persistent |
| **Embeddings** | `all-MiniLM-L6-v2` (SentenceTransformers) | 384-dim |
| **Reranking** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | — |
| **OCR** | EasyOCR (CRAFT + ResNet/LSTM) | — |
| **PDF Parsing** | PyMuPDF (fitz) | — |
| **Primary LLM** | Gemini 2.5 Flash (cloud, PII-masked) | `gemini-2.5-flash` |
| **Secondary LLM** | Ollama / llama3.2 (local, optional) | disabled by default |
| **Auth** | JWT (access 15 min) + refresh tokens (30 days) | Argon2id hashing + Google OAuth 2.0 |
| **Reverse Proxy** | Nginx | alpine |
| **Containerisation** | Docker Compose | — |

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with WSL2 backend on Windows)
- Git
- A free [Gemini API key](https://aistudio.google.com/app/apikey) *(optional but recommended)*

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/NeuroVault.git
cd NeuroVault

# 2. Create your environment file
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
POSTGRES_PASSWORD=your_strong_password_here
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# Gemini (optional — enables AI-powered OCR correction and smart chat)
GEMINI_API_KEY=AQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.5-flash

# Ollama (disabled by default — set to a URL to enable)
OLLAMA_BASE_URL=disabled
```

```bash
# 3. Start all services
docker compose up -d

# 4. Wait for health checks to pass (~60 seconds on first boot)
docker compose ps

# 5. Open the app
start http://localhost
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_DB` | `iris` | PostgreSQL database name |
| `POSTGRES_USER` | `iris_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password — **change this** |
| `JWT_SECRET_KEY` | *(required)* | Secret for JWT signing — generate with `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | *(required)* | Fernet key for AES-256 field encryption |
| `GEMINI_API_KEY` | `""` (disabled) | Google AI Studio API key — leave blank for fully offline mode |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `GOOGLE_CLIENT_ID` | `""` (disabled) | Google OAuth Client ID — see [Google OAuth Setup](#google-oauth-setup) |
| `ALLOWED_ORIGINS` | `""` (localhost) | Comma-separated list of allowed CORS origins in production |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size in megabytes |
| `OLLAMA_BASE_URL` | `disabled` | Ollama endpoint. Set to `http://host.docker.internal:11434` to use host Ollama |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model to use when Ollama is enabled |
| `CHROMA_PERSIST_DIR` | `/data/chromadb` | ChromaDB storage path inside the container |
| `UPLOADS_DIR` | `/data/uploads` | Uploaded files storage path |
| `MODEL_CACHE_DIR` | `/data/model-cache` | HuggingFace + EasyOCR model cache path |
| `HF_HOME` | `/data/model-cache/huggingface` | HuggingFace cache directory |
| `ENV_MODE` | `development` | Set to `production` for production deployments |
| `ENABLE_LOCAL_OCR` | `true` | Enable/disable local EasyOCR (disable on low-resource servers) |

---

## 🔑 Google OAuth Setup

Google Sign-In is **fully optional**. To enable it:

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Under **Authorized JavaScript origins**, add:
   - `http://localhost:5173` (development)
   - `https://yourdomain.com` (production)
5. Copy the **Client ID** and add it to your `.env`:
   ```env
   GOOGLE_CLIENT_ID=123456789-xxxxxx.apps.googleusercontent.com
   ```
6. Restart the backend: `docker compose restart backend`

The Google Sign-In button will now appear on the login page. Existing users who sign in with Google for the first time have their account **automatically linked** by email.

---

## 🔁 LLM Routing

IRIS uses a three-tier LLM routing strategy. It always tries the fastest/smartest option first:

```
User Query / Document Upload
         │
         ▼
  ┌─────────────────────┐
  │  1. Gemini 2.5 Flash │  ← Preferred: fast, accurate, PII-masked before sending
  │     (Cloud, masked)  │
  └──────────┬──────────┘
             │ unavailable / key missing
             ▼
  ┌─────────────────────┐
  │  2. Ollama (Local)  │  ← Optional: fully offline, CPU-only (slow), disabled by default
  │     llama3.2        │
  └──────────┬──────────┘
             │ unavailable / disabled
             ▼
  ┌────────────────────────────┐
  │  3. Smart Local Rules      │  ← Always available: regex + pincode/state dict + fuzzy match
  │     Engine (Offline)       │
  └────────────────────────────┘
```

---

## 🔒 Privacy Architecture

IRIS is privacy-first. Before any text is sent to Gemini:

1. **PII Masking** — `PIIMasker` scans for Aadhaar, PAN, Passport, DL, email, phone numbers, and bank account numbers using regex patterns.
2. **Placeholder Substitution** — Each PII value is replaced with a token like `[AADHAAR_0]`, `[PAN_0]`, `[EMAIL_1]`.
3. **Cloud Transmission** — Only the masked text (with placeholder tokens) is sent to Gemini.
4. **Local Unmasking** — The LLM response containing placeholder tokens is unmasked locally using the in-memory mapping dictionary.

**Nothing that reaches Google contains a real Aadhaar number, PAN number, or any other sensitive identifier.**

See [docs/10_SECURITY_AND_PRIVACY.md](docs/10_SECURITY_AND_PRIVACY.md) for full details.

---

## 📁 Project Structure

```
NeuroVault/
├── backend/
│   ├── app/
│   │   ├── config.py              # Settings (env vars, feature flags)
│   │   ├── main.py                # FastAPI application entry point
│   │   ├── database.py            # SQLAlchemy engine + session factory
│   │   ├── models/                # ORM models (User, Document, Entity …)
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── routers/               # API route handlers
│   │   ├── pipeline/              # Document pipeline orchestration
│   │   └── services/
│   │       ├── ocr_service.py         # PDF → image → EasyOCR dispatch
│   │       ├── ocr_extractor.py       # Expert prompt OCR field extractor
│   │       ├── post_ocr_corrector.py  # Three-pass OCR correction engine
│   │       ├── pii_masker.py          # Local PII detection & masking
│   │       ├── gemini_service.py      # Gemini 2.5 Flash wrapper
│   │       ├── ollama_service.py      # Ollama local LLM wrapper
│   │       ├── embedding_service.py   # SentenceTransformer + ChromaDB
│   │       ├── rag_pipeline.py        # MMR retrieval + CrossEncoder reranking
│   │       ├── document_processor.py  # Classification & metadata extraction
│   │       ├── encryption_service.py  # AES-256 Fernet field encryption
│   │       ├── knowledge_graph.py     # Entity linking & graph edges
│   │       └── security.py            # JWT + Argon2id auth helpers
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Upload, Vault, Chat, Dashboard …
│   │   ├── components/            # Reusable UI components
│   │   └── store/                 # Zustand state slices
│   └── Dockerfile
├── nginx/
│   └── nginx.conf                 # Reverse proxy + rate limiting config
├── docs/                          # Full technical documentation
├── scripts/                       # backup.sh, restore.sh, utility scripts
├── docker-compose.yml
├── .env.example                   # Template — copy to .env and fill in
├── README.md
└── DEPLOYMENT.md
```

---

## 📖 Documentation

| Doc | Description |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Full deployment and operations guide |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |
| [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) | System architecture and service diagrams |
| [docs/10_SECURITY_AND_PRIVACY.md](docs/10_SECURITY_AND_PRIVACY.md) | Security model and privacy contract |
| [docs/11_PARSING_ENGINES.md](docs/11_PARSING_ENGINES.md) | OCR pipeline and correction engines |
| [docs/06_VECTOR_DB_AND_RAG.md](docs/06_VECTOR_DB_AND_RAG.md) | ChromaDB, embeddings, MMR + reranking |
| [docs/ISSUE_LOG.md](docs/ISSUE_LOG.md) | Full debug and issue history |

---

FLOWZINT HACKATHON   


---

*Current version: **2.2.0** — See [CHANGELOG.md](CHANGELOG.md) for all changes.*
