# IRIS AI — Weekly Knowledge Digest

This document explains the backend heuristics that compile the personalized weekly digest.

---

## 1. Digest Components & Heuristics

The weekly digest engine (defined in `services/weekly_digest.py`) aggregates information into 6 categories:

1. **Expiry Warnings:** Finds completed documents where the parsed expiry date is within the next 30 days.
2. **New Connections:** Identifies graph edges (`GraphEdge`) created in the last 7 days that link documents together.
3. **Trending Topics:** Analyses the tag frequencies of all completed documents and highlights the top 3 tags.
4. **"Did you forget?"**: Resurfaces completed documents or text notes that have not been accessed in the last 60 days.
5. **Knowledge Score & Growth:** Prints the total document count and compares it against the expected 8 key documents to track growth.
6. **Recommended Next Action:** Generates targeted reminders (e.g. "Your Passport is expiring in 6 months, consider renewing it soon").

---

## 2. In-App Rendering

The frontend fetches this aggregated JSON payload via `/api/digest/weekly` and displays it to the user in a digest summary card or email layout, reminding them of tasks and new links in their second brain.
