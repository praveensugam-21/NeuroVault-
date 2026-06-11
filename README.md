# NeuroVault AI — Personal Knowledge Intelligence Engine
### FlowZint AI Hackathon 2026 | Production-Grade Semantic Memory Layer

**NeuroVault AI** is not a simple file storage vault. It is a **living, reasoning, semantic memory layer** that understands, categorizes, links, and retrieves personal knowledge across every format a human being can produce or possess. 

Built with **FastAPI**, **React + Vite**, **ChromaDB**, and the **Gemini API**, it automatically parses scanned documents, extracts structured schemas, builds an interactive knowledge graph, alerts you of upcoming document expiries, and answers complex natural language queries about your personal data.

---

## 🌟 Key Capabilities

1. **Universal Document Identity Engine:**
   - Detects and classifies **50+ document types** across 8 distinct categories (Identity, Academic, Professional, Financial, Medical, Property/Legal, Vehicle, and Personal Notes).
   - Generates 3–5 line natural language **Summary Cards** for quick scans.
   - Extracts structured JSON schemas with format validations for key identifiers (PAN, Aadhaar, GSTIN, Dates).
   - Runs a **15-stage asynchronous document processing pipeline** (Pre-processing, OCR, NER, Vector Embedding, Graph Updating, and routing).

2. **Knowledge Graph Engine:**
   - Extracts semantic entities (names, organizations, dates, locations) using spaCy.
   - Links documents automatically based on shared entities using **8 relationship types** (e.g., `ISSUED_TO`, `STUDIED_AT`, `EMPLOYED_AT`, `RELATED_TO`, `PRECEDES`, `FOLLOWS`, `CONTRADICTS`).
   - Renders a interactive, force-directed network graph in the UI using **React Flow**.

3. **AI Memory Assistant (RAG Query Engine):**
   - Implements semantic vector search with ChromaDB and Sentence Transformers.
   - Grounded RAG answering using Gemini (or a beautiful simulation fallback if no API key is set).
   - Answers multi-hop questions like: *"Show me everything related to my car,"* *"What were my Class 12 marks in Physics?"* or *"Create a professional bio from my resume."*

4. **Knowledge Insights Dashboard & Vault:**
   - Clean, dark slate aesthetic designed for maximum readability.
   - Smart Smart folders with automatic category routing.
   - **Timelines:** Visual, chronological tracking of your entire academic and career journey.
   - **Document Health Score:** Computes completeness metrics of essential documents.
   - **Expiry Alert System:** Real-time reminders for renewing passports, driving licences, or insurance.

5. **Security, Privacy & DPDP Compliance:**
   - Secondary **PIN lock (bcrypt-hashed)** to lock individual sensitive files.
   - **At-Rest AES-256 field encryption** for high-risk numbers.
   - **Automatic Masking:** Aadhaar masked as `XXXX-XXXX-1234`, PAN as `ABCDE****F`, and bank accounts as `XXXXXXXXXXXX1234`.
   - Permanent hard-delete removes all files, database rows, vector embeddings, and graph edges.
   - Full user audit log tracking all actions (Upload, View, Lock, Delete).

---

## 📂 Project Structure

```text
e:/Desktop/AI CHATBOT/
├── backend/                       # FastAPI Python Backend
│   ├── app/                       # Application code
│   │   ├── main.py                # Server entry & CORS config
│   │   ├── config.py              # Environment settings & Pydantic config
│   │   ├── database.py            # SQLite connection
│   │   ├── models/                # SQLAlchemy models (User, Document, AuditLog...)
│   │   ├── routers/               # API endpoints (auth, docs, chat, graph...)
│   │   ├── services/              # AI Core (classifier, graph, RAG, masking...)
│   │   └── pipeline/              # 15-stage async worker queue
│   ├── Dockerfile                 # Optimized Python image definition
│   └── requirements.txt           # Pip dependencies
├── frontend/                      # React + TypeScript + Vite Frontend
│   ├── src/
│   │   ├── components/            # UI components (Vault tree, Timelines, RAG Chat...)
│   │   ├── pages/                 # Full pages (Dashboard, Graph, Chat, Vault...)
│   │   ├── services/              # Axios API clients
│   │   └── store/                 # Zustand state management
│   ├── Dockerfile                 # Multi-stage production Nginx image
│   └── package.json               # NPM dependencies
├── docs/                          # Developer Learning & Debug logs
└── docker-compose.yml             # Orchestration settings
```

---

## 🚀 Installation & Running

### Option 1: Run with Docker Compose (Recommended)

To run the application in fully isolated containers using Docker:

1. **Launch Docker Desktop** on your host machine.
2. In the project root directory, run:
   ```bash
   docker compose up --build -d
   ```
3. Once running, access the services:
   - **React UI:** [http://localhost](http://localhost) (Port 80)
   - **FastAPI API Docs:** [http://localhost:8001/docs](http://localhost:8001/docs) *(Mapped to port 8001 to prevent conflicts with other port 8000 services on your machine).*

---

### Option 2: Run Locally (Host-based Fallback)

If your host C: drive is low on space, you can run the application directly on your host machine (using the E: drive workspace which has plenty of space):

#### 1. Start the Backend Server:
1. Open a terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Install python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI server using Uvicorn:
   ```bash
   python -m uvicorn app.main:app --port 8001
   ```
   The backend API will be online at `http://localhost:8001`.

#### 2. Start the Frontend Server:
1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend UI will be online at `http://localhost:5173`. Open this URL in your browser to access the app.

---

## 🔑 Sample Test Credentials

Since this is a local-first application, you can easily register any test account directly in the UI. 

For convenience, we recommend using these **sample credentials** for review and testing:

* **Sign Up / Login Credentials:**
  - **Email:** `test@neurovault.ai`
  - **Password:** `Password123`
* **Document PIN Lock:**
  - **Secondary PIN:** `1234` (Use this PIN to set up locked files or unlock sensitive documents).

---

## 🛠️ Troubleshooting: Disk Space & I/O Errors in Docker

On Windows hosts, if your **C: Drive is 100% full**, you may see Docker builds fail with:
`OSError: [Errno 5] Input/output error` or `failed to write metadata_v2.db`.

This happens because Docker Desktop's default WSL2 virtual hard disk (`ext4.vhdx`) is stored on the C: drive and cannot write or expand.

### How to resolve:
1. **Clean up space on C: Drive:** Free up at least 2-3 GB of space on your C: drive by clearing system temporary files, downloading caches, or empty the Recycle Bin.
2. **Move WSL2/Docker to E: or F: Drive:** (Since E: and F: have tens of gigabytes free):
   - Export Docker data distro: `wsl --export docker-desktop-data E:\docker-desktop-data.tar`
   - Unregister the distro: `wsl --unregister docker-desktop-data`
   - Re-import on E: Drive: `wsl --import docker-desktop-data E:\DockerWSL E:\docker-desktop-data.tar --version 2`
3. **Prune Builder Cache:**
   Run this in PowerShell to clean out build cache and free up virtual disk blocks:
   ```powershell
   docker builder prune -f
   docker system prune -f
   ```
4. **Shutdown WSL2:**
   Forces WSL to release handles and remount in write mode:
   ```powershell
   wsl --shutdown
   ```
   Then relaunch **Docker Desktop**.
