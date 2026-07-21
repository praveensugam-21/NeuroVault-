# IRIS AI — Testing & Verification Guide

This document explains how to run automated unit tests and verify the code structure.

---

## 1. Backend Unit Tests (`pytest`)

We use `pytest` to test backend models, taxonomy classifications, Google OAuth logins, settings management, and regex parsing rules.

### Test Environment & Database Fixtures:
Backend tests use a shared SQLite database fixture defined in `backend/tests/conftest.py`. This ensures tests run in-memory or in isolated test databases, completely separated from development or production databases.

### Setup Test Commands:
First, activate the virtual environment and ensure all dependencies are installed:
```bash
cd backend
pip install -r requirements.txt
```

To run the full test suite:
```bash
python -m pytest tests/ -v
```

### Writing a New Test Case:
Add test files under `backend/tests/` using the prefix `test_`. For example, checking PAN format validation:
```python
def test_pan_regex_matching():
    from app.services.document_processor import DocumentProcessor
    # Valid PAN
    res = DocumentProcessor._process_with_rules("pan_card.png", "Permanent Account Number Card ABCDE1234F")
    assert res["document_type"] == "PAN Card"
    assert res["extracted_fields"]["pan_number"] == "ABCDE1234F"
```

---

## 2. Frontend Compilation Validation

Before shipping, check that the TypeScript code builds correctly without compilation errors:
```bash
cd frontend
npm run build
```
This runs the TypeScript compiler (`tsc`) and builds the production bundles using Vite. Ensure all component imports and prop bindings pass typescript validation checks.
