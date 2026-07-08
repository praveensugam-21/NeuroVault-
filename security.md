# NeuroVault Security Policy & Data Protection Architecture

NeuroVault is designed as a secure, local-first personal document vault. Privacy, data security, and confidentiality are built into the core architecture. This document details the security layers, encryption protocols, and data handling standards that ensure **100% safety and data sovereignty** for all stored records.

---

## 1. 100% Local-First Isolation (No Cloud Leakage)

To ensure absolute confidentiality, the entire ingestion, parsing, indexing, and query pipeline runs locally on your machine.
- **Offline OCR and Parsing**: All OCR tasks (via EasyOCR) and text extractions are processed locally on CPU/GPU. No documents or text segments are ever uploaded to third-party APIs.
- **Local Machine Learning**: Embeddings generation (via SentenceTransformers) and Named Entity Recognition (spaCy NER) run entirely offline.
- **Local Vector & Relational Storage**: The SQLite database (`neurovault.db`) and ChromaDB vector store exist solely within your local installation directory.
- **Local Inference (Ollama)**: The Memory Assistant utilizes local LLM engines (like `qwen2.5:1.5b` through Ollama) on localhost. Absolutely no data is transmitted to external servers, protecting you against data harvesting.

---

## 2. Cryptographic Security & Password Hashing

NeuroVault employs industry-standard cryptographic algorithms to secure user accounts and individual documents:
- **Authentication Hashing**: User passwords are encrypted using `bcrypt` with a secure work factor, protecting against dictionary and rainbow table attacks.
- **Secondary PIN Lock**: Documents marked as private are locked behind a secondary 4-digit PIN. The validation hash is generated using `bcrypt` and stored in the database.
- **Session Tokens**: API endpoints are secured using JSON Web Tokens (JWT) containing cryptographically signed user payloads.

---

## 3. PII Masking and UI Protections

To protect Personally Identifiable Information (PII) from shoulder-surfing or accidental exposure:
- **Automatic Field Masking**: Highly sensitive extracted fields are masked by default on the client-side:
  - **Aadhaar Cards**: Masked to `XXXX-XXXX-1234`.
  - **PAN Cards**: Masked to `ABCDE****F`.
  - **Bank Accounts**: Masked to show only the last 4 digits (e.g., `********9014`).
- **Preview Blurs**: Document previews and thumbnails for locked items are blurred or restricted in the Vault page until the secondary PIN is entered.

---

## 4. RAG Context Segregation

- **Isolation of Locked Files**: Any document locked by a user is completely excluded from the retrieval-augmented generation (RAG) context. 
- **Prompt Injection Defense**: A locked document's vector representation is not queried during vector similarity searches, ensuring the Memory Assistant cannot access or leak information from locked files during an active chat session.

---

## 5. Audit Logging & Non-Repudiation

NeuroVault maintains a tamper-evident audit log in the database. Every critical action is logged with:
- **Timestamp** (UTC)
- **User Identifier**
- **Action Type** (`UPLOAD`, `PREVIEW_FILE`, `LOCK_DOCUMENT`, `UNLOCK_DOCUMENT`, `DELETE_DOCUMENT`, `CHAT_QUERY`)
- **Document Metadata**
This audit trail allows users to inspect exactly when and how their records were accessed or updated.

---

## 6. Secure Document Deletion (Permanent Purges)

When a document is deleted, NeuroVault performs a complete purge across all application layers:
1. **Physical File**: The raw PDF/Image file is permanently deleted from the disk storage directory (`uploads/`).
2. **Relational Database**: All references in `documents`, `document_tags`, and `entities` are deleted via cascade constraints.
3. **Knowledge Graph**: All `GraphEdge` entries (including `PRECEDES`, `FOLLOWS`, `ISSUED_TO`, and `RELATED_TO` relationships) linking this file to other nodes are removed.
4. **Vector Store**: Associated vector embeddings are purged from ChromaDB using the document ID.

---

## 7. Development & Deployment Guidelines

- **Environment Isolation**: The `.env` file should remain excluded from version control systems (included in `.gitignore`).
- **Dependency Sandboxing**: The FastAPI backend and Vite frontend run within distinct network bridges when run inside Docker containers, exposing only the minimum necessary ports to the host machine.
