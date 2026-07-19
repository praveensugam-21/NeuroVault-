from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def _utcnow():
    """Returns current UTC time as a naive datetime (for DB compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(512), nullable=True)            # Argon2id hash (nullable for OAuth users)
    pin_hash = Column(String(512), nullable=True)                   # Secondary PIN lock hash
    refresh_token_hash = Column(String(512), nullable=True)         # Hashed refresh token (one active per user)
    oauth_provider = Column(String(50), default="local", nullable=False)  # 'local' or 'google'
    oauth_id = Column(String(255), unique=True, index=True, nullable=True)  # Provider's unique user ID
    is_admin = Column(Boolean, default=False, nullable=False)       # First registered user becomes admin
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships — cascade deletion ensures all user data is purged on account deletion
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
