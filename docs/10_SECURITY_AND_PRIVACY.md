# IRIS — Security & Privacy Policy

This document is the formal security and privacy policy for the IRIS self-hosted platform. It explains what data is collected, where it is stored, who can access it, how it is protected, and — critically — exactly what gets transmitted to cloud AI providers and under what privacy guarantees.

> **Last Updated:** 2026-07-17 — Added Gemini API Privacy Contract section.

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
| ML model weights | Docker volume `model-cache` | No (not user data) |

---

## Data Transmitted Externally

**By default, all AI processing uses local models or the Smart Local Rules Engine. No data leaves your machine unless you explicitly configure a Gemini API key.**

When a Gemini API key is configured, **only PII-masked text is ever transmitted**. The masking happens before the HTTP request is made — the actual sensitive values never leave your machine.

See the [Gemini API Privacy Contract](#gemini-api-privacy-contract) section below for full technical details.

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

Sensitive PII fields extracted from documents are encrypted in the database using AES-256 (Fernet):

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

## Gemini API Privacy Contract

This section explains exactly what data is transmitted to the Gemini API, and what remains exclusively on your machine.

### The Core Guarantee

> **Your Aadhaar number, PAN number, passport number, phone number, and all other PII values are NEVER sent to Google's servers.**

### How PII Masking Works

Before any text is transmitted to Gemini, it passes through the local `PIIMasker` service:

**Step 1 — Detection**

`PIIMasker` scans the raw text using compiled regex patterns and identifies all PII values:

| PII Type | Pattern Example | Placeholder Token |
|---|---|---|
| Aadhaar (spaced) | `1234 5678 9012` | `[AADHAAR_0]` |
| Aadhaar (raw) | `123456789012` | `[AADHAAR_0]` |
| PAN Card | `ABCDE1234F` | `[PAN_0]` |
| Passport | `A1234567` | `[PASSPORT_0]` |
| Driving Licence | `TN0219999999999` | `[DL_0]` |
| Email Address | `user@example.com` | `[EMAIL_0]` |
| Phone Number | `+91 9876543210` | `[PHONE_0]` |
| Bank Account | `123456789012` (after keyword) | `[BANK_ACCT_0]` |

**Step 2 — Substitution**

Each detected PII value is replaced with its placeholder token in the text. The original value is stored in an in-memory mapping dictionary (never written to disk):

```python
# Before masking (raw OCR text):
"Aadhaar: 2345 6789 0123, Name: Praveen Kumar"

# After masking (sent to Gemini):
"Aadhaar: [AADHAAR_0], Name: Praveen Kumar"

# Mapping (stays on your machine):
{"[AADHAAR_0]": "2345 6789 0123"}
```

> [!NOTE]
> Names are **not** masked. Only structured identifiers with machine-readable patterns are masked. The rationale: names have no fixed format and masking them would prevent the LLM from providing useful OCR corrections.

**Step 3 — Cloud Transmission**

Only the placeholder-substituted text is sent to Gemini. The request body contains tokens like `[AADHAAR_0]` — not actual Aadhaar numbers.

**Step 4 — Local Unmasking**

When Gemini returns its response (which will contain placeholder tokens in any extracted JSON or corrected text), `PIIMasker.unmask_text()` replaces every `[AADHAAR_0]`, `[PAN_0]` etc. with the original values using the in-memory mapping. This happens entirely locally, before any response is written to the database.

```python
# Gemini response (contains placeholders):
{"aadhaar": "[AADHAAR_0]", "name": "Praveen Kumar"}

# After local unmasking:
{"aadhaar": "2345 6789 0123", "name": "Praveen Kumar"}
```

### What Google Receives vs. What Stays Local

| Data | Sent to Google | Stays Local |
|---|---|---|
| Aadhaar number | ❌ Never — replaced with `[AADHAAR_0]` | ✅ Original value in memory map |
| PAN number | ❌ Never — replaced with `[PAN_0]` | ✅ Original value in memory map |
| Passport number | ❌ Never — replaced with `[PASSPORT_0]` | ✅ Original value in memory map |
| DL number | ❌ Never — replaced with `[DL_0]` | ✅ Original value in memory map |
| Phone number | ❌ Never — replaced with `[PHONE_0]` | ✅ Original value in memory map |
| Email address | ❌ Never — replaced with `[EMAIL_0]` | ✅ Original value in memory map |
| Bank account | ❌ Never — replaced with `[BANK_ACCT_0]` | ✅ Original value in memory map |
| Person's name | ✅ Sent (no fixed format to detect) | N/A |
| Document type | ✅ Sent (not PII) | N/A |
| Placeholder-masked text | ✅ Sent | N/A |
| PII → placeholder mapping | ❌ Never | ✅ In-memory only, session-scoped |
| Encrypted DB values | ❌ Never | ✅ PostgreSQL only |

### Gemini API Configuration

```python
# Generation config used for Gemini calls
temperature = 0.2      # Low randomness for accurate field extraction
max_output_tokens = 2048
safety_settings = BLOCK_ONLY_HIGH  # Permissive for document content
```

The API key can be set in `.env` or dynamically updated via the **Settings page** UI. When updated, a live probe call (`POST /api/auth/settings/gemini-key`) validates key health before persisting settings. Direct HTTP/1.1 REST requests are used to prevent connection stalls. If the key is invalid or fails validation, Gemini is marked `_broken=True` and requests fall through to Ollama or local rules.

### Production Security Headers

The backend automatically attaches security headers to all responses:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`: Enforces HTTPS transport.
- `Cache-Control: no-store`: Prevents sensitive document payloads and PII responses from being cached in downstream client/browser caches.
- `CORS Restriction`: Origins are strictly whitelisted via `ALLOWED_ORIGINS` environment settings.

### Fully Offline Alternative

If you do not set a `GEMINI_API_KEY`, or set `GEMINI_API_KEY=""`, the Gemini tier is completely skipped. All processing uses:

1. **Ollama** (if `OLLAMA_BASE_URL` is configured and a model is pulled)
2. **Smart Local Rules Engine** (always available — no internet required)

In this configuration, zero bytes of your data leave your machine.

---

## Incident Response

Since all data is self-hosted, you are responsible for your own incident response. We recommend:

1. **Regular backups** — run `bash scripts/backup.sh` daily.
2. **Strong passwords** — use at least 16 characters for `POSTGRES_PASSWORD` and your user account.
3. **Firewall rules** — on VPS deployments, only expose ports 80 and 443 publicly.
4. **Updates** — keep IRIS updated with `git pull && docker compose up -d --build`.
5. **Rotate secrets** — if your `.env` file is compromised, regenerate `JWT_SECRET_KEY` and `ENCRYPTION_KEY` immediately (note: rotating `ENCRYPTION_KEY` invalidates all previously encrypted data).

---

## Data Deletion

You can permanently delete all data by:

1. Deleting individual documents via the Vault UI (triggers cascaded purge across DB, file system, and ChromaDB).
2. Deleting your account (triggers cascaded deletion of all documents and records).
3. Destroying the entire deployment: `docker compose down -v` removes all Docker volumes and all data.
