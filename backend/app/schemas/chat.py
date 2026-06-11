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

class ChatResponse(BaseModel):
    answer: str
    citations: List[ChatCitation] = []
