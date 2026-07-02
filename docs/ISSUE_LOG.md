# NeuroVault AI — Project Issue & Debug Log

This file is a running log of all failures, errors, installation bugs, and logic issues encountered during the development of NeuroVault AI, along with their root causes, debugging steps, and resolutions.

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
  In `docker-compose.yml`, the volume `- ./backend/neurovault.db:/app/neurovault.db` mapped a non-existent file on the host. When a file volume source does not exist, Docker automatically initializes it as a directory. SQLite crashed trying to open a directory as a DB file.
- **What I Tried:**
  - Inspected the host filesystem mode of `backend/neurovault.db` and confirmed it was a directory (`Mode: d-----`).
- **Fix:**
  Deleted the folder and updated `docker-compose.yml` to map a directory instead of a file:
  ```yaml
  volumes:
    - ./backend/data:/app/data
  environment:
    - DATABASE_URL=sqlite:////app/data/neurovault.db
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
  ERROR:neurovault.ocr:Failed to initialize EasyOCR: operator torchvision::nms does not exist
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
  WARNING:neurovault.ocr:Local EasyOCR does not support PDF files directly. Returning empty text.
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



