# IRIS AI — Natural Language Query Engine

This document explains the query patterns, reasoning chains, and local fallback rules used by the AI Memory Assistant to answer user questions.

---

## 1. Handled Query Patterns & Reasoning Chains

The assistant parses user queries and maps them to documents using semantic vector matching at the chunk level. Below are the core reasoning chains:

| User Query | Targeted Vault Assets | Reasoning & Chunk Extraction Steps |
|---|---|---|
| *"What is my PAN number?"* | `PAN Card` (Summary / Meta chunks) | Match PAN Card -> Extract decrypted `pan_number` field. Mask digits except last 4. |
| *"When does my driving licence expire?"* | `Driving Licence` (General chunks) | Match DL -> Extract decrypted `expiry_date` -> Alert user if upcoming. |
| *"What were my Class 12 marks in Physics?"* | `Class 12 Marksheet` (Marks table chunk) | Match Class 12 marksheet -> Retrieve specific subject scores -> Extract Physics score. |
| *"Which company gave me my first job and what was my CTC?"* | `Offer Letter` (CTC/Joining chunks) | Retrieve CTC and Date chunks -> Extract `company_name`, `ctc`, `joining_date`. |
| *"Summarize my entire academic history"* | `Academic Records` (All marksheets) | Merge and sort academic chunks chronologically -> Generate narrative summary. |
| *"What documents do I need to renew in the next 6 months?"* | All Documents | Scan all decrypted `action_items.expiry_date` values -> Filter dates within 180 days -> Generate list. |
| *"What is my blood type?"* | `Medical Reports` (Medical chunks) | Search medical chunks for keywords: "blood group", "blood type", "A+", "O-" -> Extract match. |
| *"Show me my resume skills"* | `Resume` (Skills chunk) | Target vector search directly at "Skills" section chunk of Resume -> Retrieve text snippet. |

---

## 2. Local Fallback Resolver (Online/Offline Resilience)

To ensure the system works offline or without a local Ollama service running, we implement a rule-based query parser inside `RAGPipeline._answer_with_local_rules`.

### How the Local Resolver Works:
1. **Keyword Analysis:** Uses regular expressions to match intent (e.g. checks if query contains "pan", "aadhaar", "marks", "job", "expire").
2. **Context Filtering:** Filters the top-matching document chunks returned by ChromaDB vector search.
3. **JSON Extraction:** Extracts targeted keys directly from the PostgreSQL database `extracted_json` text column.
4. **Formatting & Masking:** Applies masking helper functions (e.g. hides middle numbers on Aadhaar/PAN) and prints cited responses.
5. **Citations Rendering:** Displays the specific matched **Section** (e.g., *Skills*, *Education*) and **Similarity match percentage** on the frontend citations card.
