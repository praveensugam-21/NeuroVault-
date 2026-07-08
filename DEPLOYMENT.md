# NeuroVault — Deployment Guide

This document covers every aspect of deploying, configuring, securing, updating, and backing up your NeuroVault instance.

---

## 1. Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| RAM | 2 GB | 4 GB+ |
| Disk | 10 GB free | 50 GB+ |
| CPU | 2 cores | 4 cores |
| Docker | Engine 24+ | Latest |
| Docker Compose | v2+ | Latest |
| Internet | None | — |

---

## 2. Basic Installation (Local / Home Server)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/praveensugam-21/NeuroVault-.git
cd NeuroVault-
```

### Step 2 — Create Your Environment File

```bash
cp .env.example .env
```

Open `.env` and fill in all `CHANGE_ME_` values:

```env
POSTGRES_PASSWORD=your_strong_password_here
JWT_SECRET_KEY=<output of: openssl rand -hex 32>
ENCRYPTION_KEY=<output of: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```

> [!IMPORTANT]
> Never commit your `.env` file to any repository. It contains your database password and encryption key. The `.gitignore` file already excludes it.

### Step 3 — Start All Services

```bash
docker compose up -d
```

Docker will pull images and build containers. First boot takes 3–8 minutes as ML models are downloaded. Subsequent boots take under 30 seconds.

### Step 4 — Verify Services Are Running

```bash
docker compose ps
```

All four services (`postgres`, `backend`, `frontend`, `nginx`) should show `healthy` or `running`.

### Step 5 — Open the Application

Navigate to **http://localhost** in your browser.

Register your account. The first account automatically becomes the administrator of your deployment.

---

## 3. Checking Service Health

```bash
# View real-time logs for all services
docker compose logs -f

# Check only the backend
docker compose logs -f backend

# Check only the database
docker compose logs -f postgres

# API health check endpoint
curl http://localhost/health
```

---

## 4. Configuring HTTPS (Production VPS)

### Option A: Nginx with a Self-Signed Certificate (Local Network)

Generate a self-signed certificate for local HTTPS:

```bash
mkdir -p nginx/certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout nginx/certs/server.key \
  -out nginx/certs/server.crt \
  -subj "/CN=neurovault.local"
```

Then update `nginx/nginx.conf` to enable the HTTPS server block (uncomment the `443` section).

### Option B: Caddy (Automatic Free HTTPS for Public VPS)

If you have a domain name pointing to your VPS, replace Nginx with Caddy for automatic certificate management:

1. Remove the `nginx` service from `docker-compose.yml`.
2. Add the Caddy service instead:

```yaml
caddy:
  image: caddy:alpine
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile:ro
    - caddy-data:/data
  networks:
    - neurovault-net
```

3. Create a `Caddyfile` in the root:

```
your-domain.com {
    reverse_proxy /api/* backend:8000
    reverse_proxy /* frontend:80
}
```

Caddy automatically obtains and renews a free Let's Encrypt certificate.

---

## 5. Environment Variable Reference

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_DB` | Yes | Database name (default: `neurovault`) |
| `POSTGRES_USER` | Yes | Database username |
| `POSTGRES_PASSWORD` | **Yes** | Strong database password |
| `JWT_SECRET_KEY` | **Yes** | Random 32-byte hex string for JWT signing |
| `ENCRYPTION_KEY` | **Yes** | Fernet key for AES-256 field encryption |
| `UPLOAD_DIRECTORY` | No | Path inside container (default: `/data/uploads`) |
| `CHROMADB_PATH` | No | Path inside container (default: `/data/chromadb`) |

---

## 6. Backup & Restore

### Create a Backup

```bash
bash scripts/backup.sh
```

Creates a timestamped `.tar.gz` archive inside the `backups/` folder containing:
- A full PostgreSQL database dump
- All uploaded documents
- ChromaDB vector store

### Restore from a Backup

```bash
bash scripts/restore.sh backups/neurovault_backup_YYYYMMDD_HHMMSS.tar.gz
```

> [!WARNING]
> Restore will **overwrite** your current data. Always confirm you are targeting the correct backup file.

### Automated Backups (Linux/VPS)

Add a cron job to run backups automatically:

```bash
crontab -e
# Add this line to run a backup every day at 2 AM:
0 2 * * * cd /path/to/NeuroVault- && bash scripts/backup.sh >> /var/log/neurovault-backup.log 2>&1
```

---

## 7. Updating NeuroVault

```bash
# 1. Pull latest source code
git pull origin main

# 2. Rebuild and restart containers
docker compose up -d --build
```

Your data (PostgreSQL, uploads, ChromaDB) is stored in Docker named volumes and is never deleted during updates.

---

## 8. Stopping & Removing Services

```bash
# Stop all services (data is preserved)
docker compose down

# Stop and remove ALL data volumes (DESTRUCTIVE — all data will be lost)
docker compose down -v
```

---

## 9. Deployment on Specific Platforms

### Raspberry Pi

Use ARM-compatible images by adding `platform: linux/arm64` to services in `docker-compose.yml` that require it.

### Synology NAS

1. Install **Container Manager** from the Package Center.
2. Clone the repository to a shared folder.
3. Open Container Manager → Project → Create from `docker-compose.yml`.

### DigitalOcean / AWS / Azure / GCP

1. Create a VM (minimum 2 GB RAM, 2 CPUs, 20 GB SSD).
2. Install Docker: `curl -fsSL https://get.docker.com | sh`
3. Clone the repo, configure `.env`, and run `docker compose up -d`.
4. Configure your firewall to open ports 80 and 443.
5. Point your domain to the server IP and use Caddy for HTTPS.
