from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String, nullable=False) # PERSON, ORG, DATE, ID_NUMBER, GPE
    entity_value = Column(String, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="entities")
