# IRIS — Deployment Guide

This guide covers everything needed to install, configure, run, and maintain a self-hosted IRIS instance using Docker Compose.

---

## Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10/11 (WSL2), Ubuntu 20.04+, macOS 12+ | Ubuntu 22.04 LTS |
| **RAM** | 4 GB | 8 GB+ |
| **Disk** | 10 GB free | 20 GB+ (model cache is ~1.5 GB) |
| **Docker** | Docker Desktop 4.x / Docker Engine 24+ | Latest stable |
| **Docker Compose** | v2.x (plugin) | Latest stable |
| **Internet** | Required on first boot (model download) | — |

> [!WARNING]
> WSL2 on Windows requires free space on the **C: drive** for the WSL2 virtual disk (`ext4.vhdx`). If C: is full, Docker will throw I/O errors. Move the IRIS project to a secondary drive (e.g., `E:\`) to avoid filling up C:.

---

## 1. Installation

### Step 1 — Clone the Repository

```powershell
git clone https://github.com/your-username/NeuroVault.git
cd NeuroVault
```

### Step 2 — Create Your Environment File

```powershell
copy .env.example .env
```

Then open `.env` in a text editor and fill in every value. See the [Environment Variables Reference](#environment-variables-reference) below.

### Step 3 — Generate Security Keys

Open a terminal and run these commands to generate cryptographically secure keys:

```powershell
# JWT signing key (paste into JWT_SECRET_KEY)
python -c "import secrets; print(secrets.token_hex(32))"

# AES-256 encryption key (paste into ENCRYPTION_KEY)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 4 — Start All Services

```powershell
docker compose up -d
```

On first boot, Docker will:
1. Build the backend and frontend containers (~3–5 minutes)
2. Download PostgreSQL, Nginx, and Ollama images
3. Download ML model weights into the `model-cache` volume (~1.5 GB on first run)

> [!NOTE]
> Subsequent restarts are fast because the `model-cache` Docker volume persists the HuggingFace and EasyOCR model weights between container restarts.

### Step 5 — Verify All Services Are Healthy

```powershell
docker compose ps
```

Expected output (all services should show `healthy` or `running`):

```
NAME            STATUS                    PORTS
iris_postgres   Up X minutes (healthy)    5432/tcp
iris_backend    Up X minutes (healthy)    8000/tcp
iris_frontend   Up X minutes             
iris_ollama     Up X minutes             0.0.0.0:11434->11434/tcp
iris_nginx      Up X minutes             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Step 6 — Access the Application

Open your browser and navigate to:

```
http://localhost
```

Register your first account. The first registered user is the owner of that IRIS instance.

---

## 2. Gemini API Key Setup

Gemini 2.5 Flash is the primary LLM used for OCR correction, field extraction, and the chat interface. It requires an API key from Google AI Studio.

### Getting Your Key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API key"** and select a Google Cloud project (or create a new one)
4. Copy the generated key

> [!IMPORTANT]
> API keys generated from Google AI Studio now start with the prefix `AQ.` (project-scoped keys). These are **different** from the older `AIza...` style keys. Make sure you use a new `AQ.` prefix key.

### Configuring the Key

You can configure your Gemini API Key in two ways:

1. **Via the UI (Recommended)**:
   - Log in to the application and navigate to **Settings** (`/settings`).
   - Paste your API key into the Gemini API Key input field and click **Test & Save**.
   - The backend runs a live probe (`POST /api/auth/settings/gemini-key`). If valid, the key is applied instantly without restarting containers.

2. **Via `.env` file**:
   ```env
   GEMINI_API_KEY=AQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   GEMINI_MODEL=gemini-2.5-flash
   ```

> [!NOTE]
> The old model `gemini-1.5-flash` is deprecated and does not work with new `AQ.` prefix keys. Always use `gemini-2.5-flash` or a newer model.

### Key Validation

On first request to the backend, IRIS automatically validates the key with a probe call:

```
Gemini probe → "Reply with only the word: READY"
Expected response: non-empty text
```

If the probe fails (wrong key, quota exhausted, etc.), IRIS automatically falls back to Ollama or the local rules engine. You will see this in the backend logs:

```bash
docker compose logs backend --tail=50
```

---

## 3. Ollama Configuration

Ollama provides a fully offline LLM option. It is **disabled by default** because running a 3B parameter model on CPU inside Docker takes 75+ seconds per inference.

### Option A — Disabled (Default)

```env
OLLAMA_BASE_URL=disabled
```

When set to `disabled`, the backend skips Ollama entirely and falls back directly to the Local Rules Engine if Gemini is also unavailable.

### Option B — Use Host-Installed Ollama

If you have Ollama installed on your Windows/Linux host, you can connect the backend container to it over the `host.docker.internal` bridge (already configured in `docker-compose.yml`):

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
```

Then start Ollama on your host machine:

```powershell
# Pull the model (first time only)
ollama pull llama3.2

# Ollama serves automatically on localhost:11434
ollama serve
```

> [!TIP]
> Running Ollama on a machine with a dedicated GPU (NVIDIA CUDA or Apple Metal) is dramatically faster. A GPU-accelerated llama3.2 answers in 2–5 seconds versus 75+ seconds on CPU.

### Option C — Containerised Ollama

The `docker-compose.yml` includes a containerised Ollama service. To enable it:

1. Set `OLLAMA_BASE_URL=http://ollama:11434` in `.env`
2. Run `docker compose up -d ollama` to start the container
3. Pull a model into the container:
   ```powershell
   docker exec -it iris_ollama ollama pull llama3.2
   ```

> [!WARNING]
> The containerised Ollama stores models in `./ollama_data/` on the project folder (not C:) to avoid filling up the system drive.

---

## 4. Re-Extracting Documents

If a document was uploaded while the Gemini key was invalid (or Ollama was unavailable), the stored metadata may contain raw garbled OCR output. You can trigger re-extraction once a valid LLM is configured:

```bash
# Re-extract a specific document by ID
curl -X POST http://localhost/api/documents/{document_id}/reextract \
  -H "Authorization: Bearer <your_jwt_token>"
```

This endpoint re-runs the full OCR correction and field extraction pipeline using the currently active LLM.

---

## 5. Health Checks

The backend health check uses Python's built-in `urllib` (no `curl` required):

```yaml
# In docker-compose.yml:
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

To manually check service health:

```powershell
# All services at once
docker compose ps

# Backend health endpoint
curl http://localhost/health

# View backend logs
docker compose logs backend --tail=100 --follow
```

---

## 6. Updating IRIS

```powershell
# Pull latest images and rebuild
git pull
docker compose pull
docker compose up -d --build

# Verify all services are healthy
docker compose ps
```

> [!NOTE]
> Your data (PostgreSQL, ChromaDB, uploads, model cache) is stored in named Docker volumes and is **not affected** by rebuilds.

---

## 7. Backup and Restore

### Backup

```powershell
# Run the automated backup script
bash scripts/backup.sh
```

The script creates a timestamped archive in `./backups/` containing:
- PostgreSQL database dump (pg_dump)
- ChromaDB vector store snapshot
- Uploads directory

### Restore

```powershell
# Restore from a backup archive
bash scripts/restore.sh ./backups/iris_backup_YYYYMMDD_HHMMSS.tar.gz
```

> [!CAUTION]
> Restore will overwrite existing data. Make a backup of the current state before restoring an older snapshot.

### Manual Database Backup

```powershell
# Backup PostgreSQL only
docker exec iris_postgres pg_dump -U iris_user iris > iris_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL from dump
cat iris_backup_YYYYMMDD.sql | docker exec -i iris_postgres psql -U iris_user iris
```

---

## 8. Stopping and Removing

```powershell
# Stop all containers (data preserved)
docker compose down

# Stop and remove all data volumes (DESTRUCTIVE — deletes all documents, DB, vectors)
docker compose down -v

# Remove only a specific volume
docker volume rm neurovault_postgres-data
```

---

## 9. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Backend shows `starting` forever | ML model download in progress | Wait ~5 min, then `docker compose logs backend` |
| `(unhealthy)` on backend | Health probe failing | `docker compose logs backend --tail=50` |
| Gemini not working | Wrong key or deprecated model | Check key starts with `AQ.` and model is `gemini-2.5-flash` |
| OCR names garbled | LLM was unavailable at upload time | Use `/api/documents/{id}/reextract` endpoint |
| `I/O error` in Docker build | WSL2 disk full | Free space on C:, run `wsl --shutdown`, restart Docker |
| Ollama timeout (75+ sec) | Running on CPU | Set `OLLAMA_BASE_URL=disabled` or use GPU machine |
| Model re-downloading every restart | `model-cache` volume not mounted | Ensure `MODEL_CACHE_DIR` and `HF_HOME` use Docker volume paths |

---

## Environment Variables Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `POSTGRES_DB` | `iris` | No | PostgreSQL database name |
| `POSTGRES_USER` | `iris_user` | No | PostgreSQL username |
| `POSTGRES_PASSWORD` | `changeme` | **Yes** | PostgreSQL password — change before deploying |
| `JWT_SECRET_KEY` | placeholder | **Yes** | 32-byte hex secret for JWT signing |
| `ENCRYPTION_KEY` | placeholder | **Yes** | Fernet key for AES-256 field encryption |
| `GOOGLE_CLIENT_ID` | `""` | No | Google OAuth Client ID — enables Google Sign-In button |
| `ALLOWED_ORIGINS` | `""` | No | Comma-separated list of allowed CORS origins in production |
| `MAX_UPLOAD_SIZE_MB` | `50` | No | Maximum file upload size in MB |
| `GEMINI_API_KEY` | `""` | No | Google AI Studio API key (enables cloud LLM) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | No | Gemini model name |
| `OLLAMA_BASE_URL` | `disabled` | No | Ollama URL or `disabled` to skip |
| `OLLAMA_MODEL` | `llama3.2` | No | Ollama model name |
| `OLLAMA_TIMEOUT` | `120` | No | Ollama request timeout in seconds |
| `CHROMA_PERSIST_DIR` | `/data/chromadb` | No | ChromaDB storage path (inside container) |
| `UPLOADS_DIR` | `/data/uploads` | No | Uploads directory (inside container) |
| `MODEL_CACHE_DIR` | `/data/model-cache` | No | ML model cache (inside container) |
| `HF_HOME` | `/data/model-cache/huggingface` | No | HuggingFace cache directory |
| `ENV_MODE` | `development` | No | Set to `production` for production deployments |
| `ENABLE_LOCAL_OCR` | `true` | No | Enable EasyOCR for image/scanned-PDF ingestion |
| `ENABLE_VOICE_TRANSCRIPTION` | `true` | No | Enable Whisper voice note transcription |

---

## 10. Production Security Checklist

Before exposing IRIS to the internet, verify each item:

- [ ] `JWT_SECRET_KEY` is a randomly generated 32-byte hex value (not the placeholder)
- [ ] `ENCRYPTION_KEY` is a randomly generated Fernet key (not the placeholder)
- [ ] `POSTGRES_PASSWORD` is a strong random password (not `changeme`)
- [ ] `ALLOWED_ORIGINS` is set to your actual domain (e.g. `https://iris.yourdomain.com`)
- [ ] Nginx is configured with a valid TLS certificate (HTTPS only)
- [ ] `ENV_MODE=production` in your `.env`
- [ ] Docker volumes are backed up regularly (see [Backup & Restore](#8-backup--restore))
- [ ] `GEMINI_API_KEY` is a project-scoped key with usage quotas set in Google Cloud Console
- [ ] `GOOGLE_CLIENT_ID` has only your domain in Authorized JavaScript Origins
- [ ] The backend port (8000) is **not** exposed to the internet — only Nginx (80/443) should be
- [ ] Firewall rules block direct access to PostgreSQL port 5432 from outside Docker network

