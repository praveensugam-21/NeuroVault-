# IRIS

**A secure, self-hosted personal document vault. Your data stays on your machine — always.**

IRIS is an open-source document intelligence platform you deploy on your own hardware. Upload, classify, search, and query your documents using local OCR, named entity recognition, vector search, and a local Ollama-powered Memory Assistant — all without sending any file or query to external servers.

> The developer distributes the software. You own everything else.

---

## What Makes IRIS Different?

| Feature | Traditional Cloud Apps | IRIS |
|---|---|---|
| Document storage | Provider's cloud | Your machine only |
| Who can see your data | Provider + their staff | Only you |
| Database | Shared cloud DB | Your private PostgreSQL |
| AI queries | Sent to cloud | Local Ollama LLM |
| Internet required | Always | None (100% offline) |
| Monthly fee | Usually yes | Free (open source) |

---

## What It Does

- **Smart Classification** — Automatically categorises documents into Identity, Academic, Financial, Professional, Medical, Vehicle, and more.
- **OCR & PDF Parsing** — Extracts text from scanned images (EasyOCR) and digital PDFs (pypdf) without any cloud service.
- **Metadata Extraction** — Pulls structured fields like Aadhaar numbers, PAN numbers, DOBs, expiry dates, and bank account numbers. Sensitive fields are encrypted at rest using AES-256.
- **Knowledge Graph** — Links documents through shared entities (names, organisations, dates). Visualise connections between your Aadhaar, PAN, and bank statements.
- **Semantic Search** — Powered by SentenceTransformer embeddings (ChromaDB). Find the document by meaning, not just keywords.
- **Memory Assistant** — Ask natural language questions about your vault ("When does my driving licence expire?") and get structured, cited answers. Uses a **100% private local rules engine** or your local Ollama instance for answering queries completely offline, keeping all personal details secure on your device.
- **Document Lock** — Lock sensitive files behind a secondary PIN. Locked files are excluded from all search results and AI queries.
- **Audit Logs** — Every action (upload, view, lock, unlock, delete, query) is logged in your private database.

---

## Quick Start (5 Steps)

### Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux)
- [Ollama](https://ollama.com) running locally on your host or as a Docker container

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/praveensugam-21/IRIS-.git
cd IRIS-

# 2. Create your environment file
cp .env.example .env

# 3. Edit .env and fill in your values (see notes below)
#    Required: POSTGRES_PASSWORD, JWT_SECRET_KEY, ENCRYPTION_KEY

# 4. Start all services
docker compose up -d

# 5. Open your browser
# → http://localhost
```

On first boot, create your account. You are the owner and administrator of your own deployment.

---

## Generating Required Keys

Open a terminal and run these commands to generate secure keys:

```bash
# JWT Secret Key
openssl rand -hex 32

# AES-256 Encryption Key (for sensitive fields)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output values into your `.env` file.

---

## Supported Platforms

IRIS requires no code changes to deploy on any of the following:

| Platform | Notes |
|---|---|
| Windows Laptop | Docker Desktop required |
| Mac | Docker Desktop required |
| Linux Desktop/Server | Docker Engine |
| Raspberry Pi 4+ | Use ARM-compatible images |
| Synology NAS | Enable Container Manager |
| Linux VPS (DigitalOcean, Linode) | Recommended for shared/family use |
| AWS EC2 | t3.medium or larger |
| Azure VM | Standard_B2s or larger |
| Google Cloud VM | e2-medium or larger |

---

## Architecture

```
Your Device / Server
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   Browser  ──►  Nginx (Port 80/443)                       │
│                    │                                       │
│                    ├──► Frontend (React + Vite)            │
│                    │                                       │
│                    └──► Backend API (FastAPI)              │
│                              │                             │
│                    ┌─────────┼─────────┐                   │
│                    ▼         ▼         ▼                   │
│               PostgreSQL  ChromaDB  Uploads/               │
│               (Relational) (Vectors) (Files)               │
│                                                            │
│   All data is stored in Docker named volumes on YOUR disk  │
└────────────────────────────────────────────────────────────┘
```

All data stays completely isolated on your infrastructure, running fully locally and offline.


---

## Documentation

| File | Description |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Full deployment guide (HTTPS, VPS, backup, update) |
| [database.md](database.md) | PostgreSQL schema, Alembic migrations, pgAdmin |
| [security.md](security.md) | Encryption, authentication, privacy architecture |
| [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) | System architecture deep dive |
| [docs/10_SECURITY_AND_PRIVACY.md](docs/10_SECURITY_AND_PRIVACY.md) | Security & privacy policy |

---

## Test Credentials (Development Only)

For local testing after first boot:
- Register any email and password you choose — you are the admin.
- Secondary PIN: Set via **Settings → Security PIN** after login.

---

## License

IRIS is open-source software. You are free to use, modify, and self-host it.
