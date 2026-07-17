# IRIS Security Policy & Data Protection Architecture

IRIS is built on a strict **privacy-first, zero-trust** philosophy. The developer who builds and distributes this software has **zero access** to your data at any point in time. This document details every security layer protecting your information.

---

## 1. Core Privacy Guarantee — 100% Self-Hosted

Every IRIS deployment is completely independent and sovereign:

| Data Type | Stored Where | Who Can Access |
| :--- | :--- | :--- |
| Your documents (PDFs, images) | Docker volume on your machine | Only you |
| Database (documents, entities, graph) | PostgreSQL inside your Docker network | Only your backend |
| Vector embeddings | ChromaDB inside your Docker volume | Only your backend |
| AI conversations (Gemini path) | Masked + sent to API; response returned | Only you (masked) |
| Encryption keys, JWT secrets | Your local `.env` file only | Only you |
| Telemetry / usage data | **Not collected — does not exist** | Nobody |

---

## 2. Password Hashing — Argon2id

User passwords and secondary document PINs are hashed using **Argon2id**, the winner of the 2015 Password Hashing Competition.

| Parameter | Value | Effect |
| :--- | :--- | :--- |
| `time_cost` | 3 | 3 iterations of the hashing function |
| `memory_cost` | 65,536 KB (64 MB) | Memory required per hash attempt |
| `parallelism` | 4 | Parallel threads |
| `hash_len` | 32 bytes | Output hash length |
| `salt_len` | 16 bytes | Random salt (unique per hash) |

An attacker with 1,000 GPUs would require millions of years to crack a single strong password. Legacy `bcrypt` hashes are **automatically re-hashed to Argon2id** on the user's next successful login.

---

## 3. JWT Session Tokens — Access + Refresh Token Model

| Token | Lifetime | Storage | Purpose |
| :--- | :--- | :--- | :--- |
| **Access Token** | 15 minutes | Browser memory (not localStorage) | Authenticates API requests |
| **Refresh Token** | 30 days | HttpOnly cookie (Argon2id hash in DB) | Silently renews access tokens |

**Token Rotation**: Every refresh operation issues a new refresh token and invalidates the old one. If a refresh token is stolen and used by an attacker, the next legitimate use by the real user immediately invalidates the attacker's session.

---

## 4. AES-256 Field Encryption at Rest

The entire `extracted_json` field in the `documents` table is encrypted **before database writes** using AES-256 via Python's `cryptography.fernet` library.

**What is encrypted:**
- Aadhaar Number
- PAN Card Number
- Passport Number
- Driving Licence Number
- Bank Account Number
- Any other structured extracted fields

**Key Management**: The `ENCRYPTION_KEY` lives only in your `.env` file. A stolen database backup without the key is completely unreadable.

---

## 5. Local PII Masking — Cloud AI Privacy Layer

When using the Gemini API, a local pre-processing layer (`pii_masker.py`) ensures sensitive values **never leave your server in plaintext**:

**PII Types Detected & Masked Locally:**
- **Aadhaar Numbers** (spaced and raw 12-digit patterns)
- **PAN Card Numbers** (5-letter + 4-digit + 1-letter pattern)
- **Passport Numbers** (Indian format: 1 letter + 7 digits)
- **Driving Licence Numbers**
- **Bank Account Numbers** (preceded by contextual keywords)
- **Email Addresses**
- **Indian Mobile Numbers** (with/without +91 prefix)

**How It Works:**
1. Before sending context to Gemini: `1234 5678 9012` → `[AADHAAR_0]`
2. Gemini generates its response referencing only `[AADHAAR_0]`
3. After receiving the response locally: `[AADHAAR_0]` → `1234 5678 9012`
4. The final unmasked response is sent to your browser

**Result**: Google's servers never process any real PII.

---

## 6. UI Data Masking (Frontend Display Layer)

Even after decryption on the backend, the React frontend applies a display-level masking layer:

| Field | Displayed As |
| :--- | :--- |
| Aadhaar Number | `XXXX-XXXX-1234` |
| PAN Number | `ABCDE****F` |
| Bank Account | `**** **** **** 9014` |
| Passport Number | `A*****7` |

Users can toggle full values by clicking the field (requires active session + PIN if document is locked).

---

## 7. Document Lock — Secondary PIN

Sensitive documents can be locked with a secondary 4-digit PIN:
- The PIN hash (Argon2id) is stored in `users.pin_hash`.
- Locked documents are **excluded from all semantic search** and vector retrieval.
- Locked documents are **excluded from the Gemini, Ollama, and Local Rules context** — no AI engine can access or leak locked content.
- Locked document previews are blurred in the Vault UI.

---

## 8. Audit Logging

Every significant action is recorded in the `audit_logs` table:

| Field | Description |
| :--- | :--- |
| `user_id` | The user who performed the action |
| `timestamp` | UTC timestamp |
| `action_type` | `LOGIN`, `LOGOUT`, `UPLOAD`, `PREVIEW_FILE`, `LOCK_DOCUMENT`, `UNLOCK_DOCUMENT`, `DELETE_DOCUMENT`, `CHAT_QUERY` |
| `ip_address` | Client IP address |
| `document_id` | Associated document (where applicable) |

---

## 9. Network Security — Nginx Rate Limiting

| Zone | Limit | Target |
| :--- | :--- | :--- |
| `auth_limit` | 5 requests / minute | `/api/auth/` (login, register, refresh) |
| `api_limit` | 30 requests / second | All other API routes |

---

## 10. Secure Document Deletion — Complete Purge

When a document is deleted, IRIS cascades the purge across all storage layers:

1. **Physical file** — deleted from the `uploads/` Docker volume
2. **Database records** — `documents`, `document_tags`, `entities` rows deleted
3. **Graph edges** — all `GraphEdge` relationships deleted
4. **Vector embeddings** — ChromaDB entry deleted by document ID

No trace of the document remains in any storage layer after deletion.

---

## 11. Docker Network Isolation

All services communicate exclusively via an internal Docker bridge network (`iris-net`). The PostgreSQL database and ChromaDB are **not exposed on any host port** — they are only reachable from inside the Docker network. Nginx is the sole publicly accessible entry point.
