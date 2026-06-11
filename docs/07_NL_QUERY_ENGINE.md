# NeuroVault AI — Natural Language Query Engine

This document explains the query patterns, reasoning chains, and local fallback rules used by the AI Memory Assistant to answer user questions.

---

## 1. Handled Query Patterns & Reasoning Chains

The assistant parses user queries and maps them to documents using semantic vector matching. Below are the core reasoning chains:

| User Query | Targeted Vault Assets | Reasoning & Extraction Steps |
|---|---|---|
| *"What is my PAN number?"* | `PAN Card` | Find PAN Card -> Extract `pan_number` field. Mask digits except last 4. |
| *"When does my driving licence expire?"* | `Driving Licence` | Find DL -> Extract `expiry_date` -> Alert user if upcoming. |
| *"What were my Class 12 marks in Physics?"* | `Class 12 Marksheet` | Find Class 12 marksheet -> Parse `subjects` list -> Filter subject "Physics" -> Extract score. |
| *"Which company gave me my first job and what was my CTC?"* | `Offer Letter` | Query oldest Offer Letters -> Extract `company_name`, `ctc`, `joining_date`. |
| *"Summarize my entire academic history"* | `Academic Records` | Chain Class 10, Class 12, and Degree certificates chronologically -> Generate narrative summary. |
| *"What documents do I need to renew in the next 6 months?"* | All Documents | Scan all `action_items.expiry_date` values -> Filter dates within 180 days -> Generate list. |
| *"What is my blood type?"* | `Medical Reports` / `Prescriptions` | Search medical vault for keywords: "blood group", "blood type", "A+", "O-" -> Extract match. |
| *"Show me everything related to my car"* | `Vehicle Documents` | Search RC, Vehicle Insurance, and PUC -> Cluster by shared vehicle registration number. |

---

## 2. Local Fallback Resolver (Online/Offline Resilience)

To ensure the system works offline or without a Gemini API Key, we implement a rule-based query parser inside `RAGPipeline._answer_with_local_rules`.

### How the Local Resolver Works:
1. **Keyword Analysis:** Uses regular expressions to match intent (e.g. checks if query contains "pan", "aadhaar", "marks", "job", "expire").
2. **Context Filtering:** Filters the top-matching documents returned by ChromaDB vector search.
3. **JSON Extraction:** Extracts targeted keys directly from the SQLite database `extracted_json` text column.
4. **Formatting & Masking:** Applies masking helper functions (e.g. hides middle numbers on Aadhaar/PAN) and prints cited responses.
