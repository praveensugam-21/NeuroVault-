from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any
from datetime import datetime
import json

class TagSchema(BaseModel):
    tag_name: str

    class Config:
        from_attributes = True

class DocumentTagResponse(BaseModel):
    id: int
    tag_name: str

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str
    name: str
    file_type: str
    category: Optional[str] = None
    document_type: Optional[str] = None
    confidence_score: float
    status: str
    extracted_json: Optional[Any] = None
    summary: Optional[str] = None
    is_locked: bool
    created_at: datetime
    tags: List[DocumentTagResponse] = []

    class Config:
        from_attributes = True

    @field_validator('extracted_json', mode='before')
    @classmethod
    def parse_extracted_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            val = v.strip()
            if val.startswith("gAAAAA"):
                from app.services.encryption_service import EncryptionService
                try:
                    val = EncryptionService.decrypt(val)
                except Exception:
                    pass
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {}
        return v

class DocumentBriefResponse(BaseModel):
    id: str
    name: str
    file_type: str
    category: Optional[str] = None
    document_type: Optional[str] = None
    confidence_score: float
    status: str
    summary: Optional[str] = None
    is_locked: bool
    created_at: datetime
    tags: List[DocumentTagResponse] = []

    class Config:
        from_attributes = True
