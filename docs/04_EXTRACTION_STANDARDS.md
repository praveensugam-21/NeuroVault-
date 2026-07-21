# IRIS AI — Extraction Quality & Validation Standards

This document explains how IRIS AI validates data extraction, determines confidence scores, and flags anomalies.

---

## 1. Validation Rules & Regex Reference

To maintain data integrity, every extracted field is checked against standard formats using Pydantic or custom regular expressions.

### Identity & Resume Validations
- **Aadhaar Number:**
  - Pattern: `^[0-9]{12}$` (Exactly 12 digits after stripping whitespace/spaces).
  - Validation: Luhn algorithm check (optional verification check) or simple digit length checks.
- **PAN Number:**
  - Pattern: `^[A-Z]{5}[0-9]{4}[A-Z]{1}$`
  - Break-down:
    - First 3 chars: `AAA` to `ZZZ` (letters).
    - 4th char: Cardholder type (e.g. `P` = Individual, `C` = Company, `F` = Firm).
    - 5th char: First letter of cardholder's surname.
    - Chars 6–9: Sequential numbers.
    - 10th char: Alphabetic check digit.
- **Passport Number:**
  - Pattern: `^[A-Z]{1}[0-9]{7}$` (Standard Indian passport format).
- **Voter ID (EPIC Number):**
  - Pattern: `^[A-Z]{3}[0-9]{7}$` or state-specific codes like `^MH/[0-9]{2}/[0-9]{3}/[0-9]{6}$`.
- **Resume Skills & Competencies:**
  - Parses skills list using customized keyword extractors and resume models to populate the tags database structure.
  - Matches programming languages, software, cloud services, and professional competencies.

### Tax & Business Validations
- **GSTIN Number:**
  - Pattern: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$` (15 characters).
  - Break-down: Begins with 2-digit state code, followed by 10-char PAN, then entity index, letter 'Z', and check digit.

### Universal Date Parsing
- All dates are run through standard date parsers and saved as standard ISO formats (`YYYY-MM-DD`). 
- **Rule Check:** If date of birth is future-dated, or expiry date precedes the issue date, it triggers a validation error.

---

## 2. Confidence Scoring Algorithm

The confidence score (between 0.0 and 1.0) indicates the reliability of the extracted content. It is calculated dynamically based on:

$$Score = (0.4 \times OCR\_Conf) + (0.4 \times Field\_Fill\_Rate) + (0.2 \times Form\_Validation\_Rate)$$

- **OCR Confidence ($OCR\_Conf$):** Average confidence returned by the OCR layer (Gemini or EasyOCR character detection score).
- **Field Fill Rate ($Field\_Fill\_Rate$):** Count of successfully filled taxonomy-required fields divided by the total number of schema fields for that document type.
- **Format Validation Rate ($Form\_Validation\_Rate$):** Percentage of fields that matched their regex validation patterns.

### Classification Categories:
- **High Confidence (>= 0.85):** Direct auto-save; no user review required.
- **Medium Confidence (0.60 - 0.84):** Saved, but shown in UI with a "Review Fields" warning.
- **Low Confidence (< 0.60):** Marked as `Unclassified` or triggers a warning banner requiring human validation.

---

## 3. Anomaly Flagging System

Anomalies do not imply fraud, but identify items that might be incorrect.

- **Tampering/Editing Indicators:** Checking if metadata details of a PDF mention editing software (e.g. Photoshop) or if visual blocks have mismatching compression indices (for future premium modules).
- **Blur & Readability Warnings:**
  - If characters are low contrast or have very low OCR confidence scores.
  - If mandatory fields for identity cards (like the card number itself) cannot be parsed.
- **Visual Crop Flags:** If page edges are cropped, causing a text string to end abruptly (e.g. cut-off address lines).
