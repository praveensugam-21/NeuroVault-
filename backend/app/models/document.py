from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(16), nullable=False)      # pdf, image, audio, text
    category = Column(String(128), nullable=True)       # e.g. Financial Documents
    document_type = Column(String(128), nullable=True)  # e.g. Bank Statement
    confidence_score = Column(Float, default=0.0)
    status = Column(String(16), default="PROCESSING")   # PROCESSING, COMPLETE, FAILED

    # AES-256 encrypted JSON payload — stored as ciphertext
    extracted_json = Column(Text, nullable=True)

    summary = Column(Text, nullable=True)               # 3-5 line natural language summary card
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="document", cascade="all, delete-orphan")

    def get_extracted_fields(self) -> dict:
        """
        Helper method to safely decrypt and parse the extracted_json payload.
        Handles both plaintext JSON and encrypted Fernet base64 strings gracefully.
        """
        from app.services.encryption_service import EncryptionService
        import json
        
        if not self.extracted_json:
            return {}
            
        val = self.extracted_json.strip()
        
        # Detect if the value is encrypted (Fernet tokens start with gAAAAA)
        if val.startswith("gAAAAA"):
            try:
                val = EncryptionService.decrypt(val)
            except Exception:
                pass
                
        try:
            return json.loads(val) if val else {}
        except Exception:
            # Fallback if the database was somehow storing double-encoded JSON or direct plaintext
            try:
                return json.loads(self.extracted_json)
            except Exception:
                return {}


    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_documents_user_id", "user_id"),
        Index("ix_documents_user_status", "user_id", "status"),
        Index("ix_documents_user_category", "user_id", "category"),
    )


class DocumentTag(Base):
    __tablename__ = "document_tags"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String(128), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="tags")
