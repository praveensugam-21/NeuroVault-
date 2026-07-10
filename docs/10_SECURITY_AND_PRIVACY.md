# IRIS — Security & Privacy Policy

This document is the formal security and privacy policy for the IRIS self-hosted platform. It explains what data is collected, where it is stored, who can access it, and how it is protected.

---

## Privacy Statement

**IRIS is 100% self-hosted. The developer and publisher of this software has no access to your data — ever.**

The developer:
- Does not receive your documents.
- Does not receive your extracted text or metadata.
- Does not receive your database contents.
- Does not receive your vector embeddings.
- Does not receive your chat history or AI query logs.
- Does not collect telemetry, crash reports, or usage statistics.

Your IRIS instance is exclusively under your control. You are the only person with access to your data.

---

## Data Storage

| Data Type | Storage Location | Encrypted |
|---|---|---|
| Uploaded files (PDFs, images) | Docker volume `uploads` on your server | File system level (OS encryption optional) |
| Extracted metadata (JSON) | PostgreSQL `documents.extracted_json` | **Yes — AES-256 Fernet** |
| User passwords | PostgreSQL `users.hashed_password` | **Yes — Argon2id hash** |
| Session tokens | Browser memory (not localStorage) | **Yes — Argon2id hash in DB** |
| Vector embeddings | ChromaDB volume on your server | No (embeddings are not personally identifiable) |
| Audit logs | PostgreSQL `audit_logs` table | No (timestamps and action types only) |
| AI chat history | Not persisted to database by default | N/A |

## Data Transmitted Externally

**No data is transmitted externally. IRIS operates 100% offline.**

- All processing, OCR, classification, and metadata extraction are completed locally on your server.
- The Memory Assistant queries run against your local Ollama server.
- No network connections are initiated to Google's Gemini, OpenAI, or other cloud AI providers.

---

## Authentication Security

See [security.md](../security.md) for full technical details. Summary:

| Mechanism | Standard Used |
|---|---|
| Password hashing | Argon2id (time: 3, mem: 64MB, par: 4) |
| Session management | JWT access token (15 min) + refresh token (30 days) |
| Refresh token storage | Argon2id hash only — raw token never stored |
| Token rotation | Yes — refresh invalidated after each use |
| Logout | Refresh token hash wiped from database |

---

## Field-Level Encryption

Sensitive PII fields extracted from documents are encrypted in the database using AES-256:

- Aadhaar Number
- PAN Number
- Passport Number
- Driving Licence Number
- Bank Account Number

The encryption key is stored in your `.env` file — on your machine only. The developer never has access to this key.

---

## Access Control

| User Role | Capability |
|---|---|
| Registered User | Access only their own documents, graphs, and chat history |
| Admin (first user) | Same as regular user — no elevated data access currently |
| Developer | Zero access — no backend access, no DB access, no file access |

Row-level user isolation is enforced in every database query. A user cannot access another user's documents even if they know the document ID.

---

## Incident Response

Since all data is self-hosted, you are responsible for your own incident response. We recommend:

1. **Regular backups** — run `bash scripts/backup.sh` daily.
2. **Strong passwords** — use at least 16 characters for `POSTGRES_PASSWORD` and your user account.
3. **Firewall rules** — on VPS deployments, only expose ports 80 and 443 publicly.
4. **Updates** — keep IRIS updated with `git pull && docker compose up -d --build`.

---

## Data Deletion

You can permanently delete all data by:

1. Deleting individual documents via the Vault UI (triggers cascaded purge across DB, file system, and ChromaDB).
2. Deleting your account (triggers cascaded deletion of all documents and records).
3. Destroying the entire deployment: `docker compose down -v` removes all Docker volumes and all data.
