from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.chat import ChatQuery, ChatResponse
from app.services.security import SecurityService
from app.services.rag_pipeline import RAGPipeline
from typing import List, Dict, Any

router = APIRouter(prefix="/api/chat", tags=["Query Engine"])

@router.post("/", response_model=ChatResponse)
def ask_assistant(
    query_in: ChatQuery,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Interfaces with the AI Memory Assistant. Answers questions
    by reasoning over vector databases and database records.
    Supports multi-turn conversation history.
    """
    # Convert Pydantic history objects to dictionaries
    history_dicts = []
    if query_in.history:
        for msg in query_in.history:
            history_dicts.append({
                "role": msg.role,
                "content": msg.content
            })

    result = RAGPipeline.answer_query(
        db=db,
        user_id=current_user.id,
        question=query_in.question,
        history=history_dicts
    )
    return result

@router.get("/suggestions", response_model=List[str])
def get_chat_suggestions(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates smart dynamic suggestions based on what documents the user has actually uploaded.
    """
    documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.status == "COMPLETE"
    ).all()
    
    suggestions = ["Summarize my vault"]
    
    uploaded_types = {d.document_type for d in documents if d.document_type}
    
    if "PAN Card" in uploaded_types:
        suggestions.append("What is my PAN number?")
    if "Aadhaar Card" in uploaded_types:
        suggestions.append("What is my Aadhaar address?")
    if "Driving Licence" in uploaded_types:
        suggestions.append("When does my driving licence expire?")
    if any("marksheet" in d.name.lower() or d.category == "Academic Records" for d in documents):
        suggestions.append("Summarize my academic history")
    if any(d.category == "Professional Documents" for d in documents):
        suggestions.append("Show my employment summary")
        
    # Default fallback suggestions if vault is empty/small
    if len(suggestions) < 3:
        suggestions.append("What key documents am I missing?")
        suggestions.append("How do I lock my sensitive documents?")
        
    return suggestions[:4]
