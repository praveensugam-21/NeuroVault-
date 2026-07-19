from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, nullable=True)   # Linked document UUID if applicable
    action = Column(String, nullable=False)        # VIEW, LOCK, UNLOCK, DELETE, UPLOAD, LOGIN, LOGOUT
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
