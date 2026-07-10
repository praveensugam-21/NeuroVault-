from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str # "user" or "assistant"
    content: str

class ChatQuery(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = Field(default=[], description="Previous message history")

class ChatCitation(BaseModel):
    document_id: str
    document_name: str
    category: str
    snippet: str
    similarity: Optional[float] = Field(default=1.0, description="Semantic similarity score")

class ChatResponse(BaseModel):
    answer: str
    citations: List[ChatCitation] = []
    retrieval_method: Optional[str] = Field(default="local_rules", description="Engine used to retrieve/answer")
