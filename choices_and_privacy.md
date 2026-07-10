# Technology Choices & AI Privacy Guide

This document explains why we chose the core technologies for IRIS's self-hosted platform and clarifies how local privacy is maintained.

---

## 1. Are We Using Gemini, Ollama, or Local Rules?

**IRIS is 100% local, offline, and runs on a smart Local Rules Engine or local Ollama.**

* **No Gemini Integration**: There are no active API calls to Google's Gemini services, satisfying strict data privacy constraints.
* **Smart Local Rules Engine**: If Ollama is offline or not installed, the platform uses a local, regex-driven, decrypted database reasoning system. It extracts facts (like PAN, Aadhaar, marks, salary details) directly from database records instantly with 0% CPU overhead, 100% private and offline.
* **Ollama (Optional local LLM)**: Ollama runs inside a container. It reads model files completely locally from your device's workspace folder (on E: drive to preserve space on your C: drive), guaranteeing that no query data or document details leave your server.

---

## 2. Why We Chose These Specific Technologies

Here is the technical reasoning behind our architectural choices:

### A. SQLite (Development) & PostgreSQL (Production)
* **SQLite (Hybrid local setup)**: SQLite is used as the default development database. We configured it with `StaticPool`, `check_same_thread=False`, and **WAL (Write-Ahead Logging)** mode. This ensures multithreaded request safety and prevents database locking exceptions.
* **PostgreSQL (Production scaling)**: IRIS easily scales to PostgreSQL 15 in production/Docker environments, handling concurrent transactions and connection pooling seamlessly.
* **Why not MongoDB**: IRIS's data is highly relational. A user owns documents, documents have tags/entities, and documents link to other documents via graph edges. Relational databases enforce strict integrity rules (e.g. if a document is deleted, all its tags, entities, and graph relations are instantly deleted as well).

### B. Why Argon2id? (Instead of Bcrypt or SHA-256)
* **The Problem**: Standard hashing algorithms like SHA-256 can be calculated billions of times per second on modern graphics cards, making brute-force attacks easy if a database is leaked.
* **The Solution**: **Argon2id** is the winner of the Password Hashing Competition. It is designed to be memory-hard. By requiring 64MB of RAM per hash operation, it makes brute-forcing computationally and financially impossible for hackers using GPUs or ASICs.

### C. Why AES-256 (Fernet) Encryption at Rest?
* **The Threat**: If someone gains unauthorized access to your server or steals the physical hard drive, they could look at the PostgreSQL database files and read your extracted Aadhaar, PAN, and Bank Account numbers in plaintext.
* **The Solution**: Before writing the extracted JSON payload to the database, we encrypt it using AES-256. The decryption key lives only in your local `.env` file. Without this key, the database entries look like random garbled characters.

### D. Why Docker Compose & Nginx?
* **Docker Compose**: Standardizes the environment. It ensures that the React frontend, FastAPI backend, PostgreSQL, and ChromaDB configure themselves automatically with the correct ports and network bridge on any operating system (Windows, Mac, Linux, Synology NAS).
* **Nginx**: Operates as a security barrier. It blocks brute-force attempts at the gateway using rate-limiting zones (maximum 5 login attempts per minute per IP) before they ever hit the Python backend.
