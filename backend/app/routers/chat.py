from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatQuery, ChatResponse
from app.services.security import SecurityService
from app.services.rag_pipeline import RAGPipeline

router = APIRouter(prefix="/api/chat", tags=["Query Engine"])

@router.post("/", response_model=ChatResponse)
def ask_assistant(
    query_in: ChatQuery,
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Interfaces with the AI Memory Assistant. Answers questions
    by reasoning over vector databases with inline citations.
    """
    result = RAGPipeline.answer_query(
        db=db,
        user_id=current_user.id,
        question=query_in.question
    )
    return result
