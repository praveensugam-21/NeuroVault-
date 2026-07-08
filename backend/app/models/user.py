from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(512), nullable=False)           # Argon2id hash
    pin_hash = Column(String(512), nullable=True)                   # Secondary PIN lock hash
    refresh_token_hash = Column(String(512), nullable=True)         # Hashed refresh token (one active per user)
    is_admin = Column(Boolean, default=False, nullable=False)       # First registered user becomes admin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships — cascade deletion ensures all user data is purged on account deletion
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
