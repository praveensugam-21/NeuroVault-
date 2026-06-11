# NeuroVault AI — REST API Endpoint Documentation

This document lists the REST API endpoints provided by the FastAPI backend.

---

## 1. Authentication Endpoints

### `POST /api/auth/register`
- **Description:** Creates a new user account.
- **Request Body:**
  ```json
  {
    "email": "user@email.com",
    "password": "strongpassword"
  }
  ```
- **Response:** `201 Created`

### `POST /api/auth/login`
- **Description:** OAuth2 standard password flow. Returns JWT access token.
- **Request (Form Data):**
  - `username`: Email address.
  - `password`: Password.
- **Response:**
  ```json
  {
    "access_token": "jwt_token_string",
    "token_type": "bearer"
  }
  ```

---

## 2. Document Endpoints

### `POST /api/documents/upload`
- **Description:** Uploads a document file and starts the 15-step processing pipeline.
- **Request (Multipart Form):**
  - `file`: Binary file upload.
  - `name`: Custom display name.
- **Response:** `202 Accepted`

### `GET /api/documents/`
- **Description:** Lists all documents. Supports category filtering.
- **Query Parameter:** `category` (optional).
- **Response:** Array of Document summaries.

### `GET /api/documents/{id}`
- **Description:** Retrieves document details.
- **Query Parameter:** `pin` (optional, required if document is locked).

### `DELETE /api/documents/{id}`
- **Description:** Hard-deletes document file from disk, SQLite records, and ChromaDB.

---

## 3. Query & Graph Endpoints

### `POST /api/chat/`
- **Description:** Interfaces with the RAG assistant.
- **Request Body:**
  ```json
  {
    "question": "What is my PAN number?",
    "history": []
  }
  ```

### `GET /api/graph/`
- **Description:** Returns the nodes and edges for React Flow visualization.
- **Response:**
  ```json
  {
    "nodes": [{"id": "doc_id", "label": "My PAN", "type": "document"}],
    "edges": [{"id": "edge-1", "source": "doc_id", "target": "Praveen", "label": "ISSUED_TO"}]
  }
  ```
