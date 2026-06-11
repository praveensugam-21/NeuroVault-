import json
import logging
import re
from sqlalchemy.orm import Session
from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.models.document import Document
from typing import List, Dict, Any

logger = logging.getLogger("neurovault.rag")

class RAGPipeline:
    @staticmethod
    def answer_query(db: Session, user_id: int, question: str) -> Dict[str, Any]:
        """
        Retrieves relevant document fragments from vector database
        and feeds them into the reasoning LLM (Gemini) to produce cited answers.
        """
        # Step 1: Semantic search in ChromaDB
        search_hits = EmbeddingService.search(user_id=user_id, query=question, top_k=3)
        
        # Gather source documents info
        citations = []
        context_parts = []
        
        for hit in search_hits:
            doc_id = hit["document_id"]
            # Fetch full document from relational database
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                # If document is PIN locked, we do not expose its details in context unless unlocked.
                # In a real system, we restrict locked docs.
                if doc.is_locked:
                    continue
                
                citations.append({
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "category": doc.category or "General",
                    "snippet": doc.summary or hit["text"][:200]
                })
                
                # Append raw json + summary to prompt context
                fields_str = doc.extracted_json or "{}"
                context_parts.append(
                    f"Document Name: {doc.name}\n"
                    f"Category: {doc.category}\n"
                    f"Type: {doc.document_type}\n"
                    f"Summary: {doc.summary}\n"
                    f"Extracted Details: {fields_str}"
                )

        # If no documents are matching or found
        if not context_parts:
            return {
                "answer": "I couldn't find any relevant unlocked documents in your NeuroVault to answer that question. Please upload your identity, academic, or financial documents first.",
                "citations": []
            }

        context_text = "\n\n---\n\n".join(context_parts)

        # Step 2: Query Gemini or Fallback
        if settings.GEMINI_API_KEY:
            try:
                return RAGPipeline._answer_with_gemini(question, context_text, citations)
            except Exception as e:
                logger.error(f"Gemini RAG failed: {str(e)}. Falling back to local rules.")

        # Local keyword/schema matching fallback (accurate RAG simulation)
        return RAGPipeline._answer_with_local_rules(question, citations, db)

    @staticmethod
    def _answer_with_gemini(question: str, context: str, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are the NeuroVault AI Memory Assistant, a living personal knowledge intelligence engine.
        Answer the user's question using ONLY the retrieved document contexts below. 
        Cite the document names when reporting facts (e.g. "According to your Aadhaar Card, your address is...").
        If the information is not present in the context, state that you cannot find it in the vault.
        
        Retrieved Document Contexts:
        {context}
        
        User Question: {question}
        
        Provide a professional, clear, and cited response.
        """
        
        response = model.generate_content(prompt)
        return {
            "answer": response.text.strip(),
            "citations": citations
        }

    @staticmethod
    def _answer_with_local_rules(question: str, citations: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
        """
        Directly mines DB records corresponding to matched citations to answer common queries.
        Handles: PAN, Aadhaar, marksheet subjects, CTC, expiry, blood group.
        """
        q_lower = question.lower()
        
        # Load full records of cited documents
        docs = []
        for c in citations:
            doc = db.query(Document).filter(Document.id == c["document_id"]).first()
            if doc:
                docs.append(doc)

        # Match specific patterns
        # 1. PAN Number
        if "pan" in q_lower:
            for doc in docs:
                if doc.document_type == "PAN Card" and doc.extracted_json:
                    fields = json.loads(doc.extracted_json)
                    pan = fields.get("pan_number", "ABCDE1234F")
                    name = fields.get("name", "Praveen Kumar")
                    return {
                        "answer": f"Your PAN number is **{pan}** (issued to **{name}**), as retrieved from your **{doc.name}**.",
                        "citations": [citations[0]]
                    }

        # 2. Aadhaar Number
        if "aadhaar" in q_lower or "aadhar" in q_lower:
            for doc in docs:
                if doc.document_type == "Aadhaar Card" and doc.extracted_json:
                    fields = json.loads(doc.extracted_json)
                    num = fields.get("aadhaar_number", "123456789012")
                    # Mask Aadhaar: show only last 4 digits
                    masked = f"XXXX-XXXX-{num[-4:]}"
                    name = fields.get("name", "Praveen Kumar")
                    addr = fields.get("address", "")
                    return {
                        "answer": f"Your Aadhaar number is **{masked}** (belonging to **{name}**). The registered address is: *{addr}*. Retrieved from **{doc.name}**.",
                        "citations": [citations[0]]
                    }

        # 3. Driving Licence
        if "driving licence" in q_lower or "dl" in q_lower or "licence expire" in q_lower:
            for doc in docs:
                if doc.document_type == "Driving Licence" and doc.extracted_json:
                    fields = json.loads(doc.extracted_json)
                    num = fields.get("dl_number", "")
                    exp = fields.get("expiry_date", "")
                    classes = ", ".join(fields.get("vehicle_classes", []))
                    return {
                        "answer": f"Your Driving Licence (**{num}**) expires on **{exp}** and is authorized for vehicles: **{classes}**. Retrieved from **{doc.name}**.",
                        "citations": [citations[0]]
                    }

        # 4. Class 12 or 10 marksheet subjects
        if "marks" in q_lower or "subject" in q_lower or "score" in q_lower or "percentage" in q_lower or "physics" in q_lower or "math" in q_lower:
            for doc in docs:
                if doc.category == "Academic Records" and doc.extracted_json:
                    fields = json.loads(doc.extracted_json)
                    percentage = fields.get("percentage", 0.0)
                    subjects = fields.get("subjects", [])
                    
                    sub_marks = []
                    for s in subjects:
                        sub_marks.append(f"{s['subject_name']}: {s['marks_obtained']}/{s['max_marks']}")
                    
                    details = ", ".join(sub_marks)
                    return {
                        "answer": f"According to your **{doc.name}**, you obtained an overall score of **{percentage}%** with the following subject breakdown:\n\n{details}.",
                        "citations": [citations[0]]
                    }

        # 5. Offer Letter / Career
        if "company" in q_lower or "job" in q_lower or "ctc" in q_lower or "salary" in q_lower:
            for doc in docs:
                if doc.document_type == "Offer Letter" and doc.extracted_json:
                    fields = json.loads(doc.extracted_json)
                    company = fields.get("company_name", "Tech Solutions Inc")
                    ctc = fields.get("ctc", "")
                    date = fields.get("joining_date", "")
                    role = fields.get("designation", "Software Engineer")
                    return {
                        "answer": f"Your first job offer was from **{company}** for the role of **{role}** with a CTC of **{ctc}**, joining on **{date}**. Retrieved from your **{doc.name}**.",
                        "citations": [citations[0]]
                    }

        # 6. Expiry calendar
        if "expire" in q_lower or "renew" in q_lower:
            expiries = []
            for doc in docs:
                if doc.extracted_json:
                    fields = json.loads(doc.extracted_json)
                    exp = fields.get("expiry_date") or fields.get("validity")
                    if exp:
                        expiries.append(f"**{doc.document_type}** ({doc.name}) expiring on **{exp}**")
            
            if expiries:
                details = "\n- ".join(expiries)
                return {
                    "answer": f"Here are the upcoming renewal/expiry details found in your matching documents:\n\n- {details}",
                    "citations": citations
                }

        # 7. Default generic response summarizer
        summaries = []
        for doc in docs:
            summaries.append(f"From **{doc.name}** ({doc.document_type}): {doc.summary}")
            
        summary_text = "\n\n".join(summaries)
        return {
            "answer": f"Based on the documents matching your query, here is what I found:\n\n{summary_text}",
            "citations": citations
        }
