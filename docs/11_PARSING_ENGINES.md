# IRIS — Text Extraction & Parsing Engines

This document explains the roles of the local text extraction and natural language parsing engines used inside the IRIS document intelligence system.

---

## 1. Local OCR Engine (EasyOCR & Direct PDF Extraction)

### What it is
IRIS uses a local text extraction engine. For digital documents (like digital PDFs), it extracts text layers directly using `pypdf`. For scanned documents or image uploads, it runs **EasyOCR** (built on PyTorch, running CRAFT text detection and ResNet+LSTM recognition models) entirely locally on your device.

### Why we use it
To guarantee the system is **100% local-first and operational offline**, all text extraction runs on your machine. EasyOCR allows us to handle image-based documents without needing external network calls or cloud API keys.

---

## 2. Speech-to-Text Transcriber (Whisper Engine)

### What it is
Whisper is an open-source, automatic speech recognition (ASR) system trained on multilingual and multitasking data.

### Why we use it
For personal notes, users can record quick voice memos. The Whisper transcriber converts audio into clean, punctuated text which then undergoes the exact same indexing, entity extraction, and vector store pipeline as text notes.

---

## 3. Named Entity Recognition (spaCy Parser)

### What it is
spaCy is an industrial-strength Natural Language Processing library in Python. It includes fast pre-trained pipeline models capable of tagging parts of speech, parsing dependencies, and identifying Named Entities (NER).

### Why we use it
We use spaCy's English model (`en_core_web_sm`) to automatically extract key entities from text:
- **PERSON**: Names of individuals (e.g., "Ravi Kumar").
- **ORG**: Organizations (e.g., "Income Tax Department", "CBSE").
- **DATE**: Calendar dates (e.g., "12/04/2021", "2026-06-11").
- **GPE**: Geopolitical entities (e.g., "New Delhi", "Maharashtra").

These extracted entities form the basis of our **Knowledge Graph Linking** logic. If two separate documents contain the name "Ravi Kumar", spaCy tags them both, and the graph engine draws a relation between them.

---

## 4. Vector Embeddings (Sentence Transformers)

### What it is
Sentence Transformers is a Python framework for sentence, text, and image embeddings. We use the model `all-MiniLM-L6-v2`.

### Why we use it
It maps sentences and paragraphs into a dense vector space (384 dimensions). 
- Words or sentences with similar meanings are mapped close together.
- For example, the query "doctor's prescription" and the document text "medical receipt with list of drugs" will have high cosine similarity, even if they share zero exact keyword matches.
This powers our semantic search database (ChromaDB) to retrieve relevant records for context queries.

---

## 5. Local Natural Language Query Engine (Ollama Integration)

### What it is
Ollama is a lightweight, extensible framework for running inference models locally. We utilize the `qwen2.5:1.5b` model running locally.

### Why we use it
It orchestrates the contextual query pipeline:
1. Accepts user question.
2. Embeds the question.
3. Queries ChromaDB for top-K matching documents.
4. Formats the system instruction, documents context, and query into a structured prompt template.
5. Sends it to the local inference model (Ollama) and returns a clean, cited response.
