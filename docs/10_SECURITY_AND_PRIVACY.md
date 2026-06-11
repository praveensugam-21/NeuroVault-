# NeuroVault AI — Security, Privacy & Compliance Standards

This document outlines the security architecture and privacy compliance standards implemented in NeuroVault AI.

---

## 1. Sensitive Data Masking Formats

To protect personally identifiable information (PII), sensitive identifiers are masked in all frontend views and only exposed in full after secondary PIN verification:

- **Aadhaar Numbers:** Masked to show only the last 4 digits.
  - Raw format: `123456789012`
  - Masked format: `XXXX-XXXX-9012`
- **PAN Numbers:** Masked to show only the first 5 and last 1 characters.
  - Raw format: `ABCDE1234F`
  - Masked format: `ABCDE****F`
- **Bank Account Numbers:** Masked to show only the last 4 digits.
  - Raw format: `30148291048`
  - Masked format: `XXXXXXX1048`

---

## 2. Authentication & Session Control (JWT)

We secure API endpoints using standard JSON Web Tokens (JWT):
1. **Login:** Users post credentials to `/api/auth/login`.
2. **Hashing:** Password matching is verified using `bcrypt` (via `passlib.context`).
3. **Token:** The server signs a JWT containing the user's email sub, valid for 24 hours (1440 minutes).
4. **Header:** The client stores the token in localStorage and attaches it to all subsequent requests inside the `Authorization: Bearer <token>` header.

---

## 3. Secondary PIN Locks

Highly sensitive documents (like tax papers or medical records) can be individually "Locked" with a secondary security PIN:
- The PIN is stored in the database as a strong bcrypt hash (`users.pin_hash`).
- When a document's `is_locked` flag is true, the backend router `/api/documents/{id}` checks if a valid PIN matches.
- If no PIN (or an invalid PIN) is provided, the API hides the `extracted_json` fields and prints a locked placeholder summary, preventing leaks if the user leaves their session open.

---

## 4. SQL Access Auditing

Every action taken on documents is recorded in the `audit_logs` table for compliance:
- **Recorded Fields:** User ID, Document ID, Action (VIEW, LOCK, UNLOCK, DELETE, UPLOAD), and Timestamp.
- Users can review their active security trail in the Settings dashboard.
