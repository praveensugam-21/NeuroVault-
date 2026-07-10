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

class RAGPipeline:
    @staticmethod
    def answer_query(db: Session, user_id: int, question: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Retrieves relevant document chunks and answers the query.
        Uses Ollama if available, otherwise falls back to a smart local rules reasoning engine.
        Ensures full privacy, absolute local execution, and handles multi-turn conversation context.
        """
        history = history or []
        
        # Step 1: Multi-stage Chunk Retrieval
        # Query semantic chunks (top_k=6 diverse chunks selected via MMR and Cross-Encoder)
        search_hits = EmbeddingService.search(user_id=user_id, query=question, top_k=6)
        
        citations = []
        doc_chunks = {}  # document_id -> {doc, hits}
        
        # Gather matching chunks and group by document
        for hit in search_hits:
            doc_id = hit["document_id"]
            doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
            if doc and doc.status == "COMPLETE" and not doc.is_locked:
                if doc_id not in doc_chunks:
                    doc_chunks[doc_id] = {
                        "doc": doc,
                        "hits": []
                    }
                doc_chunks[doc_id]["hits"].append(hit)
                
                # Add chunk metadata to citations
                citations.append({
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "category": doc.category or "General",
                    "snippet": hit["text"][:300],
                    "similarity": hit.get("similarity", 0.8),
                    "section": hit["metadata"].get("section", "General"),
                    "chunk_index": hit["metadata"].get("chunk_index", 0)
                })

        # SQL keyword search fallback if semantic search returns absolutely nothing
        if not doc_chunks:
            logger.info("Semantic search yielded no chunk results. Falling back to SQL keyword search.")
            q_terms = [term.strip().lower() for term in re.split(r'\s+', question) if len(term.strip()) > 2]
            if q_terms:
                sql_docs = db.query(Document).filter(
                    Document.user_id == user_id,
                    Document.status == "COMPLETE"
                ).all()
                
                for doc in sql_docs:
                    if doc.is_locked:
                        continue
                    
                    # Compute keyword match score
                    doc_text = f"{doc.name} {doc.category or ''} {doc.document_type or ''} {doc.summary or ''}".lower()
                    matches = sum(1 for term in q_terms if term in doc_text)
                    if matches > 0:
                        snippet = doc.summary or doc.name
                        similarity_score = 0.5 + (0.05 * matches)
                        
                        citations.append({
                            "document_id": doc.id,
                            "document_name": doc.name,
                            "category": doc.category or "General",
                            "snippet": snippet[:300],
                            "similarity": similarity_score,
                            "section": "General",
                            "chunk_index": 0
                        })
                        
                        doc_chunks[doc.id] = {
                            "doc": doc,
                            "hits": [{
                                "text": snippet,
                                "metadata": {"section": "General", "chunk_index": 0}
                            }]
                        }

        # Check if vault is empty
        all_completed_docs = db.query(Document).filter(
            Document.user_id == user_id, 
            Document.status == "COMPLETE"
        ).all()

        if not all_completed_docs:
            return {
                "answer": "🔒 **Welcome to your private IRIS Vault!**\n\nI couldn't find any documents in your vault yet. Please upload files (such as your **Aadhaar Card, PAN Card, Driving Licence, Marksheets, Resume, or Bank Statements**) using the Upload page.\n\nOnce uploaded, I will automatically classify them, split them into semantic chunks, and let you ask questions about them securely and offline.",
                "citations": [],
                "retrieval_method": "empty_vault"
            }

        # Build context from merged chunks (grouped by document and sorted by chunk index)
        context_parts = []
        for doc_id, data in doc_chunks.items():
            doc = data["doc"]
            hits = data["hits"]
            
            # Sort chunks to ensure reading continuity
            hits.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
            
            merged_chunks_text = "\n\n".join([
                f"[Section: {hit['metadata'].get('section', 'General')} (Chunk {hit['metadata'].get('chunk_index', 0)})]\n{hit['text']}"
                for hit in hits
            ])

            # Decrypt fields safely
            decrypted_json_str = "{}"
            if doc.extracted_json:
                try:
                    decrypted_json_str = EncryptionService.decrypt(doc.extracted_json)
                except Exception as e:
                    logger.error(f"Decryption of document {doc.id} failed: {e}")

            try:
                extracted_fields = json.loads(decrypted_json_str) if decrypted_json_str else {}
            except Exception:
                extracted_fields = {}

            fields_str = ", ".join([f"{k}: {v}" for k, v in extracted_fields.items() if not isinstance(v, (dict, list))])

            context_parts.append(
                f"Document: {doc.name}\n"
                f"Type: {doc.document_type or 'Unknown'}\n"
                f"Category: {doc.category or 'General'}\n"
                f"Key Metadata: {fields_str or 'None'}\n"
                f"Relevant Text Passages:\n{merged_chunks_text}"
            )

        context_text = "\n\n---\n\n".join(context_parts)
        retrieval_method = "vector_chunks" if search_hits else "sql_fallback"

        # Log query context details for debugging/observability
        logger.info(f"RAG Query: '{question}'")
        logger.info(f"Retrieved {len(citations)} chunk citations.")
        logger.debug(f"Final Prompt Context:\n{context_text}")

        # Step 2: Query LLM or fall back to Smart Local Rules Engine
        from app.services.ollama_service import OllamaService
        if OllamaService.is_available():
            try:
                logger.info("Routing query to local Ollama instance...")
                return RAGPipeline._answer_with_ollama(question, context_text, citations, history)
            except Exception as e:
                logger.error(f"Ollama generation failed: {e}. Falling back to Smart Local Rules.")

        logger.info("Running query through Smart Local Rules Engine...")
        return RAGPipeline._answer_with_local_rules(question, citations, db, user_id, history, all_completed_docs)

    @staticmethod
    def _answer_with_ollama(question: str, context: str, citations: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        from app.services.ollama_service import OllamaService
        
        # Build chat history context
        history_context = ""
        if history:
            history_context = "Previous Conversation History:\n"
            for msg in history[-5:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_context += f"{role}: {msg.get('content')}\n"
            history_context += "\n"

        prompt = f"""
You are the IRIS AI Memory Assistant, a secure personal document intelligence assistant.
Answer the user's question using ONLY the retrieved document contexts below.

Guidelines:
1. Cite the document names and specific sections when reporting facts (e.g. "According to your Aadhaar Card, your address is..." or "Under the Experience section of your Resume, you worked at...").
2. Use markdown formatting (bold, tables, bullet points) to present information clearly.
3. If the information is not present in the contexts, state clearly that you cannot find it in the vault. Do NOT make up information.
4. Maintain context from previous conversation history if provided.

{history_context}
Retrieved Document Contexts:
{context}

User Question: {question}

Provide a professional, formatted, and cited response:
"""
        answer = OllamaService.generate_completion(prompt)
        if not answer:
            raise RuntimeError("Ollama returned an empty response.")
            
        return {
            "answer": answer,
            "citations": citations,
            "retrieval_method": "ollama_chunks"
        }

    @staticmethod
    def _answer_with_local_rules(
        question: str,
        citations: List[Dict[str, Any]],
        db: Session,
        user_id: int,
        history: List[Dict[str, Any]],
        all_completed_docs: List[Document]
    ) -> Dict[str, Any]:
        """
        Smart Local Rules Engine that parses the user's query and outputs highly detailed,
        fully private responses using actual database records.
        """
        q_lower = question.lower()
        
        # Load all user document entities with decrypted JSONs
        docs_metadata = []
        for doc in all_completed_docs:
            decrypted_json_str = "{}"
            if doc.extracted_json:
                try:
                    decrypted_json_str = EncryptionService.decrypt(doc.extracted_json)
                except Exception:
                    pass
            try:
                extracted_fields = json.loads(decrypted_json_str) if decrypted_json_str else {}
            except Exception:
                extracted_fields = {}
                
            docs_metadata.append({
                "doc": doc,
                "fields": extracted_fields
            })

        # --- RULE 1: Broad Vault Summary / Status Queries ---
        is_summary_query = any(w in q_lower for w in ["summarize", "summary", "list", "what documents", "what do i have", "show all", "my vault", "overview", "what are in my"])
        if is_summary_query:
            markdown = "### 📂 Your IRIS Vault Summary\n\n"
            markdown += "Here is a complete list of documents currently processed and secure in your vault:\n\n"
            markdown += "| Document Name | Type | Category | Upload Date | Status |\n"
            markdown += "| :--- | :--- | :--- | :--- | :--- |\n"
            
            for item in docs_metadata:
                doc = item["doc"]
                date_str = doc.created_at.strftime("%d %b %Y")
                lock_status = "🔒 Locked" if doc.is_locked else "🔓 Unlocked"
                markdown += f"| **{doc.name}** | {doc.document_type or 'General'} | {doc.category or 'General'} | {date_str} | {lock_status} |\n"
            
            # Add missing document alerts
            key_doc_types = ["Aadhaar Card", "PAN Card", "Driving Licence", "Class 10 Marksheet", "Class 12 Marksheet", "Resume", "Bank Statement", "Vehicle RC"]
            uploaded_types = {item["doc"].document_type for item in docs_metadata}
            missing = [k for k in key_doc_types if k not in uploaded_types]
            
            if missing:
                markdown += "\n\n⚠️ **Recommended uploads to complete your profile:**\n"
                for m in missing:
                    markdown += f"- [ ] {m}\n"
            else:
                markdown += "\n\n✨ **Excellent! All recommended key identity and financial documents have been uploaded.**"
                
            return {
                "answer": markdown,
                "citations": citations[:5] if citations else [{"document_id": d["doc"].id, "document_name": d["doc"].name, "category": d["doc"].category or "General", "snippet": d["doc"].summary or "No summary available"} for d in docs_metadata[:5]],
                "retrieval_method": "local_rules_summary"
            }

        # --- RULE 2: PAN Card Query ---
        if "pan" in q_lower:
            for item in docs_metadata:
                doc = item["doc"]
                fields = item["fields"]
                if doc.document_type == "PAN Card" or "pan" in doc.name.lower():
                    pan = fields.get("pan_number") or fields.get("pan") or fields.get("number")
                    name = fields.get("name") or fields.get("full_name")
                    dob = fields.get("dob") or fields.get("date_of_birth")
                    father = fields.get("father_name") or fields.get("fathers_name")
                    
                    if pan:
                        # Mask PAN for privacy: first 5 and last 1 visible
                        masked_pan = f"{pan[:5]}****{pan[-1]}" if len(pan) >= 10 else pan
                        ans = f"💳 **PAN Card Details found in '{doc.name}':**\n\n"
                        ans += f"- **PAN Number:** `{masked_pan}`\n"
                        if name: ans += f"- **Name:** {name}\n"
                        if dob: ans += f"- **DOB:** {dob}\n"
                        if father: ans += f"- **Father's Name:** {father}\n"
                        return {
                            "answer": ans,
                            "citations": citations[:1] if citations else [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or f"PAN details for {name}"}],
                            "retrieval_method": "local_rules_pan"
                        }

        # --- RULE 3: Aadhaar Card Query ---
        if "aadhaar" in q_lower or "aadhar" in q_lower:
            for item in docs_metadata:
                doc = item["doc"]
                fields = item["fields"]
                if doc.document_type == "Aadhaar Card" or "aadhaar" in doc.name.lower() or "aadhar" in doc.name.lower():
                    num = fields.get("aadhaar_number") or fields.get("uid") or fields.get("number")
                    name = fields.get("name") or fields.get("full_name")
                    gender = fields.get("gender") or fields.get("sex")
                    dob = fields.get("dob") or fields.get("date_of_birth")
                    addr = fields.get("address")
                    
                    if num:
                        masked = f"XXXX-XXXX-{num[-4:]}" if len(num) >= 4 else num
                        ans = f"🆔 **Aadhaar Card Details found in '{doc.name}':**\n\n"
                        ans += f"- **Aadhaar Number:** `{masked}`\n"
                        if name: ans += f"- **Name:** {name}\n"
                        if gender: ans += f"- **Gender:** {gender}\n"
                        if dob: ans += f"- **DOB/Year of Birth:** {dob}\n"
                        if addr: ans += f"- **Address:** {addr}\n"
                        return {
                            "answer": ans,
                            "citations": citations[:1] if citations else [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or f"Aadhaar card for {name}"}],
                            "retrieval_method": "local_rules_aadhaar"
                        }

        # --- RULE 4: Driving Licence Query ---
        if "driving licence" in q_lower or "driving license" in q_lower or "dl" in q_lower:
            for item in docs_metadata:
                doc = item["doc"]
                fields = item["fields"]
                if doc.document_type == "Driving Licence" or "driving" in doc.name.lower() or "dl" in doc.name.lower():
                    dl_num = fields.get("dl_number") or fields.get("licence_number")
                    exp = fields.get("expiry_date") or fields.get("validity")
                    name = fields.get("name")
                    classes = fields.get("vehicle_classes") or fields.get("class")
                    if isinstance(classes, list):
                        classes = ", ".join(classes)
                        
                    ans = f"🚗 **Driving Licence Details found in '{doc.name}':**\n\n"
                    if dl_num: ans += f"- **DL Number:** `{dl_num}`\n"
                    if name: ans += f"- **Name:** {name}\n"
                    if exp: ans += f"- **Expiry Date:** {exp}\n"
                    if classes: ans += f"- **Authorized Vehicle Classes:** {classes}\n"
                    return {
                        "answer": ans,
                        "citations": citations[:1] if citations else [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or "DL Details"}],
                        "retrieval_method": "local_rules_dl"
                    }

        # --- RULE 5: Academic marksheet/grade queries ---
        if any(w in q_lower for w in ["marks", "subject", "score", "percentage", "gpa", "cgpa", "grade", "physics", "math", "chemistry", "english"]):
            for item in docs_metadata:
                doc = item["doc"]
                fields = item["fields"]
                if doc.category == "Academic Records" or any(w in doc.name.lower() for w in ["marksheet", "marks", "grade", "10th", "12th"]):
                    percentage = fields.get("percentage") or fields.get("gpa_cgpa") or fields.get("marks")
                    school = fields.get("school_name") or fields.get("institution")
                    year = fields.get("year")
                    subjects = fields.get("subjects") or []
                    
                    ans = f"🎓 **Academic Record found in '{doc.name}':**\n\n"
                    if school: ans += f"- **Institution:** {school}\n"
                    if year: ans += f"- **Year:** {year}\n"
                    if percentage: ans += f"- **Performance Metric:** `{percentage}%`\n"
                    
                    if subjects:
                        ans += "\n**Subject Breakdown:**\n"
                        ans += "| Subject | Marks Obtained | Max Marks |\n"
                        ans += "| :--- | :--- | :--- |\n"
                        for sub in subjects:
                            if isinstance(sub, dict):
                                name = sub.get("subject_name") or sub.get("subject") or "Unknown"
                                ob = sub.get("marks_obtained") or sub.get("score") or "-"
                                mx = sub.get("max_marks") or sub.get("total") or "-"
                                ans += f"| {name} | {ob} | {mx} |\n"
                            else:
                                ans += f"| {sub} | - | - |\n"
                    return {
                        "answer": ans,
                        "citations": citations[:1] if citations else [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or "Academic records detail"}],
                        "retrieval_method": "local_rules_academic"
                    }

        # --- RULE 6: Professional salary/ctc/joining queries ---
        if any(w in q_lower for w in ["company", "salary", "ctc", "joining", "job", "designation", "role", "offer"]):
            for item in docs_metadata:
                doc = item["doc"]
                fields = item["fields"]
                if doc.category == "Professional Documents" or any(w in doc.name.lower() for w in ["offer", "appointment", "payslip", "salary"]):
                    company = fields.get("company_name") or fields.get("employer") or fields.get("company")
                    role = fields.get("designation") or fields.get("role")
                    ctc = fields.get("ctc") or fields.get("salary")
                    joining = fields.get("joining_date") or fields.get("date")
                    
                    ans = f"💼 **Professional details found in '{doc.name}':**\n\n"
                    if company: ans += f"- **Company:** {company}\n"
                    if role: ans += f"- **Designation/Role:** {role}\n"
                    if ctc: ans += f"- **CTC/Salary:** {ctc}\n"
                    if joining: ans += f"- **Joining Date:** {joining}\n"
                    return {
                        "answer": ans,
                        "citations": citations[:1] if citations else [{"document_id": doc.id, "document_name": doc.name, "category": doc.category or "General", "snippet": doc.summary or "Professional employment records"}],
                        "retrieval_method": "local_rules_professional"
                    }

        # --- RULE 7: Expiry or Renewals ---
        if any(w in q_lower for w in ["expire", "expiry", "renew", "validity", "valid"]):
            expiries = []
            for item in docs_metadata:
                doc = item["doc"]
                fields = item["fields"]
                exp = fields.get("expiry_date") or fields.get("validity")
                if exp:
                    expiries.append(f"- **{doc.document_type or 'Document'}** (*{doc.name}*) expires on `{exp}`")
            if expiries:
                ans = "📅 **Upcoming Expiries & Renewals:**\n\n" + "\n".join(expiries)
                return {
                    "answer": ans,
                    "citations": citations if citations else [{"document_id": d["doc"].id, "document_name": d["doc"].name, "category": d["doc"].category or "General", "snippet": d["doc"].summary or ""} for d in docs_metadata if d["fields"].get("expiry_date")][:4],
                    "retrieval_method": "local_rules_expiry"
                }

        # --- RULE 8: Default Fallback (General RAG Context Synthesis) ---
        if citations:
            ans = "🔍 **I searched your vault and found the following relevant information chunks:**\n\n"
            for c in citations:
                ans += f"📄 **From {c['document_name']}** (Section: {c.get('section', 'General')}, Similarity: {int(c.get('similarity', 0.8)*100)}%):\n"
                ans += f"> {c['snippet']}\n\n"
            return {
                "answer": ans,
                "citations": citations,
                "retrieval_method": "local_rules_chunks_fallback"
            }

        # --- RULE 9: Completely Unmatched ---
        return {
            "answer": "🤷 **I couldn't find a direct answer to that question in your vault documents.**\n\nTry asking about a specific value or document name (e.g. *'What is my PAN number?'*, *'Show my marksheet subjects'*, *'What documents are expiring?'*, or *'Give me a summary of my vault'*) or upload the relevant document.",
            "citations": [],
            "retrieval_method": "local_rules_unmatched"
        }
