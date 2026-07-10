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
1. **Recursive Text Chunking:**
   The document's full parsed text is split into smaller, semantic chunks using a `RecursiveCharacterTextSplitter`.
   - **Chunk Size:** Target of 700 characters (~150 tokens) per chunk.
   - **Overlap:** 100 characters (~20 tokens) overlap to preserve semantic context across chunk borders.
2. **Metadata Association:**
   Each individual chunk is embedded and stored as a separate vector in the ChromaDB collection `iris_documents_chunks` with rich metadata:
   - `chunk_id`: Unique identifier (`<document_id>_chunk_<index>`).
   - `document_id`: Relates chunks back to the original document.
   - `user_id`: Isolate search results between users.
   - `chunk_index`: The sequence number of the chunk.
   - `section`: Heuristic section identifier (e.g. "Skills", "Experience", "Education").
   - `category` & `document_type`: For folder-level or document-type filtering.

---

## 3. RAG Query Execution Flow (Advanced Search Pipeline)

```
User Query ───────────────────────────────────┐
                                               ▼
                               Embed Query (384-dim vector)
                                               │
                                               ▼
                         Query ChromaDB for Candidate Chunks (Top-25)
                                               │
                                               ▼
                      Apply Local BM25 Keyword Matching (Hybrid Search)
                                               │
                                               ▼
                         Rerank Candidates using Cross-Encoder Model
                          (ms-marco-MiniLM-L-6-v2, optimized for CPU)
                                               │
                                               ▼
                         Apply MMR (Maximum Marginal Relevance) Filter
                            (Eliminates redundant/duplicated chunks)
                                               │
                                               ▼
                         Merge diverse Chunks sorted by chunk_index
                                               │
                                               ▼
                       Assemble Context Prompt + Chunk Citations
                                               │
                                               ▼
                                    Generate Cited Response
                            (via local Ollama or Local Rules Engine)
                                               │
                                               ▼
                                    Display Answer to User
```

This chunk-level retrieval loop ensures the query assistant extracts specific relevant sections (e.g. only the *Skills* section of a Resume) instead of loading the entire document, resulting in a cleaner prompt and more accurate answers with section-specific citations.
