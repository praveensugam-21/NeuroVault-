from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.graph import GraphResponse
from app.services.security import SecurityService
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])

@router.get("/", response_model=GraphResponse)
def get_knowledge_graph(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns nodes and edges mapping of user's personal knowledge network.
    Consumed by the React Flow interactive layout.
    """
    graph_data = KnowledgeGraphService.get_user_graph(db, current_user.id)
    return graph_data
