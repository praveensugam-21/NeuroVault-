# IRIS — Text Extraction & Parsing Engines

This document explains the full OCR pipeline, text correction engines, and field extraction architecture used inside the IRIS document intelligence system.

> **Last Updated:** 2026-07-21 — Updated for PyMuPDF (`fitz`), direct HTTP/1.1 REST client for Gemini, live Settings API probe, and PostOCRCorrector fixes.

---

## 1. Local OCR Engine (EasyOCR & Direct PDF Extraction)

### What It Is

IRIS uses a two-path text extraction strategy depending on the document type:

| Document Type | Extraction Method |
|---|---|
| Digital PDF (searchable) | `PyMuPDF (fitz)` — extracts the embedded text layer 5–10x faster |
| Scanned PDF | Rendered to page images via PyMuPDF, then processed by EasyOCR |
| Image file (JPG, PNG, TIFF) | Passed directly to EasyOCR |

**EasyOCR** is a neural OCR engine built on PyTorch that uses:
- **CRAFT** (Character Region Awareness for Text Detection) for text detection
- **ResNet + LSTM** for text recognition
- CPU-only inference (no GPU required, but slower)

All OCR runs entirely locally on your machine. No image data is ever sent to a cloud OCR service.

### EasyOCR Limitations on CPU

EasyOCR is accurate but not perfect, particularly on low-resolution scans, unusual fonts, or smudged documents. On CPU inference, several systematic character confusion patterns have been observed:

| Misread Pattern | Example | Actual |
|---|---|---|
| `ee` → `d` (character merge) | `Kumadr` | `Kumaar` or `Kumar` |
| `hin` → `lim` (shape confusion) | `Tamilnadu` → `Taminadu` | `Tamil Nadu` |
| `T` → `J` (stroke ambiguity) | `Jamil Nadu` | `Tamil Nadu` |
| `0` → `O` (zero/letter) | `A0BCD1234E` | `A0BCD1234E` (PAN) |
| `l` → `1` (thin stroke) | `1ast name` | `last name` |
| State name merging | `TamilNadu` | `Tamil Nadu` |

These systematic errors are the primary reason IRIS runs a multi-pass correction engine after raw OCR.

---

## 2. PostOCRCorrector — Three-Pass Correction Engine

The `PostOCRCorrector` service (`backend/app/services/post_ocr_corrector.py`) runs immediately after raw EasyOCR output is obtained. It corrects common OCR errors using three sequential passes:

### Pass 1 — Pincode → State Resolution

Aadhaar cards and other Indian documents include a 6-digit pincode. The corrector uses a built-in pincode-to-state lookup dictionary to verify and correct the state name field:

```python
# Example:
extracted_fields["pincode"] = "600001"
# → Lookup: 600001 → Tamil Nadu
extracted_fields["state"] = "Tamil Nadu"   # Overwrites any garbled OCR state
```

This is highly reliable because pincodes are machine-readable numbers (EasyOCR rarely confuses digits) and the state name can be deterministically derived.

### Pass 2 — Known OCR Corrections Dictionary

A hard-coded dictionary of known character confusion corrections specific to Indian document fonts:

```python
KNOWN_CORRECTIONS = {
    "Jamil Nadu":   "Tamil Nadu",
    "Taminadu":     "Tamil Nadu",
    "TamilNadu":    "Tamil Nadu",
    "Kumadr":       "Kumar",
    "Ratlimum":     "Rathinam",  # Common name confusion
    # ... 50+ entries
}
```

Each field value is checked against this dictionary and corrected if matched.

### Pass 3 — Fuzzy String Matching

For fields that Pass 2 doesn't correct, a fuzzy match is performed against known Indian state names, city names, and common name fragments using `difflib.get_close_matches()`. A similarity threshold of 0.8 is applied to avoid over-correction.

### Key Casing Bug (Fixed 2026-07-17)

A critical bug was found and fixed in the PostOCRCorrector:

**Bug:** The `extracted_json` stored by the OCR extractor used `"State"` (capital S), but the corrector's lookup logic used `"state"` (lowercase):

```python
# BUG — key never matched:
if "state" in extracted_fields:          # ← lowercase
    pincode_state = lookup(pincode)
    extracted_fields["state"] = pincode_state   # ← never executed

# ACTUAL key in extracted_json:
{"State": "Jamil Nadu", "Pincode": "600001"}   # ← capital S
```

**Fix:** All keys in `extracted_fields` are now normalised to lowercase before any processing, then restored to the original casing before saving:

```python
# Normalize all keys to lowercase for processing
normalised = {k.lower(): v for k, v in extracted_fields.items()}

# ... all correction logic uses lowercase keys ...

# Re-apply corrected values back to original keys
for original_key in extracted_fields:
    if original_key.lower() in normalised:
        extracted_fields[original_key] = normalised[original_key.lower()]
```

---

## 3. OCRExtractor — Expert Prompt Pipeline

The `OCRExtractor` service (`backend/app/services/ocr_extractor.py`) sits above the PostOCRCorrector and is responsible for:

1. Determining the document type (Aadhaar, PAN, Passport, Resume, etc.)
2. Building a document-type-specific expert prompt
3. Routing the prompt through the LLM Router (Gemini → Ollama → Rules)
4. Parsing the JSON response and merging with PostOCRCorrector output

### Expert Prompt Structure

Each document type has a dedicated extraction prompt template:

```
You are an expert document parser. You are given the OCR text of an Aadhaar card.

Extract the following fields and return ONLY valid JSON:
- "Name": The full name of the cardholder
- "DOB": Date of birth in DD/MM/YYYY format
- "Gender": Male / Female / Transgender
- "Aadhaar": The 12-digit Aadhaar number (with or without spaces)
- "Address": Full address
- "Pincode": 6-digit postal code
- "State": Indian state name

OCR Text:
---
{masked_ocr_text}
---

Return only the JSON object. No explanation.
```

The `{masked_ocr_text}` placeholder is filled with the **PII-masked** version of the raw OCR text (Aadhaar number replaced with `[AADHAAR_0]` etc.) before sending to Gemini.

### LLM Response Validation

After the LLM returns a JSON response, the extractor validates:
- All expected fields are present
- Aadhaar number passes the Verhoeff checksum (if extractable)
- PAN number matches the `[A-Z]{5}[0-9]{4}[A-Z]` pattern
- Date fields parse as valid dates

---

## 4. Gemini 2.5 Flash as the LLM Correction Layer

Gemini 2.5 Flash is the primary LLM used for OCR correction and field extraction. It provides significantly better name correction than rule-based approaches because it can use contextual reasoning.

### Why Gemini 2.5 Flash

| Capability | Rule-Based | Gemini 2.5 Flash |
|---|---|---|
| Correct garbled state names | ✅ (dictionary) | ✅ |
| Correct garbled person names | ❌ | ✅ (contextual) |
| Handle novel character confusions | ❌ | ✅ |
| Structured JSON extraction | ✅ (regex) | ✅ (more reliable) |
| Privacy (PII stays local) | ✅ | ✅ (via PII masking) |
| Speed | ✅ Fast | ✅ Fast (< 2s) |
| Requires internet | ✅ No | ❌ Yes |

### Gemini Model Configuration

```env
GEMINI_MODEL=gemini-2.5-flash
```

> [!IMPORTANT]
> Use `gemini-2.5-flash`, not `gemini-1.5-flash`. The `1.5` model is deprecated and does not work with new `AQ.` prefix API keys from Google AI Studio.

### Probe Token Budget

`gemini-2.5-flash` uses **thinking tokens** internally even for simple requests. The validation probe call uses `max_output_tokens=100` (not 10) to ensure the model has enough token budget to return a non-empty response:

```python
# Correct probe configuration:
config=types.GenerateContentConfig(max_output_tokens=100, temperature=0.0)
```

---

## 5. What Happens When No LLM Is Available

When a document is uploaded and neither Gemini nor Ollama is available:

1. Raw EasyOCR text is captured.
2. `PostOCRCorrector` runs its three passes (rule-based only).
3. The rule-based extractor (`_process_with_rules()`) applies regex patterns to extract fields.
4. **The extracted data may contain garbled values** (e.g., `"Name": "Pravden Ratlimum"` instead of the real name) because LLM contextual correction did not run.
5. The document is saved with `status = COMPLETE`, but the metadata quality is limited.

### How to Fix: The /reextract Endpoint

Once a valid Gemini key (or Ollama) is configured, you can re-run the full correction pipeline on any previously processed document without re-uploading it:

```bash
POST /api/documents/{document_id}/reextract
Authorization: Bearer <your_jwt_token>
```

**What reextract does:**
1. Reloads the original raw OCR text from the database
2. Re-runs `PostOCRCorrector` with the latest correction dictionaries
3. Re-runs `OCRExtractor` with the currently active LLM (Gemini → Ollama → Rules)
4. Overwrites `extracted_json` with the improved result
5. Regenerates entity links and updates ChromaDB embeddings
6. Sets `status = COMPLETE`

**When to use reextract:**
- After setting up a Gemini API key for the first time
- After documents were uploaded during a Gemini outage
- After updating correction dictionaries for new OCR error patterns

---

## 6. Named Entity Recognition (spaCy)

After field extraction, the spaCy `en_core_web_sm` model processes the document summary to extract:

| Entity Type | Examples |
|---|---|
| `PERSON` | "Praveen Kumar", "Ravi Shankar" |
| `ORG` | "Income Tax Department", "CBSE" |
| `DATE` | "12/04/2021", "March 2019" |
| `GPE` | "New Delhi", "Tamil Nadu" |

These extracted entities form the basis of the **Knowledge Graph** — if two documents mention the same person name, spaCy tags both and the graph engine draws a relation edge between them.

---

## 7. Vector Embeddings (Sentence Transformers)

The final step in the pipeline converts the processed document text into a 384-dimensional embedding vector using `all-MiniLM-L6-v2`:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding = model.encode("Aadhaar card of Praveen Kumar, Tamil Nadu")
# → 384-dimensional float32 vector
```

This vector is stored in ChromaDB with user metadata. During search:
- MMR (Maximal Marginal Relevance) retrieval selects diverse top-20 candidates
- CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks to the top-5 most relevant

### Model Cache

Both models are cached in the persistent `model-cache` Docker volume at `/data/model-cache/huggingface/`. The `HF_HOME` environment variable points HuggingFace Transformers to this directory. Models are downloaded once (~1.5 GB) and reused across all container restarts.
