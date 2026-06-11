# NeuroVault AI — Testing & Verification Guide

This document explains how to run automated unit tests and verify the code structure.

---

## 1. Backend Unit Tests (`pytest`)

We use `pytest` to test backend models, taxonomy classifications, and regex parsing rules.

### Setup Test Commands:
First, activate the virtual environment and ensure test packages are installed:
```bash
cd backend
pip install pytest pytest-mock
```

To run the full test suite:
```bash
pytest tests/ -v
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
