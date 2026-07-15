from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Union

class ChatMessage(BaseModel):
    role: str # "user" or "assistant"
    content: str

class ChatQuery(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = Field(default=[], description="Previous message history")

class ChatCitation(BaseModel):
    document_id: Optional[Any] = Field(default=None, description="Document ID (int or str)")
    document_name: str
    category: str
    snippet: str
    similarity: Optional[float] = Field(default=1.0, description="Semantic similarity score")
    section: Optional[str] = Field(default="General", description="Document section")
    chunk_index: Optional[int] = Field(default=0, description="Chunk index in document")

    @field_validator("document_id", mode="before")
    @classmethod
    def coerce_document_id(cls, v: Any) -> Optional[str]:
        """Coerce int or any document_id to string for consistent serialisation."""
        return str(v) if v is not None else None

class ChatResponse(BaseModel):
    answer: str
    citations: List[ChatCitation] = []
    retrieval_method: Optional[str] = Field(default="local_rules", description="Engine used to retrieve/answer")
