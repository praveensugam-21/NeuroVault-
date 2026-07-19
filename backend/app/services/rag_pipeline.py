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
import logging
import re
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.models.document import Document
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("iris.rag")


_SYSTEM_PROMPT = """You are IRIS — Intelligent Retrieval and Information System."""

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
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        history = history or []

        search_hits = EmbeddingService.search(user_id=user_id, query=question, top_k=8)

        citations: List[Dict[str, Any]] = []
        doc_chunks: Dict[str, Dict[str, Any]] = {}

        for hit in search_hits:
            doc_id = hit["document_id"]
            doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()

            if doc and doc.status == "COMPLETE" and not doc.is_locked:
                doc_chunks.setdefault(doc_id, {"doc": doc, "hits": []})
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

        # SQL metadata search (kept from existing behavior)
        try:
            all_docs = db.query(Document).filter(Document.user_id == user_id, Document.status == "COMPLETE").all()
            cleaned_q = EmbeddingService.clean_query(question).lower()
            query_words = set(re.findall(r"\w+", cleaned_q))

            for doc in all_docs:
                if doc.is_locked:
                    continue

                fields = doc.get_extracted_fields() or {}
                matched_fields: Dict[str, Any] = {}

                for k, v in fields.items():
                    if not v or isinstance(v, (dict, list)):
                        continue
                    v_str = str(v).lower()
                    k_clean = str(k).replace("_", " ").lower()

                    k_words = set(re.findall(r"\w+", k_clean))
                    v_words = set(re.findall(r"\w+", v_str))

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
                            "document_type": doc.document_type,
                        },
                    }

                    doc_chunks.setdefault(doc.id, {"doc": doc, "hits": []})
                    if not any(h.get("chunk_id") == metadata_hit["chunk_id"] for h in doc_chunks[doc.id]["hits"]):
                        doc_chunks[doc.id]["hits"].append(metadata_hit)
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

        # SQL keyword fallback
        if not doc_chunks:
            q_terms = [t.strip().lower() for t in re.split(r"\s+", question) if len(t.strip()) > 2]
            if q_terms:
                sql_docs = db.query(Document).filter(Document.user_id == user_id, Document.status == "COMPLETE").all()
                for doc in sql_docs:
                    if doc.is_locked:
                        continue
                    doc_text = f"{doc.name} {doc.category or ''} {doc.document_type or ''} {doc.summary or ''}".lower()
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
                        doc_chunks[doc.id] = {"doc": doc, "hits": [{"text": snippet, "metadata": {"section": "General", "chunk_index": 0}}]}

        # Vault empty check
        all_completed_docs = db.query(Document).filter(Document.user_id == user_id, Document.status == "COMPLETE").all()
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

        # Context
        context_parts: List[str] = []
        for data in doc_chunks.values():
            doc = data["doc"]
            hits = sorted(data["hits"], key=lambda x: x["metadata"].get("chunk_index", 0))
            passages = "\n\n".join(
                f"[Section: {h['metadata'].get('section', 'General')} | Chunk {h['metadata'].get('chunk_index', 0)}]\n{h['text']}" for h in hits
            )
            extracted_fields = doc.get_extracted_fields() or {}
            fields_summary = ", ".join(f"{k}: {v}" for k, v in extracted_fields.items() if v and not isinstance(v, (dict, list)))
            context_parts.append(
                f"### Document: {doc.name}\n"
                f"- **Type**: {doc.document_type or 'Unknown'}\n"
                f"- **Category**: {doc.category or 'General'}\n"
                f"- **Key Extracted Fields**: {fields_summary or 'None extracted'}\n\n"
                f"**Relevant Text Passages:**\n{passages}"
            )

        context_text = "\n\n---\n\n".join(context_parts)

        # LLM routing
        retrieval_method = "vector_chunks" if search_hits else "sql_fallback"
        logger.info(f"RAG Query: '{question}' | Retrieved {len(citations)} citations | Method: {retrieval_method}")

        from app.services.gemini_service import GeminiService
        from app.services.ollama_service import OllamaService

        if GeminiService.is_available():
            try:
                return RAGPipeline._answer_with_gemini(question, context_text, citations, history)
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}")
                if GeminiService._is_temporary_error(e) and ("429" in str(e) or "quota" in str(e).lower() or "limit" in str(e).lower()):
                    return {
                        "answer": (
                            "⚠️ **Gemini API Rate Limit Exceeded (429 Resource Exhausted)**\n\n"
                            "The configured Gemini API key has exceeded its rate limit or free tier quota.\n\n"
                            "**How to fix this:**\n"
                            "- Wait a few seconds and try again.\n"
                            "- Set a custom pay-as-you-go Gemini API key in your **Settings** panel (Security & Settings → AI Configuration) or `.env` file."
                        ),
                        "citations": [],
                        "retrieval_method": "gemini_rate_limit"
                    }

        if OllamaService.is_available():
            try:
                return RAGPipeline._answer_with_ollama(question, context_text, citations, history)
            except Exception:
                pass

        return RAGPipeline._answer_with_local_rules(question, citations, db, user_id, history, all_completed_docs)

    @staticmethod
    def _answer_with_gemini(
        question: str,
        context: str,
        citations: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from app.services.gemini_service import GeminiService
        from app.services.pii_masker import PIIMasker

        pii_mapping: Dict[str, str] = {}

        masked_history = []
        for msg in history:
            masked_content, pii_mapping = PIIMasker.mask_text(msg.get("content", ""), pii_mapping)
            masked_history.append({"role": msg.get("role"), "content": masked_content})

        masked_context, pii_mapping = PIIMasker.mask_text(context, pii_mapping)
        masked_question, pii_mapping = PIIMasker.mask_text(question, pii_mapping)

        history_context = ""
        if masked_history:
            history_context = "## Conversation History\n"
            for msg in masked_history[-6:]:
                role = "User" if msg.get("role") == "user" else "IRIS"
                history_context += f"**{role}:** {msg.get('content')}\n\n"

        prompt = _PROMPT_TEMPLATE.format(
            system_prompt=_SYSTEM_PROMPT,
            history_context=history_context,
            context=masked_context,
            question=masked_question,
        )

        masked_answer = GeminiService.generate_completion(prompt)
        if not masked_answer:
            raise RuntimeError("Gemini returned an empty response.")

        unmasked_answer = PIIMasker.unmask_text(masked_answer, pii_mapping)
        return {"answer": unmasked_answer, "citations": citations, "retrieval_method": "gemini_chunks"}

    @staticmethod
    def _answer_with_ollama(
        question: str,
        context: str,
        citations: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
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

        return {"answer": answer, "citations": citations, "retrieval_method": "ollama_chunks"}

    @staticmethod
    def _answer_with_local_rules(
        question: str,
        citations: List[Dict[str, Any]],
        db: Session,
        user_id: int,
        history: List[Dict[str, Any]],
        all_completed_docs: List[Document],
    ) -> Dict[str, Any]:
        """Offline rules-based engine.

        Unit-test compatibility:
          - community cert must return retrieval_method local_rules_community_cert
          - resume skills must return retrieval_method local_rules_resume_skills
          - resume skills answer must include the original comma-separated substring
        """
        q_lower = (question or "").lower()

        docs_metadata = []
        for doc in all_completed_docs:
            extracted_fields = doc.get_extracted_fields() or {}
            docs_metadata.append({"doc": doc, "fields": extracted_fields})

        # Vault Overview
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

            return {
                "answer": md,
                "citations": citations[:5] if citations else [
                    {
                        "document_id": d["doc"].id,
                        "document_name": d["doc"].name,
                        "category": d["doc"].category or "General",
                        "snippet": d["doc"].summary or "No summary available",
                    } for d in docs_metadata[:5]
                ],
                "retrieval_method": "local_rules_summary",
            }

        # Community Certificate
        community_kws = [
            "community", "caste", "scheduled caste", "scheduled tribe",
            "adi dravidar", "backward class", "obc", "community certificate",
            "caste certificate", "my community",
        ]
        if any(w in q_lower for w in community_kws):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Community Certificate" or any(w in (doc.name or "").lower() for w in ["community", "caste", "cert"]):
                    community = fields.get("community") or fields.get("caste")
                    caste_cat = fields.get("caste_category") or fields.get("category")
                    cert_no = fields.get("certificate_number")

                    ans = "### 🪪 Community Certificate Details\n"
                    ans += f"**Source:** {doc.name}\n\n"
                    ans += "| Field | Value |\n| :--- | :--- |\n"
                    if community:
                        ans += f"| **Community** | {community} |\n"
                    if caste_cat:
                        ans += f"| **Caste Category** | {caste_cat} |\n"
                    if cert_no:
                        ans += f"| **Certificate No.** | `{cert_no}` |\n"

                    return {
                        "answer": ans,
                        "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or ""}],
                        "retrieval_method": "local_rules_community_cert",
                    }

        # Resume skills
        resume_kws = ["skills", "resume", "cv", "projects", "experience", "technical skills", "technologies", "programming", "languages"]
        if any(w in q_lower for w in resume_kws):
            for item in docs_metadata:
                doc, fields = item["doc"], item["fields"]
                if doc.document_type == "Resume" or any(w in (doc.name or "").lower() for w in ["resume", "cv"]):
                    skills = fields.get("skills")
                    ans = f"### 📄 Skills & Technical Expertise\n**Source:** {doc.name}\n\n"
                    if skills:
                        # keep comma-separated substring intact for unit tests
                        ans += "**Extracted Skills:**\n"
                        ans += f"{skills}"

                    return {
                        "answer": ans,
                        "citations": citations[:1] or [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "Professional Documents", "snippet": doc.summary or ""}],
                        "retrieval_method": "local_rules_resume_skills",
                    }

        # Generic fallback
        if citations:
            ans = "### 🔍 Relevant Information Found in Your Vault\n\n"
            for c in citations[:5]:
                similarity_pct = int(c.get("similarity", 0.8) * 100)
                ans += (
                    f"**From {c['document_name']}** — Section: *{c.get('section', 'General')}* — Relevance: `{similarity_pct}%`\n"
                    f"> {c['snippet']}\n\n"
                )
            return {"answer": ans, "citations": citations, "retrieval_method": "local_rules_chunks_fallback"}

        return {
            "answer": (
                "### ℹ️ IRIS Help & General Answer\n\n"
                "I couldn't locate a direct answer in your uploaded documents for this question.\n\n"
                "**Try one of these approaches:**\n"
                "- If your question is about a specific document, ask using the document type (PAN / Aadhaar / DL / Passport / Marksheets / Resume).\n"
                "- Ask for a specific field (name, DOB, address, mobile, email, expiry dates, skills, company, etc.).\n"
                "- Use the **Vault** page to confirm the document was processed and extracted correctly."
            ),
            "citations": [],
            "retrieval_method": "local_rules_unmatched",
        }

