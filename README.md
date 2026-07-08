# NeuroVault

NeuroVault is a secure, local-first document processing, categorization, and querying application. It parses uploads (PDFs, images, text), extracts structured fields, builds a semantic knowledge graph of links, tracks document health/completeness, and runs natural language queries over your files.

---

## Key Features

1. **Document Processing Pipeline**
   - Automatically classifies files into key business categories (Identity, Academic, Financial, Professional, etc.).
   - Runs layout OCR (using EasyOCR for scanned pages) and text-layer parsing (using `pypdf` for digital documents).
   - Generates concise summary cards and extracts structured metadata (e.g. Aadhaar, PAN numbers, birth dates, names).

2. **Semantic Knowledge Graph**
   - Automatically extracts entity relationships (names, organizations, dates) using spaCy NER.
   - Links documents based on mutual connections (e.g., studies at, issued by, follows).
   - Renders a clean, structured clustered layout using React Flow in the browser.

3. **Secure Local-First Architecture**
   - Field-level encryption for sensitive identifiers.
   - Front-end data masking (e.g., masking Aadhaar and PAN numbers by default).
   - Individual document locks secured by a bcrypt-hashed PIN.
   - Full audit trail logging actions like uploads, queries, lock/unlock, and deletes.

4. **NL Query Engine & Assistant**
   - Combines ChromaDB vector search with Sentence Transformers (`all-MiniLM-L6-v2`) and Gemini.
   - Answers questions regarding vault content (e.g., extracting marks, license expiry, or bio-data fields).
   - Features a clean, three-panel workspace layout with cited document slide-out drawers.

---

## Performance Optimizations (Ingestion & Boot)

To ensure low latency and a smooth user experience, the system implements several production-level optimizations:
- **Pre-downloaded ML Models**: Neural network weights for `SentenceTransformer`, `EasyOCR`, and `spaCy` are baked directly into the Docker image layers on build. No model downloads occur during runtime, keeping document processing offline and fast.
- **Persistent Model Cache**: Caches are mounted to the host filesystem via Docker volumes (`./backend/cache`). If the container is rebuilt or reset, the weights load instantly from the host disk.
- **Client-Side Polling**: The React client polls the FastAPI status endpoint every 800ms during upload, fast-forwarding the pipeline tracker as soon as processing completes on the server.

---

## Quick Start

### Run with Docker Compose (Recommended)

1. Launch Docker Desktop.
2. In the project root directory, run:
   ```bash
   docker compose up --build -d
   ```
3. Access the applications:
   - **React UI**: [http://localhost](http://localhost) (Port 80)
   - **FastAPI Documentation**: [http://localhost:8001/docs](http://localhost:8001/docs)

---

### Local Development Setup

If you prefer to run the backend and frontend services directly on your host machine:

#### 1. Backend Service
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the Uvicorn server:
   ```bash
   python -m uvicorn app.main:app --port 8001
   ```
   The backend API will run on `http://localhost:8001`.

#### 2. Frontend Client
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend will run on `http://localhost:5173`.

---

## Test Credentials

For testing and verification:
- **Login Account**: `test@neurovault.ai` / `Password123`
- **Secondary PIN**: `1234` (for locking and unlocking documents)
