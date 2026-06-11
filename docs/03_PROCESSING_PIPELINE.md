# NeuroVault AI — 15-Step Async Document Processing Pipeline

This document explains the step-by-step lifecycle of a document as it passes through the NeuroVault processing pipeline. Every stage is asynchronous to prevent locking the main thread.

---

## The 15 Stages of Understanding

```
[Upload] ─► 1. Format Detection ─► 2. OpenCV Pre-processing
                                             │
 ┌───────────────────────────────────────────┘
 ▼
 3. OCR / Vision Analysis (Gemini / EasyOCR) ─► 4. Doc Type Classification
                                                          │
 ┌────────────────────────────────────────────────────────┘
 ▼
 5. Field Extraction (JSON) ─► 6. Format Validation (Regex)
                                           │
 ┌─────────────────────────────────────────┘
 ▼
 7. Quality & Confidence ─► 8. Summary Generation ─► 9. Entity Mining (spaCy)
                                                           │
 ┌─────────────────────────────────────────────────────────┘
 ▼
 10. Sentence Embeddings ─► 11. Vector Store Commit (Chroma)
                                           │
 ┌─────────────────────────────────────────┘
 ▼
 12. Knowledge Graph Linker ─► 13. Expiry / Action Items
                                           │
 ┌─────────────────────────────────────────┘
 ▼
 14. Tagging & Vault Routing ─► 15. Push Notification
```

---

### Step 1: File Upload & Format Detection
- **Trigger:** The user submits a file through the `/api/documents/upload` API.
- **Action:** The system parses the MIME type (e.g. `image/png`, `application/pdf`, `audio/mp3`, `text/plain`). It generates a unique UUID, instantiates a row in the SQLite database with state `PROCESSING`, and saves the file to the local `uploads/` directory.

### Step 2: Image Pre-processing (OpenCV)
- **Applicable to:** Images and PDF pages.
- **Action:** The backend uses OpenCV to enhance image quality:
  - Denoising: Remove high-frequency camera noise.
  - Deskewing: Check orientation and rotate the image if it was shot tilted.
  - Thresholding/Contrast enhancement: Improve legibility of faded text.

### Step 3: OCR / Vision AI Analysis
- **Primary:** Google Gemini Vision API. It receives the image bytes and reads the text directly, maintaining visual layout understanding.
- **Fallback:** If Gemini fails or is unconfigured, the system runs local **EasyOCR** to parse the raw text lines offline.

### Step 4: Document Type Classification
- **Action:** The text contents are processed to identify the document type from our 50+ taxonomy classes (e.g., detecting terms like "Permanent Account Number Card" or "Aadhaar" or "marksheet"). It outputs the classification alongside a confidence level (High / Medium / Low).

### Step 5: Structured Field Extraction
- **Action:** Map the text to the target category schema (defined in `02_DOCUMENT_TAXONOMY.md`). If Gemini is used, it utilizes structured schema outputs. If using fallback, it uses targeted regular expressions (Regex) to extract the key values.

### Step 6: Data Validation
- **Action:** Extracted fields are parsed against standard format rules:
  - Aadhaar: Matches exactly 12 digits.
  - PAN: Matches `[A-Z]{5}[0-9]{4}[A-Z]{1}` format.
  - Dates: Parses into unified `YYYY-MM-DD` ISO format.

### Step 7: Quality & Confidence Score
- **Action:** Compute a metric representation of document readability. If vital fields (e.g. the PAN number or the Aadhaar number) are missing or misformatted, the confidence score drops and the record is flagged for review.

### Step 8: Summary Card Generation
- **Action:** The AI (or a template builder) writes a natural language summary explaining what the document is, who it belongs to, and key dates (e.g. "Passport belonging to John Doe, issued in 2021, expiring in 2031").

### Step 9: Named Entity Extraction (spaCy)
- **Action:** Pass the raw text and summary card to spaCy's Named Entity Recognition model to identify instances of people, companies, boards, and dates.

### Step 10: Embedding Generation
- **Action:** Convert the summary card and key metadata strings into a 384-dimensional floating point vector representation using the `all-MiniLM-L6-v2` transformer model.

### Step 11: Vector Store Commit (ChromaDB)
- **Action:** Save the embedding vector into our local ChromaDB vector collection, indexed with the Document UUID and user filters.

### Step 12: Knowledge Graph Update
- **Action:** Run comparisons against previously uploaded documents. If matching names, dates, or card numbers are found, write the relationships (`ISSUED_TO`, `PRECEDES`, `EMPLOYED_AT`) into the `graph_edges` table.

### Step 13: Action Item & Expiry Detection
- **Action:** Scan the structured JSON for fields indicating deadlines, bill due dates, or document expirations. Add these items to the upcoming alerts calendar.

### Step 14: Auto-Tagging & Vault Routing
- **Action:** Assign tags (e.g. `#identity`, `#academic`) and place the file in the virtual folder tree based on its category (e.g., `Identity Documents/Aadhaar`).

### Step 15: Push Notification / Completion
- **Action:** Update the SQLite record status to `COMPLETE`. The frontend, which polls the backend or listens to a websocket, immediately updates the UI to show the processed card.
