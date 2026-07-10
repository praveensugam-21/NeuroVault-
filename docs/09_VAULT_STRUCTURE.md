# IRIS AI — Smart Vault Directory Structure

This document details the virtual folder tree hierarchy used by IRIS AI to auto-organize your documents without manual labeling.

---

## 1. Virtual Directory Hierarchy

When files are uploaded and classified, they are virtually routed to one of 9 base categories and 30+ folder nodes:

- `Identity Documents/`
  - Aadhaar
  - PAN
  - Passport
  - Driving Licence
  - Voter ID
  - Ration Card
  - Birth Certificate
  - Caste/Community Certificate
  - Income Certificate
  - Domicile Certificate
- `Academic Records/`
  - School (Class 10)
  - School (Class 12)
  - Undergraduate
  - Postgraduate
  - Certificates & Diplomas
  - Course Completions
- `Professional Documents/`
  - Resume / CV
  - Offer Letters
  - Experience Letters
  - Pay Slips
  - Internship Certificates
- `Financial Documents/`
  - Bank Statements
  - Insurance Policies
  - Loan Documents
  - Tax Documents (Form 16, ITR, GST)
- `Medical Records/`
  - Prescriptions
  - Lab Reports
  - Vaccination Certificates
  - Discharge Summaries
- `Property & Legal/`
  - Property Registration
  - Rent Agreements
  - Utility Bills (Electricity, Water)
- `Vehicle Documents/`
  - Registration Certificate (RC)
  - Vehicle Insurance
  - PUC Certificate
- `Personal Notes/`
  - Text Notes
  - Voice Memos (Whisper transcription files)
- `Unclassified (Review Needed)/`
  - Documents falling below the 60% confidence threshold.

---

## 2. Auto-Categorization Logic

The classification routing is managed by `pipeline/processing_queue.py`:
1. The AI engine classifies the document type (e.g. "Aadhaar Card").
2. The pipeline maps the document type to its parent category folder (e.g. "Identity Documents").
3. The database updates the document's `category` and `document_type` columns.
4. The frontend Sidebar fetches these categories dynamically to build folder nodes.
