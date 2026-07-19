"""
IRIS RAG Pipeline — Retrieval-Augmented Generation Engine
==========================================================
Core orchestration layer for the IRIS AI Memory Assistant.

Pipeline Order:
  1. ChromaDB semantic vector search (MMR + Cross-Encoder reranking)
  2. SQL keyword fallback (if vector search yields nothing)
  3. LLM routing: Gemini API (primary, with local PII masking)
              -> Ollama local LLM (offline fallback)
              -> Smart Local Rules Engine (always-offline fallback)
"""
import json
import logging
import re
from sqlalchemy.orm import Session
from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.encryption_service import EncryptionService
from app.models.document import Document
from typing import List, Dict, Any, Optional

logger = logging.getLogger("iris.rag")


# ── Shared prompt template for Gemini and Ollama ─────────────────────────────
_SYSTEM_PROMPT = """You are IRIS — Intelligent Retrieval and Information System, a highly professional, secure AI Memory Assistant.

Your role is to help the user retrieve accurate, well-structured information from their private personal document vault. You operate with the highest standards of accuracy, citation discipline, and professional communication.

## Core Behaviour Rules

1.  **Strict Grounding**: Answer ONLY from the retrieved document contexts provided. Do NOT hallucinate, infer beyond the text, or use any external knowledge.
2.  **Mandatory Citations**: Every factual claim MUST be attributed to its source document and section (e.g., "According to your **Resume** (Work Experience section), you worked at...").
3.  **Professional Formatting**: Structure all responses with markdown — use **bold** for labels, bullet lists for multiple items, and tables for comparative data (e.g., subject marks). Keep responses concise yet complete.
4.  **Privacy-First Mindset**: Sensitive values like Aadhaar numbers, PAN numbers, bank details, and passport numbers appear as placeholders (e.g., `[AADHAAR_0]`, `[PAN_0]`). Reference them exactly as given — do NOT expand, remove, or guess at their values.
5.  **Honest Acknowledgement**: If the requested information is not present in any retrieved context, respond clearly: "I could not find this information in your vault. Please ensure the relevant document has been uploaded."
6.  **No Fabrication**: Never invent names, numbers, dates, or any other detail not present in the retrieved contexts.
7.  **Conversational Continuity**: If conversation history is provided, maintain coherence with prior exchanges and avoid repeating the same information unnecessarily.
"""

_PROMPT_TEMPLATE = """{system_prompt}

---
{history_context}
## Retrieved Document Contexts

{context}

---

## User Question

{question}

---

## Your Response

Provide a professional, well-cited, markdown-formatted answer based strictly on the retrieved contexts above:
"""


class RAGPipeline:

    @staticmethod
    def answer_query(
        db: Session,
        user_id: int,
        question: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline entry point.
        Retrieves relevant document chunks and generates an AI answer.

        Args:
            db: SQLAlchemy database session.
            user_id: Authenticated user ID.
            question: The user's natural language question.
            history: Optional list of prior conversation turns.

        Returns:
            A dict with keys: answer, citations, retrieval_method.
        """
        history = history or []

        # ── Step 1: Semantic vector search (top_k=8 diverse chunks via MMR + Cross-Encoder) ──
        search_hits = EmbeddingService.search(user_id=user_id, query=question, top_k=8)

        citations = []
        doc_chunks: Dict[str, Dict] = {}

        for hit in search_hits:
            doc_id = hit["document_id"]
            doc = db.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id
            ).first()

            if doc and doc.status == "COMPLETE" and not doc.is_locked:
                if doc_id not in doc_chunks:
                    doc_chunks[doc_id] = {"doc": doc, "hits": []}
                doc_chunks[doc_id]["hits"].append(hit)

                citations.append({
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "category": doc.category or "General",
                    "snippet": hit["text"][:300],
                    "similarity": hit.get("similarity", 0.8),
                    "section": hit["metadata"].get("section", "General"),
                    "chunk_index": hit["metadata"].get("chunk_index", 0),
                })

        # ── Step 1b: Parallel SQL Metadata Search ──
        # Scan clean database fields in parallel to guarantee accurate retrieval for OCR-noisy scans
        try:
            all_docs = db.query(Document).filter(
                Document.user_id == user_id,
                Document.status == "COMPLETE"
            ).all()

            cleaned_q = EmbeddingService.clean_query(question).lower()
            query_words = set(re.findall(r'\w+', cleaned_q))

            for doc in all_docs:
                if doc.is_locked:
                    continue

                fields = doc.get_extracted_fields()
                matched_fields = {}

                for k, v in fields.items():
                    if not v or isinstance(v, (dict, list)):
                        continue
                    v_str = str(v).lower()
                    k_clean = str(k).replace("_", " ").lower()

                    k_words = set(re.findall(r'\w+', k_clean))
                    v_words = set(re.findall(r'\w+', v_str))

                    # Key overlap or value matching (e.g. "what is my PAN" matches key "pan_number"; name matches value)
                    if (query_words & k_words) or (query_words & v_words) or (cleaned_q in v_str) or (v_str in cleaned_q):
                        matched_fields[k] = v

                if matched_fields:
                    fields_str = "\n".join(f"- **{k.replace('_', ' ').title()}**: `{v}`" for k, v in matched_fields.items())
                    
                    metadata_hit = {
                        "document_id": doc.id,
                        "chunk_id": f"{doc.id}_verified_metadata",
                        "similarity": 1.0,
                        "text": f"Verified Database Fields:\n{fields_str}",
                        "metadata": {
                            "section": "Verified Fields",
                            "chunk_index": -1,
                            "document_type": doc.document_type
                        }
                    }

                    if doc.id not in doc_chunks:
                        doc_chunks[doc.id] = {"doc": doc, "hits": []}

                    # Inject if not already added
                    if not any(h.get("chunk_id") == f"{doc.id}_verified_metadata" for h in doc_chunks[doc.id]["hits"]):
                        doc_chunks[doc.id]["hits"].append(metadata_hit)

                        # Place verified metadata citation at the very front of citation list
                        citations.insert(0, {
                            "document_id": doc.id,
                            "document_name": doc.name,
                            "category": doc.category or "General",
                            "snippet": f"Verified Database Fields: {', '.join(f'{k}: {v}' for k, v in matched_fields.items())}",
                            "similarity": 1.0,
                            "section": "Verified Fields",
                            "chunk_index": -1,
                        })
        except Exception as e:
            logger.error(f"Parallel SQL metadata search failed: {e}")

        # ── Step 2: SQL keyword fallback if semantic search and metadata search found nothing ─────
        if not doc_chunks:
            logger.info("Semantic search returned no results. Falling back to SQL keyword search.")
            q_terms = [
                t.strip().lower()
                for t in re.split(r'\s+', question)
                if len(t.strip()) > 2
            ]
            if q_terms:
                sql_docs = db.query(Document).filter(
                    Document.user_id == user_id,
                    Document.status == "COMPLETE"
                ).all()

                for doc in sql_docs:
                    if doc.is_locked:
                        continue
                    doc_text = (
                        f"{doc.name} {doc.category or ''} "
                        f"{doc.document_type or ''} {doc.summary or ''}"
                    ).lower()
                    matches = sum(1 for t in q_terms if t in doc_text)
                    if matches > 0:
                        snippet = doc.summary or doc.name
                        citations.append({
                            "document_id": doc.id,
                            "document_name": doc.name,
                            "category": doc.category or "General",
                            "snippet": snippet[:300],
                            "similarity": round(0.5 + 0.05 * matches, 3),
                            "section": "General",
                            "chunk_index": 0,
                        })
                        doc_chunks[doc.id] = {
                            "doc": doc,
                            "hits": [{"text": snippet, "metadata": {"section": "General", "chunk_index": 0}}],
                        }

        # ── Step 3: Vault empty check ──────────────────────────────────────────────────────────
        all_completed_docs = db.query(Document).filter(
            Document.user_id == user_id,
            Document.status == "COMPLETE"
        ).all()

        if not all_completed_docs:
            return {
                "answer": (
                    "🔒 **Welcome to your private IRIS Vault!**\n\n"
                    "Your vault is currently empty. Please upload documents such as your "
                    "**Aadhaar Card, PAN Card, Driving Licence, Marksheets, Resume, or Bank Statements** "
                    "using the Upload page.\n\n"
                    "Once uploaded, IRIS will automatically classify them, extract key fields, "
                    "index them as semantic chunks, and allow you to ask intelligent questions — "
                    "all **100% privately on your own device**."
                ),
                "citations": [],
                "retrieval_method": "empty_vault",
            }

        # ── Step 4: Build structured LLM context from retrieved chunks ────────────────────────
        context_parts = []
        for doc_id, data in doc_chunks.items():
            doc = data["doc"]
            hits = sorted(data["hits"], key=lambda x: x["metadata"].get("chunk_index", 0))

            passages = "\n\n".join(
                f"[Section: {h['metadata'].get('section', 'General')} | Chunk {h['metadata'].get('chunk_index', 0)}]\n{h['text']}"
                for h in hits
            )

            extracted_fields = doc.get_extracted_fields()

            fields_summary = ", ".join(
                f"{k}: {v}"
                for k, v in extracted_fields.items()
                if v and not isinstance(v, (dict, list))
            )

            context_parts.append(
                f"### Document: {doc.name}\n"
                f"- **Type**: {doc.document_type or 'Unknown'}\n"
                f"- **Category**: {doc.category or 'General'}\n"
                f"- **Key Extracted Fields**: {fields_summary or 'None extracted'}\n\n"
                f"**Relevant Text Passages:**\n{passages}"
            )

        context_text = "\n\n---\n\n".join(context_parts)
        retrieval_method = "vector_chunks" if search_hits else "sql_fallback"

        logger.info(f"RAG Query: '{question}' | Retrieved {len(citations)} citations | Method: {retrieval_method}")

        # ── Step 5: Route to best available LLM ───────────────────────────────────────────────
        from app.services.gemini_service import GeminiService
        from app.services.ollama_service import OllamaService

        if GeminiService.is_available():
            try:
                logger.info("Routing to Gemini API with local PII masking...")
                return RAGPipeline._answer_with_gemini(question, context_text, citations, history)
            except Exception as e:
                logger.error(f"Gemini generation failed: {e}. Falling back to Ollama...")

        if OllamaService.is_available():
            try:
                logger.info("Routing to local Ollama LLM...")
                return RAGPipeline._answer_with_ollama(question, context_text, citations, history)
            except Exception as e:
                logger.error(f"Ollama generation failed: {e}. Falling back to Smart Local Rules Engine.")

        logger.info("All LLMs unavailable. Running Smart Local Rules Engine...")
        return RAGPipeline._answer_with_local_rules(question, citations, db, user_id, history, all_completed_docs)

    # ─────────────────────────────────────────────────────────────────────────
    # GEMINI PATH (Primary — with PII masking)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _answer_with_gemini(
        question: str,
        context: str,
        citations: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        from app.services.gemini_service import GeminiService
        from app.services.pii_masker import PIIMasker

        pii_mapping: Dict[str, str] = {}

        # Mask history
        masked_history = []
        for msg in history:
            masked_content, pii_mapping = PIIMasker.mask_text(msg.get("content", ""), pii_mapping)
            masked_history.append({"role": msg.get("role"), "content": masked_content})

        # Mask context and question
        masked_context, pii_mapping = PIIMasker.mask_text(context, pii_mapping)
        masked_question, pii_mapping = PIIMasker.mask_text(question, pii_mapping)

        # Build conversation history block
        history_context = ""
        if masked_history:
            history_context = "## Conversation History\n"
            for msg in masked_history[-6:]:
                role = "User" if msg.get("role") == "user" else "IRIS"
                history_context += f"**{role}:** {msg.get('content')}\n\n"

        # Render the full prompt
        prompt = _PROMPT_TEMPLATE.format(
            system_prompt=_SYSTEM_PROMPT,
            history_context=history_context,
            context=masked_context,
            question=masked_question,
        )

        masked_answer = GeminiService.generate_completion(prompt)
        if not masked_answer:
            raise RuntimeError("Gemini returned an empty response.")

        # Unmask locally — real PII values restored before sending to client
        unmasked_answer = PIIMasker.unmask_text(masked_answer, pii_mapping)

        return {
            "answer": unmasked_answer,
            "citations": citations,
            "retrieval_method": "gemini_chunks",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # OLLAMA PATH (Local LLM Fallback)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _answer_with_ollama(
        question: str,
        context: str,
        citations: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        from app.services.ollama_service import OllamaService

        history_context = ""
        if history:
            history_context = "## Conversation History\n"
            for msg in history[-6:]:
                role = "User" if msg.get("role") == "user" else "IRIS"
                history_context += f"**{role}:** {msg.get('content')}\n\n"

        prompt = _PROMPT_TEMPLATE.format(
            system_prompt=_SYSTEM_PROMPT,
            history_context=history_context,
            context=context,
            question=question,
        )

        answer = OllamaService.generate_completion(prompt)
        if not answer:
            raise RuntimeError("Ollama returned an empty response.")

        return {
            "answer": answer,
            "citations": citations,
            "retrieval_method": "ollama_chunks",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # SMART LOCAL RULES ENGINE (Always-offline database fallback)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _answer_with_local_rules(
        question: str,
        citations: List[Dict[str, Any]],
        db: Session,
        user_id: int,
        history: List[Dict[str, Any]],
        all_completed_docs: List[Document],
    ) -> Dict[str, Any]:
        """
        Fully offline rules-based engine.
        Uses decrypted database records to answer common structured queries
        without any external API calls.
        """
        q_lower = question.lower()

        # Preload all document metadata with decrypted fields
        docs_metadata = []
        for doc in all_completed_docs:
            extracted_fields = doc.get_extracted_fields()
            docs_metadata.append({"doc": doc, "fields": extracted_fields})

        # ── RULE 1: Vault Overview / Summary ─────────────────────────────────
        summary_keywords = [
            "summarize", "summary", "list", "what documents", "what do i have",
            "show all", "my vault", "overview", "what files", "vault status",
        ]
        if any(w in q_lower for w in summary_keywords):
            md = "### 📂 Your IRIS Vault — Document Overview\n\n"
            md += "| # | Document Name | Type | Category | Uploaded | Status |\n"
            md += "| :- | :--- | :--- | :--- | :--- | :--- |\n"
            for i, item in enumerate(docs_metadata, 1):
                doc = item["doc"]
                date_str = doc.created_at.strftime("%d %b %Y")
                lock = "🔒 Locked" if doc.is_locked else "🔓 Active"
                md += f"| {i} | **{doc.name}** | {doc.document_type or '—'} | {doc.category or '—'} | {date_str} | {lock} |\n"

            key_types = ["Aadhaar Card", "PAN Card", "Driving Licence", "Class 10 Marksheet",
                         "Class 12 Marksheet", "Resume", "Bank Statement", "Vehicle RC", "Passport"]
            uploaded_types = {item["doc"].document_type for item in docs_metadata}
            missing = [k for k in key_types if k not in uploaded_types]
            if missing:
                md += "\n\n⚠️ **Recommended documents to complete your profile:**\n"
                for m in missing:
                    md += f"- [ ] {m}\n"
            else:
                md += "\n\n✅ **All recommended identity and financial documents are present in your vault.**"

            return {
                "answer": md,
                "citations": citations[:5] if citations else [
                    {"document_id": d["doc"].id, "document_name": d["doc"].name,
                     "category": d["doc"].category or "General",
                     "snippet": d["doc"].summary or "No summary available"}
                    for d in docs_metadata[:5]
                ],
                "retrieval_method": "local_rules_summary",
            }

        # ── RULE 2: PAN Card ──────────────────────────────────────────────────
        if "pan" in q_lower:
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "PAN Card" or "pan" in doc.name.lower():
                    pan    = fields.get("pan_number") or fields.get("pan") or fields.get("number")
                    name   = fields.get("name") or fields.get("full_name")
                    dob    = fields.get("dob") or fields.get("date_of_birth")
                    father = fields.get("father_name") or fields.get("fathers_name")
                    if pan:
                        masked_pan = f"{pan[:5]}****{pan[-1]}" if len(pan) >= 10 else pan
                        ans = f"### 💳 PAN Card Details\n**Source:** {doc.name}\n\n"
                        ans += f"| Field | Value |\n| :--- | :--- |\n"
                        ans += f"| **PAN Number** | `{masked_pan}` |\n"
                        if name:   ans += f"| **Name** | {name} |\n"
                        if dob:    ans += f"| **Date of Birth** | {dob} |\n"
                        if father: ans += f"| **Father's Name** | {father} |\n"
                        return {"answer": ans,
                                "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                                "retrieval_method": "local_rules_pan"}

        # ── RULE 2.5: Community Certificate ────────────────────────────────────
        community_kws = [
            "community", "caste", "scheduled caste", "scheduled tribe",
            "adi dravidar", "backward class", "obc", "community certificate",
            "caste certificate", "my community", "community name",
        ]
        if any(w in q_lower for w in community_kws):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Community Certificate" or any(
                    w in doc.name.lower() for w in ["community", "caste", "cert"]
                ):
                    community  = fields.get("community") or fields.get("caste")
                    caste_cat  = fields.get("caste_category") or fields.get("category")
                    cert_no    = fields.get("certificate_number")
                    name       = fields.get("name")
                    district   = fields.get("district")
                    authority  = fields.get("issuing_authority")
                    father     = fields.get("father_name")

                    ans = f"### 🪪 Community Certificate Details\n**Source:** {doc.name}\n\n"
                    ans += f"| Field | Value |\n| :--- | :--- |\n"
                    if name:       ans += f"| **Name** | {name} |\n"
                    if community:  ans += f"| **Community** | {community} |\n"
                    if caste_cat:  ans += f"| **Caste Category** | {caste_cat} |\n"
                    if cert_no:    ans += f"| **Certificate No.** | `{cert_no}` |\n"
                    if father:     ans += f"| **Father's Name** | {father} |\n"
                    if district:   ans += f"| **District** | {district} |\n"
                    if authority:  ans += f"| **Issuing Authority** | {authority} |\n"

                    if not any([community, caste_cat, cert_no, name]):
                        # Fields not yet extracted — tell user to re-upload
                        ans = (
                            "### 🪪 Community Certificate\n"
                            f"**Source:** {doc.name}\n\n"
                            "⚠️ Key fields (community, caste category) could not be extracted from this document. "
                            "This is likely due to low OCR quality on the scanned image. "
                            "Please try re-uploading a clearer scan of your Community Certificate."
                        )

                    return {
                        "answer": ans,
                        "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name,
                                                        "category": doc.category or "Identity Documents",
                                                        "snippet": doc.summary or ""}],
                        "retrieval_method": "local_rules_community_cert"
                    }

        # ── RULE 3: Aadhaar Card ─────────────────────────────────────────────
        if "aadhaar" in q_lower or "aadhar" in q_lower:
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Aadhaar Card" or "aadhaar" in doc.name.lower() or "aadhar" in doc.name.lower():
                    num    = fields.get("aadhaar_number") or fields.get("uid") or fields.get("number")
                    name   = fields.get("name") or fields.get("full_name")
                    gender = fields.get("gender") or fields.get("sex")
                    dob    = fields.get("dob") or fields.get("date_of_birth")
                    addr   = fields.get("address")
                    if num:
                        masked = f"XXXX-XXXX-{num[-4:]}" if len(num) >= 4 else num
                        ans = f"### 🆔 Aadhaar Card Details\n**Source:** {doc.name}\n\n"
                        ans += f"| Field | Value |\n| :--- | :--- |\n"
                        ans += f"| **Aadhaar Number** | `{masked}` |\n"
                        if name:   ans += f"| **Name** | {name} |\n"
                        if gender: ans += f"| **Gender** | {gender} |\n"
                        if dob:    ans += f"| **Date of Birth** | {dob} |\n"
                        if addr:   ans += f"| **Address** | {addr} |\n"
                        return {"answer": ans,
                                "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                                "retrieval_method": "local_rules_aadhaar"}

        # ── RULE 4: Driving Licence ──────────────────────────────────────────
        if any(w in q_lower for w in ["driving licence", "driving license", "driving", " dl "]):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Driving Licence" or "driving" in doc.name.lower():
                    dl_num  = fields.get("dl_number") or fields.get("licence_number")
                    exp     = fields.get("expiry_date") or fields.get("validity")
                    name    = fields.get("name")
                    classes = fields.get("vehicle_classes") or fields.get("class")
                    if isinstance(classes, list):
                        classes = ", ".join(classes)
                    ans = f"### 🚗 Driving Licence Details\n**Source:** {doc.name}\n\n"
                    ans += f"| Field | Value |\n| :--- | :--- |\n"
                    if dl_num:  ans += f"| **DL Number** | `{dl_num}` |\n"
                    if name:    ans += f"| **Name** | {name} |\n"
                    if exp:     ans += f"| **Expiry Date** | {exp} |\n"
                    if classes: ans += f"| **Vehicle Classes** | {classes} |\n"
                    return {"answer": ans,
                            "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                            "retrieval_method": "local_rules_dl"}

        # ── RULE 5: Passport ─────────────────────────────────────────────────
        if "passport" in q_lower:
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Passport" or "passport" in doc.name.lower():
                    p_num   = fields.get("passport_number") or fields.get("number")
                    name    = fields.get("name") or fields.get("full_name")
                    exp     = fields.get("expiry_date") or fields.get("date_of_expiry")
                    dob     = fields.get("dob") or fields.get("date_of_birth")
                    country = fields.get("nationality") or fields.get("country")
                    ans = f"### 🛂 Passport Details\n**Source:** {doc.name}\n\n"
                    ans += f"| Field | Value |\n| :--- | :--- |\n"
                    if p_num:   ans += f"| **Passport Number** | `{p_num}` |\n"
                    if name:    ans += f"| **Name** | {name} |\n"
                    if dob:     ans += f"| **Date of Birth** | {dob} |\n"
                    if exp:     ans += f"| **Expiry Date** | {exp} |\n"
                    if country: ans += f"| **Nationality** | {country} |\n"
                    return {"answer": ans,
                            "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                            "retrieval_method": "local_rules_passport"}

        # ── RULE 6: Academic Records ─────────────────────────────────────────
        academic_kws = ["marks", "subject", "score", "percentage", "gpa", "cgpa",
                        "grade", "physics", "math", "chemistry", "english", "marksheet"]
        if any(w in q_lower for w in academic_kws):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.category == "Academic Records" or any(w in doc.name.lower() for w in ["marksheet", "marks", "grade", "10th", "12th", "academic"]):
                    pct      = fields.get("percentage") or fields.get("gpa_cgpa") or fields.get("marks")
                    school   = fields.get("school_name") or fields.get("institution")
                    year     = fields.get("year")
                    subjects = fields.get("subjects") or []
                    ans = f"### 🎓 Academic Record\n**Source:** {doc.name}\n\n"
                    if school: ans += f"- **Institution:** {school}\n"
                    if year:   ans += f"- **Year:** {year}\n"
                    if pct:    ans += f"- **Overall Performance:** `{pct}%`\n"
                    if subjects:
                        ans += "\n**Subject-wise Breakdown:**\n"
                        ans += "| Subject | Marks Obtained | Max Marks |\n"
                        ans += "| :--- | :---: | :---: |\n"
                        for sub in subjects:
                            if isinstance(sub, dict):
                                s_name = sub.get("subject_name") or sub.get("subject") or "—"
                                s_ob   = sub.get("marks_obtained") or sub.get("score") or "—"
                                s_mx   = sub.get("max_marks") or sub.get("total") or "—"
                                ans += f"| {s_name} | {s_ob} | {s_mx} |\n"
                            else:
                                ans += f"| {sub} | — | — |\n"
                    return {"answer": ans,
                            "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                            "retrieval_method": "local_rules_academic"}

        # ── RULE 7.2: Skills / Resume ─────────────────────────────────────────
        resume_kws = ["skills", "resume", "cv", "projects", "experience", "programming", "technologies", "languages"]
        if any(w in q_lower for w in resume_kws):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Resume" or any(w in doc.name.lower() for w in ["resume", "cv"]):
                    name   = fields.get("name") or fields.get("full_name")
                    email  = fields.get("email")
                    phone  = fields.get("phone")
                    skills = fields.get("skills")

                    ans = f"### 📄 Resume & Technical Skills Details\n**Source:** {doc.name}\n\n"
                    ans += f"| Field | Value |\n| :--- | :--- |\n"
                    if name:   ans += f"| **Name** | {name} |\n"
                    if email:  ans += f"| **Email** | {email} |\n"
                    if phone:  ans += f"| **Phone** | {phone} |\n"
                    if skills: ans += f"| **Skills** | {skills} |\n"

                    if not any([name, email, phone, skills]) and doc.summary:
                        ans += f"\n\n**Summary:**\n{doc.summary}"
                    
                    return {
                        "answer": ans,
                        "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "Professional Documents", "snippet": doc.summary or ""}],
                        "retrieval_method": "local_rules_resume_skills"
                    }

        # ── RULE 7: Professional / Employment Documents ───────────────────────
        professional_kws = ["company", "salary", "ctc", "joining", "job", "designation",
                            "role", "offer", "employer", "employment", "appointment", "payslip"]
        if any(w in q_lower for w in professional_kws):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.category == "Professional Documents" or any(w in doc.name.lower() for w in ["offer", "appointment", "payslip", "salary"]):
                    company = fields.get("company_name") or fields.get("employer") or fields.get("company")
                    role    = fields.get("designation") or fields.get("role")
                    ctc     = fields.get("ctc") or fields.get("salary")
                    joining = fields.get("joining_date") or fields.get("date")
                    ans = f"### 💼 Professional Employment Details\n**Source:** {doc.name}\n\n"
                    ans += f"| Field | Value |\n| :--- | :--- |\n"
                    if company: ans += f"| **Company** | {company} |\n"
                    if role:    ans += f"| **Designation** | {role} |\n"
                    if ctc:     ans += f"| **CTC / Salary** | {ctc} |\n"
                    if joining: ans += f"| **Joining Date** | {joining} |\n"
                    return {"answer": ans,
                            "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                            "retrieval_method": "local_rules_professional"}

        # ── RULE 8: Expiry / Renewals ─────────────────────────────────────────
        if any(w in q_lower for w in ["expire", "expiry", "renew", "validity", "valid till", "valid until"]):
            expiries = []
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                exp = fields.get("expiry_date") or fields.get("validity")
                if exp:
                    expiries.append(
                        f"| **{doc.document_type or 'Document'}** | *{doc.name}* | `{exp}` |"
                    )
            if expiries:
                ans = "### 📅 Document Expiry & Renewal Tracker\n\n"
                ans += "| Document Type | File Name | Expiry Date |\n"
                ans += "| :--- | :--- | :--- |\n"
                ans += "\n".join(expiries)
                return {"answer": ans,
                        "citations": citations or [{"document_id": d["doc"].id, "document_name": d["doc"].name, "category": d["doc"].category or "General", "snippet": d["doc"].summary or ""} for d in docs_metadata if d["fields"].get("expiry_date")][:4],
                        "retrieval_method": "local_rules_expiry"}

        # ── RULE 9: General chunk fallback ────────────────────────────────────
        if citations:
            ans = "### 🔍 Relevant Information Found in Your Vault\n\n"
            for c in citations[:5]:
                similarity_pct = int(c.get("similarity", 0.8) * 100)
                ans += (
                    f"**From {c['document_name']}** "
                    f"— Section: *{c.get('section', 'General')}* "
                    f"— Relevance: `{similarity_pct}%`\n"
                    f"> {c['snippet']}\n\n"
                )
            return {"answer": ans, "citations": citations, "retrieval_method": "local_rules_chunks_fallback"}

        # ── RULE 10: Unmatched ────────────────────────────────────────────────
        return {
            "answer": (
                "### ❓ Information Not Found\n\n"
                "I could not locate a direct answer to your question in the vault documents.\n\n"
                "**Suggestions:**\n"
                "- Try asking about a specific document type (e.g. *\"What is my PAN number?\"*, "
                "*\"Show my marksheet subjects\"*, *\"When does my DL expire?\"*)\n"
                "- Ensure the relevant document has been uploaded and processed\n"
                "- Use the **Vault** page to browse all documents and their extracted fields"
            ),
            "citations": [],
            "retrieval_method": "local_rules_unmatched",
        }
