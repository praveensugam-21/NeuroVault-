# NeuroVault AI — AI & NLP Tools Deep Dive

This document explains the roles of the AI tools, models, and libraries used inside the NeuroVault AI engine. It covers what they are, why we use them, and how they function.

---

## 1. Google Gemini Vision API (Primary Understanding Engine)

### What it is
Google's Gemini model series includes native multimodal vision capabilities. Instead of treating OCR (text scanning) and reasoning (understanding text) as two separate steps, Gemini does them simultaneously.

### Why we use it
Traditional pipelines use an OCR library (like Tesseract) to get raw text, followed by an LLM to parse that text. This fails when:
1. The OCR engine misreads text (e.g. `O` instead of `0`, or misses decimal points in mark sheets).
2. The layout is complex (e.g. multi-column medical reports or side-by-side transaction tables).

Gemini Vision looks at the **document image** directly, understands its visual formatting, handles low-contrast scans, and directly outputs structured JSON schemas with high accuracy.

### Fallback Mechanism
If the Gemini API key is missing, rate-limited, or calls fail, the pipeline falls back to **EasyOCR** for local text extraction, paired with rule-based heuristics and local fallback processing.

---

## 2. Whisper AI (Speech-to-Text)

### What it is
OpenAI's Whisper is an open-source, automatic speech recognition (ASR) system trained on 680,000 hours of multilingual and multitasking web data.

### Why we use it
For personal notes, users often want to record quick voice memos (e.g., "Note to self: the car servicing is scheduled for next Tuesday, need to bring the insurance copy"). Whisper converts audio into clean, punctuated text which then undergoes the exact same indexing, entity extraction, and vector store pipeline as text notes.

---

## 3. EasyOCR (Offline OCR Backup)

### What it is
EasyOCR is a python library for Optical Character Recognition. It is built on PyTorch and utilizes deep learning models: CRAFT (for text detection) and ResNet+LSTM (for text recognition).

### Why we use it
To guarantee the system is **100% local-first and operational offline**, we need a local OCR engine. If Gemini is unavailable, EasyOCR scans document images locally to extract raw text, which we can parse with local regex engines.

---

## 4. spaCy NER (Named Entity Recognition)

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

## 5. Sentence Transformers (Vector Embeddings)

### What it is
Sentence Transformers is a Python framework for state-of-the-art sentence, text, and image embeddings. We use the model `all-MiniLM-L6-v2`.

### Why we use it
It maps sentences and paragraphs into a dense vector space (384 dimensions). 
- Words or sentences with similar meanings are mapped close together.
- For example, the query "doctor's prescription" and the document text "medical receipt with list of drugs" will have high cosine similarity, even if they share zero exact keyword matches.
This powers our semantic search database (ChromaDB) to retrieve relevant records for RAG (Retrieval-Augmented Generation).

---

## 6. LangChain & RAG Pipeline Orchestration

### What it is
LangChain is a popular framework for building applications powered by language models.

### Why we use it
It simplifies the RAG (Retrieval-Augmented Generation) pipeline:
1. Accepts user question.
2. Embeds the question.
3. Queries ChromaDB for top-K matching documents.
4. Formatting the system instruction, documents context, and query into a structured prompt template.
5. Sending it to the LLM (Gemini) and returning a clean, cited response.
