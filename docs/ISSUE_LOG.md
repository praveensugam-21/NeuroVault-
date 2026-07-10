# IRIS AI — Project Issue & Debug Log

This file is a running log of all failures, errors, installation bugs, and logic issues encountered during the development of IRIS AI, along with their root causes, debugging steps, and resolutions.

---

## Template for Entries

```markdown
## Issue #[ID] — [Short descriptive title]
- **Date:** YYYY-MM-DD
- **Phase:** Phase X
- **File:** [path/to/file](file:///e:/Desktop/AI%20CHATBOT/...)
- **Error Message:**
  ```text
  [Raw error message or traceback]
  ```
- **Root Cause:**
  (Explanation of why the error happened)
- **What I Tried:**
  - Debug attempt 1...
  - Debug attempt 2...
- **Fix:**
  (How it was resolved, code snippet, or command)
- **Learning:**
  (Engineering takeaway for future reference)
```

---

## Running Log

## Issue #001 — 'pytest' is not recognized as a cmdlet or executable
- **Date:** 2026-06-11
- **Phase:** Phase 8 (Verification)
- **File:** Command line shell execution
- **Error Message:**
  ```text
  pytest : The term 'pytest' is not recognized as the name of a cmdlet, function, script file, or operable program.
  ```
- **Root Cause:**
  The `pytest` executable was run directly, but it is not registered in the system's PATH environment variables or python packages are not installed globally on the host computer.
- **What I Tried:**
  - Running `pytest tests/ -v` directly in PowerShell.
- **Fix:**
  Run `pytest` via the active Python module runner:
  ```powershell
  python -m pytest tests/ -v
  ```
  Or verify that packages are installed first with:
  ```powershell
  pip install -r requirements.txt
  ```
- **Learning:**
  Invoking python modules via `python -m <module_name>` is a safer practice than calling global wrapper scripts. It guarantees execution matches the specific python environment version active in the terminal.

## Issue #002 — IndentationError in embedding_service.py during test collection
- **Date:** 2026-06-11
- **Phase:** Phase 8 (Verification)
- **File:** [embedding_service.py](file:///e:/Desktop/AI%20CHATBOT/backend/app/services/embedding_service.py)
- **Error Message:**
  ```text
  File "E:\Desktop\AI CHATBOT\backend\app\services\embedding_service.py", line 142
    Weston
          ^
  IndentationError: unindent does not match any outer indentation level
  ```
- **Root Cause:**
  A stray text string "Weston" was accidentally printed at the end of the file during generation.
- **What I Tried:**
  - Inspected the end of the file using view_file.
- **Fix:**
  Removed the stray text from the file footer and verified indentation matches returning a clean empty list.
- **Learning:**
  Always review file footers and headers after generating large files to ensure copy-paste drift or template trails do not leak syntax errors.

## Issue #003 — Pillow 10.3.0 Build Failure on Python 3.13
- **Date:** 2026-06-11
- **Phase:** Phase 8 (Verification)
- **File:** [requirements.txt](file:///e:/Desktop/AI%20CHATBOT/backend/requirements.txt)
- **Error Message:**
  ```text
  KeyError: '__version__'
  error: subprocess-exited-with-error
  Getting requirements to build wheel did not run successfully.
  ```
- **Root Cause:**
  Older version pins (like `pillow==10.3.0`) do not offer pre-compiled binary wheel packages for Python 3.13 on Windows. This forces `pip` to compile them from source, which fails because the environment lacks MSVC/C++ build tools.
- **What I Tried:**
  - Removing spacy/easyocr (which also failed compiling) and running installation with pinned Pillow.
- **Fix:**
  Unpinned the package versions in `requirements.txt`. This allows `pip` to automatically retrieve newer, pre-compiled wheels (e.g., Pillow 10.4.0+ or 11.0.0+) built for Python 3.13.
- **Learning:**
  When deploying systems on brand-new Python runtimes, avoid overly restrictive pinning. Let package managers resolve dependency resolutions dynamically to match target runtimes.

## Issue #004 — WSL Read-Only Mount due to Full Host C: Drive
- **Date:** 2026-06-11
- **Phase:** Docker Setup & Execution
- **File:** WSL2 / Docker Desktop Daemon
- **Error Message:**
  ```text
  ERROR: rpc error: code = Internal desc = write /var/lib/docker/buildkit/containerd-overlayfs/metadata_v2.db: input/output error
  ERROR: Could not install packages due to an OSError: [Errno 5] Input/output error
  ```
- **Root Cause:**
  The host Windows machine's C: drive was completely full (0 bytes free), causing the WSL2 virtual disk (`ext4.vhdx`) to fail any write operation. WSL2 automatically remounted the filesystem as read-only to prevent corruption.
- **What I Tried:**
  - Ran `docker builder prune -f` to clear space within the WSL environment (reclaimed 3.4 GB).
  - Checked disk usage via `wsl df -h` and saw C: drive was 100% full.
- **Fix:**
  Shut down the WSL2 environment completely:
  ```powershell
  wsl --shutdown
  ```
  And advised the user to free up disk space on C: (or move WSL2 to E: / F: drive).
- **Learning:**
  WSL2 Input/output errors are almost always caused by Windows host disk exhaustions. Always verify host drive capacities when VM daemons begin failing with write permissions.

## Issue #005 — Database File Mapped as Directory by Docker
- **Date:** 2026-06-11
- **Phase:** Docker Run
- **File:** [docker-compose.yml](file:///e:/Desktop/AI%20CHATBOT/docker-compose.yml)
- **Error Message:**
  ```text
  sqlite3.OperationalError: unable to open database file
  ```
- **Root Cause:**
  In `docker-compose.yml`, the volume `- ./backend/iris.db:/app/iris.db` mapped a non-existent file on the host. When a file volume source does not exist, Docker automatically initializes it as a directory. SQLite crashed trying to open a directory as a DB file.
- **What I Tried:**
  - Inspected the host filesystem mode of `backend/iris.db` and confirmed it was a directory (`Mode: d-----`).
- **Fix:**
  Deleted the folder and updated `docker-compose.yml` to map a directory instead of a file:
  ```yaml
  volumes:
    - ./backend/data:/app/data
  environment:
    - DATABASE_URL=sqlite:////app/data/iris.db
  ```
- **Learning:**
  Never map individual SQLite files directly in Docker volumes. Always map the parent directory (e.g. `data/` folder) to prevent Docker from creating dummy directories.

## Issue #006 — Missing email-validator Dependency
- **Date:** 2026-06-11
- **Phase:** Docker Run
- **File:** [requirements.txt](file:///e:/Desktop/AI%20CHATBOT/backend/requirements.txt)
- **Error Message:**
- **Root Cause:**
  The User schemas in `app/schemas/user.py` use Pydantic's `EmailStr` class, which requires `email-validator` to be installed. The package was not listed in `requirements.txt`.
- **What I Tried:**
  - Verified package list in `backend/requirements.txt`.
- **Fix:**
  Appended `email-validator` to `requirements.txt` and rebuilt the backend container.
- **Learning:**
  Pydantic core features like `EmailStr` require extra validation packages. Ensure they are listed in dependencies.

## Issue #007 — PyTorch and torchvision Version Mismatch
- **Date:** 2026-07-02
- **Phase:** Docker Runtime Ingestion
- **File:** [Dockerfile](file:///e:/Desktop/AI%20CHATBOT/backend/Dockerfile)
- **Error Message:**
  ```text
  ERROR:iris.ocr:Failed to initialize EasyOCR: operator torchvision::nms does not exist
  ```
- **Root Cause:**
  `torch` (CPU) and `easyocr` (which auto-installed regular `torchvision`) were installed in separate steps, resulting in incompatible torchvision wheels. This broke the torchvision C++ extensions loader, preventing EasyOCR from starting.
- **What I Tried:**
  - Verified PyTorch torchvision compilation flags.
- **Fix:**
  Modified the Dockerfile to install both `torch` and `torchvision` simultaneously from the PyTorch CPU index wheel repository:
  `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`
- **Learning:**
  Always install companion packages (like torchvision, torchaudio) together with PyTorch from the same repository index to maintain internal ABI compatibility.

## Issue #008 — Scanned PDFs Ingestion Failure
- **Date:** 2026-07-02
- **Phase:** Document Ingestion
- **File:** [ocr_service.py](file:///e:/Desktop/AI%20CHATBOT/backend/app/services/ocr_service.py)
- **Error Message:**
  ```text
  WARNING:iris.ocr:Local EasyOCR does not support PDF files directly. Returning empty text.
  ```
- **Root Cause:**
  Digital text parsers like `pypdf` return empty text for scanned PDFs, and local `EasyOCR` only handles image file formats. Scanned PDFs had empty OCR text outputs, resulting in classification failures.
- **What I Tried:**
  - Attempted to pass raw PDFs to EasyOCR reader, which crashed.
- **Fix:**
  Updated `OCRService` to extract page images from scanned PDFs and run `EasyOCR` on those image buffers, returning parsed text.
- **Learning:**
  Scanned PDFs are essentially collections of images. Extract the images first before passing them to local image OCR engines.

## Issue #009 — Artificial Client-Side Ingestion Delays
- **Date:** 2026-07-02
- **Phase:** Frontend UX
- **File:** [Upload.tsx](file:///e:/Desktop/AI%20CHATBOT/frontend/src/pages/Upload.tsx)
- **Root Cause:**
  The React client had a simulated delay loop that waited 350ms per step regardless of how fast the backend completed processing.
- **What I Tried:**
  - Reduced simulation timers, which still caused artificial latency.
- **Fix:**
  Implemented polling checks targeting `/api/documents/{id}` every 800ms, immediately fast-forwarding the progress stepper to completion once the database status reaches `COMPLETE`.
- **Learning:**
  Avoid artificial hardcoded timers in processing workflows; poll backend status endpoints and update UI states dynamically.


## Issue #010 — False PAN Card Classification on Unrelated Documents
- **Date:** 2026-07-08
- **Phase:** Document Processing / Classification
- **File:** [document_processor.py](file:///e:/Desktop/AI%20CHATBOT/backend/app/services/document_processor.py)
- **Error Message:**
  ```text
  Document type shows "PAN Card" for an uploaded file that is NOT a PAN card.
  ```
- **Root Cause:**
  The PAN card classifier in `_process_with_rules()` used an overly broad regex and keyword condition:
  ```python
  elif "pan" in combined or bool(re.search(r"[A-Z]{5}\d{4}[A-Z]", ocr_text.upper())):
  ```
  Two distinct problems:
  1. `"pan" in combined` matched words like "panel", "panache", "panda", "pan" in any unrelated sentence.
  2. The regex `[A-Z]{5}\d{4}[A-Z]` had **no word boundaries** (`\b`). It matched any 5-letter uppercase prefix followed by 4 digits and a letter, which commonly appears in product SKUs, invoice reference numbers, order codes, and batch IDs.

- **What I Tried:**
  - Uploaded a test file unrelated to any official document → system incorrectly classified it as "PAN Card."

- **Fix (Applied in `document_processor.py`):**
  1. **Pre-computed strict signals** before the `if/elif` chain:
     ```python
     _pan_keywords = ["pan card", "permanent account number", "income tax department", "आयकर विभाग"]
     _pan_keyword_found = any(kw in combined for kw in _pan_keywords)
     _pan_number_found = bool(re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", ocr_text.upper()))
     _is_pan = _pan_keyword_found or (_pan_number_found and "pan" in combined)
     ```
  2. **PAN classifier now uses `_is_pan`** — requires an explicit PAN keyword phrase (not just the word "pan") OR a strict word-boundary PAN number AND the word "pan" together.
  3. **Strict word boundaries added** to the extraction regex: `r"\b([A-Z]{5}\d{4}[A-Z])\b"` instead of `r"([A-Z]{5}\d{4}[A-Z]{1})"`.
  4. **Ollama confidence gate added** in `process_document()`: if Ollama returns a confidence score below 0.45, it falls back to the rule-based parser instead of returning a potentially wrong AI result.

- **Learning:**
  - Never match a document type using a single short keyword like `"pan"` in a combined text + filename string without requiring co-occurrence with another strong signal.
  - Always add `\b` word boundaries to alphanumeric document ID regex patterns. Without them, they false-match on any text containing similar character sequences.
  - A defense-in-depth approach using **multiple required signals** (keyword + pattern + confidence threshold) is far more robust than single-condition classifiers.

---

## Issue #010b — Follow-Up: Ollama LLM Still Hallucinating PAN Card for Unrelated Report
- **Date:** 2026-07-08
- **Phase:** Document Processing / Classification
- **File:** [document_processor.py](file:///e:/Desktop/AI%20CHATBOT/backend/app/services/document_processor.py)
- **Error Message:**
  ```text
  Document type: "PAN Card" shown for a plain text report with no PAN card content.
  (Persisted even after rule-based fix was applied in Issue #010.)
  ```
- **Root Cause:**
  The Ollama LLM runs **before** the rule-based parser. Even after fixing the rule-based classifier, Ollama itself was the one returning "PAN Card" — because its original prompt only listed document types without instructing it when **NOT** to use them. LLMs default to "best guess" when uncertain, picking the type that partially matches any word in the document.

- **Fix (Three-layer defense added):**

  **Layer 1 — Improved Ollama Prompt**: Added an explicit `=== CRITICAL RULE ===` section at the top of the prompt that instructs the model:
  > "If the document does NOT clearly match one of the known types, you MUST set document_type = Unclassified. DO NOT guess."
  Also rewrote each document_type option with explicit evidence requirements (e.g., PAN Card — only if it explicitly says Permanent Account Number or Income Tax Department).

  **Layer 2 — Post-Validation (`_validate_ollama_result`)**: New method added that runs immediately after Ollama returns a result. For each major document type, it checks for the presence of **required evidence keywords/patterns** in the text. If Ollama classified a document but no supporting evidence is found, the classification is overridden to `Unclassified` regardless of what the LLM decided:
  ```python
  evidence_rules = {
      "PAN Card": lambda: any(kw in combined for kw in ["pan card", "permanent account number", ...])
                          or (_pan_number_found and "pan" in combined),
      ...
  }
  if not has_evidence:
      result["document_type"] = "Unclassified"
  ```

  **Layer 3 — Confidence Gate** (from Issue #010): Ollama results with `confidence_score < 0.45` still fall through to the rule-based parser.

- **Learning:**
  When using LLMs for classification on structured domain problems, always add a post-validation layer that uses deterministic rules to sanity-check the LLM output. LLMs are probabilistic — they will guess rather than abstain. The rule-based validator acts as a hard constraint filter over the LLM's soft classification.


