# IRIS Security Policy & Data Protection Architecture

IRIS is built on a strict privacy-first philosophy: the developer who builds and distributes this software has **zero access** to your data. This document details every security layer protecting your information.

---

## 1. Core Privacy Guarantee — 100% Self-Hosted

Every IRIS deployment is completely independent.

- **Your documents** are stored in a Docker volume on your own machine.
- **Your database** is a private PostgreSQL instance inside your Docker network.
- **Your vectors** are stored in a ChromaDB instance inside your Docker volume.
- **Your AI conversations** are processed by the Gemini API directly (your key, your quota).
- **No telemetry** — IRIS does not send usage statistics, error reports, or any data to any IRIS-owned server.

The developer only distributes software code. They receive nothing else.

---

## 2. Password Hashing — Argon2id

User passwords and secondary PINs are hashed using **Argon2id**, the winner of the 2015 Password Hashing Competition and the most secure password hashing algorithm available.

### Configuration

| Parameter | Value | Effect |
|---|---|---|
| `time_cost` | 3 | 3 iterations of the hashing function |
| `memory_cost` | 65,536 KB (64 MB) | Memory required per hash operation |
| `parallelism` | 4 | Parallel threads used |
| `hash_len` | 32 bytes | Output hash length |
| `salt_len` | 16 bytes | Random salt per hash |

This configuration makes brute-force attacks computationally infeasible, even with specialised hardware (GPUs, ASICs). An attacker with 1,000 GPUs would need millions of years to crack a single strong password.

### Legacy Migration
Accounts that were previously hashed with `bcrypt` are **automatically re-hashed with Argon2id** on the user's next successful login. No manual migration is needed.

---

## 3. JWT Session Tokens — Access + Refresh Token Model

IRIS uses a two-token session model for maximum security:

| Token | Lifetime | Purpose |
|---|---|---|
| **Access Token** | 15 minutes | Authenticates API requests |
| **Refresh Token** | 30 days | Obtains new access tokens without re-login |

### How It Works

1. User logs in → receives both tokens.
2. The access token is used for all API requests (stored in browser memory, not `localStorage`).
3. When the access token expires, the frontend sends the refresh token to `/api/auth/refresh`.
4. The server issues a **new access token + a new refresh token** (rotation).
5. The old refresh token is immediately invalidated.
6. On logout, the refresh token hash in the database is cleared — all future refresh attempts fail.

### Why This Is Secure

- **Access token compromise**: If stolen, it expires in 15 minutes with no way to extend it.
- **Refresh token compromise**: Token rotation means the attacker's token is invalidated as soon as the legitimate user makes a refresh request.
- **Only the hash is stored**: The raw refresh token is never stored in the database. Only an Argon2id hash is kept, so a database breach does not expose active sessions.

---

## 4. AES-256 Field Encryption at Rest

Sensitive extracted fields are encrypted before being written to the PostgreSQL database using **AES-256 via Fernet (Cryptography library)**.

### What Is Encrypted

The entire `extracted_json` field stored in the `documents` table is encrypted. This includes (where present):

- Aadhaar Number
- PAN Number
- Passport Number
- Driving Licence Number
- Bank Account Number
- Any other extracted structured metadata

### How It Works

1. The `EncryptionService` initialises a `Fernet` cipher using the `ENCRYPTION_KEY` from your `.env` file.
2. Before saving to the database, `extracted_json` is encrypted → stored as ciphertext.
3. When the API serves the document details, the backend decrypts the field in memory and sends the response.
4. The raw key never appears in any log file, database column, or API response.

### Key Management

- The encryption key lives in your `.env` file — on your own machine only.
- The developer has no knowledge of your key.
- If you lose the key, the encrypted data cannot be recovered. **Back up your `.env` file.**

---

## 5. UI Data Masking (PII Protection)

Even after decryption on the backend, the frontend applies an additional masking layer before displaying sensitive values:

| Field | Displayed As |
|---|---|
| Aadhaar Number | `XXXX-XXXX-1234` |
| PAN Number | `ABCDE****F` |
| Bank Account | `**** **** **** 9014` |
| Passport Number | `A*****6` |

Users can toggle the full value by clicking the field (requires active session + PIN if locked).

---

## 6. Document Lock (Secondary PIN)

Sensitive documents can be locked with a secondary 4-digit PIN:

- The PIN hash (Argon2id) is stored in the `users` table under `pin_hash`.
- Locked documents are **excluded from all semantic search queries**.
- Locked documents are **not included in Memory Assistant RAG context** — the AI cannot access or leak information from locked files.
- Locked document previews are blurred in the Vault UI.

---

## 7. Audit Logging

Every significant action is recorded in the `audit_logs` table with:

- User ID
- Timestamp (UTC)
- Action type (`LOGIN`, `LOGOUT`, `UPLOAD`, `PREVIEW_FILE`, `LOCK_DOCUMENT`, `UNLOCK_DOCUMENT`, `DELETE_DOCUMENT`, `CHAT_QUERY`)
- IP address of the request
- Associated document ID (where applicable)

Users can view their own audit log at any time via **Settings → Security Audit Log**.

---

## 8. Network Security — Nginx Rate Limiting

The Nginx reverse proxy applies rate limiting to prevent brute-force attacks:

| Zone | Limit | Target |
|---|---|---|
| `auth_limit` | 5 requests / minute | `/api/auth/` (login, register, refresh) |
| `api_limit` | 30 requests / second | All other API routes |

This protects against automated password-guessing attacks at the network layer, before requests even reach the application.

---

## 9. Secure Document Deletion — Complete Purge

When a document is deleted, IRIS performs a cascaded purge across all layers:

1. **Physical file** — deleted from the `uploads/` Docker volume.
2. **Database records** — `documents`, `document_tags`, and `entities` rows deleted.
3. **Graph edges** — all `GraphEdge` relationships referencing this document deleted.
4. **Vector embeddings** — ChromaDB entry deleted by document ID.

After deletion, no trace of the document remains in any storage layer.

---

## 10. Docker Network Isolation

All services communicate via an internal Docker bridge network (`iris-net`). The PostgreSQL database and ChromaDB are **not exposed on any host port** — they are only reachable from inside the Docker network. Nginx is the only publicly accessible entrypoint.
