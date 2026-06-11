from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False) # PDF, IMAGE, AUDIO, TEXT, URL
    category = Column(String, nullable=True) # e.g. Identity Documents, Academic Records
    document_type = Column(String, nullable=True) # e.g. Aadhaar Card, PAN Card
    confidence_score = Column(Float, default=0.0)
    status = Column(String, default="PROCESSING") # PROCESSING, COMPLETE, FAILED
    extracted_json = Column(Text, nullable=True) # Stringified JSON payload
    summary = Column(Text, nullable=True) # 3-5 line natural language card
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="document", cascade="all, delete-orphan")

class DocumentTag(Base):
    __tablename__ = "document_tags"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="tags")
