# Technology Choices & AI Privacy Guide

This document explains why we chose the core technologies for NeuroVault's self-hosted platform and clarifies how local privacy is maintained.

---

## 1. Are We Using Gemini or Ollama?

**NeuroVault is 100% local, offline, and runs entirely on Ollama.**

* **No Active Gemini API**: There are no active API integrations or code hooks calling Google's Gemini services.
* **Why `GEMINI_API_KEY` exists**: A setting placeholder for `GEMINI_API_KEY` exists in the configuration class and environment file template solely to support future development should you want to add cloud failovers. 
* **100% Privacy by Default**: By using Ollama on your local network/host, your document content, OCR, search vectors, and RAG conversations never leave your device.

---

## 2. Why We Chose These Specific Technologies

Here is the technical reasoning behind our architectural choices:

### A. Why PostgreSQL? (Instead of SQLite or MongoDB)
* **SQLite (Why we migrated away)**: SQLite is great for single-user apps, but it locks the entire database file during write operations. If you share your instance with friends or family, and multiple users upload documents at the same time, SQLite will throw `database is locked` errors.
* **PostgreSQL (Why we shifted)**: PostgreSQL handles thousands of concurrent read/write transactions seamlessly. It supports connection pooling (`QueuePool`), row-level security (RLS), and proper index configurations, making it the industry standard for production-grade self-hosting.
* **Why not MongoDB**: NeuroVault's data is highly relational. A user owns documents, documents have tags/entities, and documents link to other documents via graph edges. Relational databases enforce strict integrity rules (e.g. if a document is deleted, all its tags, entities, and graph relations are instantly deleted as well).

### B. Why Argon2id? (Instead of Bcrypt or SHA-256)
* **The Problem**: Standard hashing algorithms like SHA-256 can be calculated billions of times per second on modern graphics cards, making brute-force attacks easy if a database is leaked.
* **The Solution**: **Argon2id** is the winner of the Password Hashing Competition. It is designed to be memory-hard. By requiring 64MB of RAM per hash operation, it makes brute-forcing computationally and financially impossible for hackers using GPUs or ASICs.

### C. Why AES-256 (Fernet) Encryption at Rest?
* **The Threat**: If someone gains unauthorized access to your server or steals the physical hard drive, they could look at the PostgreSQL database files and read your extracted Aadhaar, PAN, and Bank Account numbers in plaintext.
* **The Solution**: Before writing the extracted JSON payload to the database, we encrypt it using AES-256. The decryption key lives only in your local `.env` file. Without this key, the database entries look like random garbled characters.

### D. Why Docker Compose & Nginx?
* **Docker Compose**: Standardizes the environment. It ensures that the React frontend, FastAPI backend, PostgreSQL, and ChromaDB configure themselves automatically with the correct ports and network bridge on any operating system (Windows, Mac, Linux, Synology NAS).
* **Nginx**: Operates as a security barrier. It blocks brute-force attempts at the gateway using rate-limiting zones (maximum 5 login attempts per minute per IP) before they ever hit the Python backend.
