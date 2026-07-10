# IRIS AI — Vector Database & RAG Pipeline

This document explains the vector search mechanics and RAG (Retrieval-Augmented Generation) pipeline used in the AI Memory Assistant.

---

## 1. Local Vector Storage (ChromaDB)

We use **ChromaDB** in persistent disk mode (`vector_store/`).
ChromaDB is a database built specifically to store and index high-dimensional vector representations of text.

### Embedding Model: `all-MiniLM-L6-v2`
- **Dimensions:** 384 floating-point values.
- **Max sequence length:** 256 tokens (words/sub-words).
- **Metric space:** Cosine Similarity.
- **Why we use it:** It is a small, fast transformer model that runs locally on CPU without needing GPU hardware, while maintaining high accuracy for semantic overlap searches.

---

## 2. Text Chunking & Metadata Strategy

When a document is indexed:
1. We construct a composite context text block:
   ```text
   Category: [Category]
   Type: [Document Type]
   Summary: [Summary Card text]
   Content:
   [Raw OCR text and stringified JSON payload]
   ```
2. We embed this block as a single document chunk.
3. We associate metadata to filter queries:
   - `user_id`: Crucial to isolate search results between users.
   - `category`: To narrow searches to specific folders (e.g. only search Financial records).
   - `document_type`: e.g. "PAN Card".

---

## 3. RAG Query Execution Flow

```
User Query ────────────────────────┐
                                   ▼
                   Embed Query (384-dim vector)
                                   │
                                   ▼
             Query ChromaDB with Metadata Filter (user_id)
                                   │
                                   ▼
             Retrieve Top-3 Matching Document UUIDs
                                   │
                                   ▼
             Load Full JSON Details from SQLite Database
                                   │
                                   ▼
          Assemble System Context Prompt + Citations List
                                   │
                                   ▼
                      Generate Cited Response
               (via local Ollama or Local Rules Engine)
                                   │
                                   ▼
                      Display Answer to User
```

This RAG loop ensures that the assistant answers questions using only verified documents in your vault, adding inline citations (e.g., *[Retrieved from PAN Card]*) for transparency.
