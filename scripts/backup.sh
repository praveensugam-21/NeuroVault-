#!/bin/bash
# NeuroVault — Backup Script
# Creates a timestamped archive of PostgreSQL data, uploaded files, and ChromaDB.
#
# Usage: bash scripts/backup.sh
# Output: backups/neurovault_backup_YYYYMMDD_HHMMSS.tar.gz

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups"
BACKUP_FILE="${BACKUP_DIR}/neurovault_backup_${TIMESTAMP}.tar.gz"
TEMP_DIR="/tmp/neurovault_backup_${TIMESTAMP}"

echo "=== NeuroVault Backup Started: ${TIMESTAMP} ==="

# Create temp and output directories
mkdir -p "${TEMP_DIR}"
mkdir -p "${BACKUP_DIR}"

# ── 1. Dump PostgreSQL database ──────────────────────────────────────────────
echo "[1/3] Dumping PostgreSQL database..."
docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-nv_user}" \
  "${POSTGRES_DB:-neurovault}" \
  > "${TEMP_DIR}/postgres_dump.sql"

# ── 2. Copy uploaded files ───────────────────────────────────────────────────
echo "[2/3] Archiving uploaded documents..."
docker run --rm \
  -v neurovault_uploads:/source \
  -v "$(pwd)/${TEMP_DIR}":/backup \
  alpine \
  tar -czf /backup/uploads.tar.gz -C /source .

# ── 3. Copy ChromaDB vector store ────────────────────────────────────────────
echo "[3/3] Archiving ChromaDB vector store..."
docker run --rm \
  -v neurovault_chromadb-data:/source \
  -v "$(pwd)/${TEMP_DIR}":/backup \
  alpine \
  tar -czf /backup/chromadb.tar.gz -C /source .

# ── Package everything into a single archive ─────────────────────────────────
echo "Packaging final archive..."
tar -czf "${BACKUP_FILE}" -C "${TEMP_DIR}" .
rm -rf "${TEMP_DIR}"

echo "=== Backup Complete: ${BACKUP_FILE} ==="
echo "To restore, run: bash scripts/restore.sh ${BACKUP_FILE}"
