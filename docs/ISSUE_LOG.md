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



