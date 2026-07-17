# Technology Choices & AI Privacy Guide

This document explains the core technology decisions for IRIS and how the platform maintains **absolute local privacy** while supporting optional cloud-enhanced intelligence.

---

## 1. AI Engine Architecture — Three-Tier Fallback System

IRIS uses a **three-tier LLM routing strategy**, prioritising intelligence while guaranteeing privacy:

| Priority | Engine | Mode | When Used |
| :---: | :--- | :--- | :--- |
| 1 | **Google Gemini 1.5 Flash** | Cloud API (with local PII masking) | When `GEMINI_API_KEY` is set in `.env` |
| 2 | **Ollama Local LLM** | 100% Offline | When Gemini is unavailable or offline |
| 3 | **Smart Local Rules Engine** | 100% Offline | When both LLMs are unavailable |

### How PII Masking Protects Your Data (Gemini Path)

Before any text chunk is sent to Google's API, a **local pre-processing layer** (`pii_masker.py`) runs on your server to detect and replace all sensitive values:

| Data Type | Example Input | What Google Receives |
| :--- | :--- | :--- |
| Aadhaar Number | `1234 5678 9012` | `[AADHAAR_0]` |
| PAN Card | `ABCDE1234F` | `[PAN_1]` |
| Passport | `A1234567` | `[PASSPORT_2]` |
| Phone Number | `+91-9876543210` | `[PHONE_3]` |
| Email Address | `john@example.com` | `[EMAIL_4]` |
| Bank Account | `Account No: 123456789012` | `Account No: [BANK_ACCT_5]` |

After Gemini generates its response, the same local server **swaps the placeholders back** to the original values before the response is ever sent to your browser. **Google only ever sees anonymized tokens — never real PII.**

---

## 2. Why We Chose These Specific Technologies

### A. SQLite (Development) & PostgreSQL (Production)
- **SQLite**: Configured with `StaticPool`, `check_same_thread=False`, and **WAL mode** for safe multi-threaded FastAPI requests during development.
- **PostgreSQL**: Full production scalability with connection pooling (`QueuePool`, 10 connections + 20 overflow) and `pool_pre_ping` for reliability.
- **Why not MongoDB**: IRIS data is fully relational. Documents → Tags → Entities → Graph Edges. Relational constraints guarantee cascade deletes and data integrity automatically.

### B. Why Argon2id for Password Hashing
- **Bcrypt / SHA-256** can be brute-forced by GPUs at billions of attempts per second.
- **Argon2id** (winner of the 2015 Password Hashing Competition) is **memory-hard**: each hash requires 64 MB of RAM, making GPU-based brute force financially impractical even with 1,000 GPUs.

### C. Why AES-256 (Fernet) Encryption at Rest
- Sensitive extracted fields (Aadhaar numbers, PAN numbers, bank account details) are **encrypted before being stored** in the database using `cryptography.fernet`.
- The decryption key lives only in your `.env` file on your machine. A stolen database backup is useless without it.

### D. Why ChromaDB for Vector Storage
- ChromaDB provides a persistent, file-based vector store with native support for cosine similarity search and metadata filtering.
- All vector embeddings stay on your local machine inside a Docker volume — they are never sent to any cloud vector database.

### E. Why Docker Compose & Nginx
- **Docker Compose**: Ensures the entire stack (FastAPI, React, PostgreSQL, ChromaDB, Ollama) is reproducibly configured and network-isolated on any OS.
- **Nginx**: Acts as the secure gateway — applies rate limiting (5 login attempts/min, 30 req/sec for API) before any request reaches Python.

### F. Why Gemini 1.5 Flash (and not GPT-4 or Claude)
- **Performance**: Gemini 1.5 Flash delivers near-GPT-4 quality responses at significantly higher speed and lower cost.
- **Safety**: Google API data is isolated per API key and **not used to train models** under the standard API terms of service (unlike consumer chat products).
- **Hybrid privacy**: Our local PII masking layer makes this choice safe even for sensitive documents — no raw PII ever reaches Google's servers.
