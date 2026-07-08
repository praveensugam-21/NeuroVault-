#!/bin/bash
# NeuroVault — Restore Script
# Restores a backup archive created by scripts/backup.sh
#
# Usage: bash scripts/restore.sh backups/neurovault_backup_YYYYMMDD_HHMMSS.tar.gz
#
# WARNING: This will overwrite existing database data, uploads, and ChromaDB!

set -euo pipefail

BACKUP_FILE="${1:-}"
TEMP_DIR="/tmp/neurovault_restore_$(date +%s)"

if [ -z "${BACKUP_FILE}" ]; then
  echo "ERROR: Please provide a backup file path."
  echo "Usage: bash scripts/restore.sh backups/neurovault_backup_YYYYMMDD_HHMMSS.tar.gz"
  exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "ERROR: Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

echo "=== NeuroVault Restore Started from: ${BACKUP_FILE} ==="
echo "WARNING: This will OVERWRITE your current database, uploads, and vector store."
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "Restore cancelled."
  exit 0
fi

# Extract backup archive
mkdir -p "${TEMP_DIR}"
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"

# ── 1. Restore PostgreSQL ────────────────────────────────────────────────────
echo "[1/3] Restoring PostgreSQL database..."
docker compose exec -T postgres psql \
  -U "${POSTGRES_USER:-nv_user}" \
  -d "${POSTGRES_DB:-neurovault}" \
  < "${TEMP_DIR}/postgres_dump.sql"

# ── 2. Restore uploaded files ────────────────────────────────────────────────
echo "[2/3] Restoring uploaded documents..."
docker run --rm \
  -v neurovault_uploads:/target \
  -v "${TEMP_DIR}":/backup \
  alpine \
  sh -c "rm -rf /target/* && tar -xzf /backup/uploads.tar.gz -C /target"

# ── 3. Restore ChromaDB ──────────────────────────────────────────────────────
echo "[3/3] Restoring ChromaDB vector store..."
docker run --rm \
  -v neurovault_chromadb-data:/target \
  -v "${TEMP_DIR}":/backup \
  alpine \
  sh -c "rm -rf /target/* && tar -xzf /backup/chromadb.tar.gz -C /target"

# Cleanup temp dir
rm -rf "${TEMP_DIR}"

echo "=== Restore Complete! ==="
echo "Restarting services..."
docker compose restart backend
