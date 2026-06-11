# NeuroVault AI — Architecture & Core Design System

Welcome to the **NeuroVault AI** Architecture document. This guide explains how the React frontend, FastAPI backend, SQLite database, and ChromaDB vector store cooperate to build a unified semantic memory layer.

---

## 1. High-Level Architecture Overview

NeuroVault AI is designed as a modular, local-first intelligence application that can be easily containerized or scaled to the cloud.

```
       ┌─────────────────────────────────────────────────────────┐
       │                  USER WEB BROWSER                       │
       │                                                         │
       │  ┌─────────────────────────┐   ┌─────────────────────┐  │
       │  │ Dashboard & Timeline    │   │ Chat Assistant (RAG)│  │
       │  └────────────┬────────────┘   └──────────┬──────────┘  │
       │               │                           │             │
       │  ┌────────────▼────────────┐   ┌──────────▼──────────┐  │
       │  │ Smart Folder Vault      │   │ React Flow Graph    │  │
       │  └────────────┬────────────┘   └──────────┬──────────┘  │
       └───────────────┼───────────────────────────┼─────────────┘
                       │ HTTP / REST               │
                       ▼                           ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │                       FASTAPI BACKEND                             │
 │                                                                   │
 │  ┌─────────────────────────────────────────────────────────────┐  │
 │  │                  APIs & Routers                            │  │
 │  │  /documents  |  /chat (RAG)  |  /graph  |  /dashboard      │  │
 │  └──────────────┬─────────────────────────────────────────────┘  │
 │                 │                                                 │
 │                 ▼                                                 │
 │  ┌─────────────────────────────────────────────────────────────┐  │
 │  │        15-Step Async Processing Pipeline (Manager)         │  │
 │  └──────────────┬───────────────────────────────┬─────────────┘  │
 │                 │                               │                 │
 │                 ▼ (Relational)                  ▼ (Embeddings)    │
 │        ┌─────────────────┐             ┌─────────────────┐        │
 │        │  SQLite DB      │             │  ChromaDB       │        │
 │        │  (Metadata,     │             │  (Vector Store) │        │
 │        │   Graph Edges)  │             └─────────────────┘        │
 │        └────────┬────────┘                                        │
 │                 │                                                 │
 └─────────────────┼─────────────────────────────────────────────────┘
                   │ Secure API Calls
                   ▼
         ┌──────────────────────────────────────┐
         │          EXTERNAL AI LAYER           │
         │  Google Gemini Vision / Whisper /    │
         │  spaCy NER / Sentence Transformers   │
         └──────────────────────────────────────┘
```

---

## 2. Relational Database Schema (SQLite)

We use SQLAlchemy ORM with a local SQLite database file `neurovault.db`. It consists of five primary tables:

### A. `users`
Tracks user accounts, passwords (bcrypt hashes), and secondary document locks.
- `id`: Integer (Primary Key)
- `email`: String (Unique, Indexed)
- `hashed_password`: String
- `pin_hash`: String (Optional, for secondary document PIN protection)
- `created_at`: DateTime

### B. `documents`
Stores document metadata, processing status, and raw extracted structured data.
- `id`: String (UUID, Primary Key)
- `user_id`: Integer (Foreign Key -> `users.id`)
- `name`: String
- `file_path`: String (Path to file on disk)
- `file_type`: String (PDF, Image, Audio, Text, URL)
- `category`: String (e.g., Identity, Academic, Professional, etc.)
- `document_type`: String (e.g., Aadhaar Card, PAN Card, Class 10 Marksheet)
- `confidence_score`: Float
- `status`: String (PROCESSING, COMPLETE, FAILED)
- `extracted_json`: Text/JSON (Full schema fields stored as a structured JSON object)
- `summary`: Text (3-5 line natural language summary card)
- `is_locked`: Boolean (Defaults to False)
- `created_at`: DateTime
- `updated_at`: DateTime

### C. `document_tags`
Represents tags associated with documents for fast categorization.
- `id`: Integer (Primary Key)
- `document_id`: String (Foreign Key -> `documents.id`)
- `tag_name`: String (e.g., `#identity`, `#academic`)

### D. `entities`
Stores specific entities (people, organizations, dates, document numbers) extracted via spaCy and Gemini.
- `id`: Integer (Primary Key)
- `document_id`: String (Foreign Key -> `documents.id`)
- `entity_type`: String (PERSON, ORG, DATE, ID_NUMBER)
- `entity_value`: String (e.g., "Ravi Kumar", "CBSE Board", "2026-06-11")

### E. `graph_edges`
Represents named entity links and relationship semantic overlaps in the Knowledge Graph.
- `id`: Integer (Primary Key)
- `source_id`: String (Foreign Key -> `documents.id` or `entities.id`)
- `target_id`: String (Foreign Key -> `documents.id` or `entities.id`)
- `relationship_type`: String (e.g., `ISSUED_TO`, `STUDIED_AT`, `EMPLOYED_AT`, `RELATED_TO`, `PRECEDES`, `FOLLOWS`, `CONTRADICTS`)
- `created_at`: DateTime

### F. `audit_logs`
Tracks document accesses for strict compliance and privacy audits.
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key -> `users.id`)
- `document_id`: String (Foreign Key -> `documents.id`)
- `action`: String (e.g., "VIEW", "DOWNLOAD", "DELETE", "LOCK")
- `ip_address`: String (Anonymized)
- `user_agent`: String
- `timestamp`: DateTime

---

## 3. Vector Database Structure (ChromaDB)

We run **ChromaDB** in a local persistent directory `vector_store/`.
We maintain a single collection: `neurovault_documents`.

### Document Chunking Strategy
- For structured documents (e.g. Aadhaar, PAN), we embed the natural language **Summary Card** + the flat stringified **Extracted JSON fields** as a single document chunk.
- For free-text documents (e.g. Resumes, notes), we chunk the text by paragraphs (max 1000 characters) with a 200-character overlap.

### Metadata Schema
Every chunk stored in ChromaDB contains metadata fields to enable metadata filtering:
- `document_id`: String (matches SQLite `documents.id`)
- `user_id`: Integer
- `category`: String
- `document_type`: String
- `created_at`: String

---

## 4. Pipeline Data Flow

When a file is uploaded, it transitions through:
1. **API Router**: Receives file, generates a UUID, saves to `uploads/` directory, creates database record with status `PROCESSING`.
2. **Pipeline Manager**: Launches an asynchronous worker thread/asyncio task to process the file step-by-step.
3. **Pre-processing Engine**: If it is an image, it uses OpenCV to denoise, deskew, and enhance contrast.
4. **Vision/OCR Engine**: Gemini Vision API reads the document. If it fails or is offline, EasyOCR processes it.
5. **Taxonomy Classifier**: Decides if it is an Aadhaar, Class 10 mark sheet, etc.
6. **Field Extractor**: Calls Gemini or local parser to extract type-specific JSON fields.
7. **Validation & Quality Engine**: Assesses formatting rules and computes confidence.
8. **Entity Extractor & Embedder**: Extracts named entities via spaCy and computes vector embeddings using `all-MiniLM-L6-v2`.
9. **Knowledge Graph Linker**: Queries database for other records matching extracted entities, and creates matching relationship edges.
10. **Database & Vector Commit**: Updates SQLite status to `COMPLETE`, stores extracted JSON, adds vector embeddings to ChromaDB, and updates graph links.
11. **User Notification**: Frontend polling or WebSockets notifies the user that the document is ready.
