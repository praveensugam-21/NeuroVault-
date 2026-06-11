from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=False) # ID of source document or entity value
    target_id = Column(String, nullable=False) # ID of target document or entity value
    source_name = Column(String, nullable=False) # Label of source (e.g. Doc Name)
    target_name = Column(String, nullable=False) # Label of target (e.g. Entity Name)
    source_type = Column(String, nullable=False) # "document" or "entity"
    target_type = Column(String, nullable=False) # "document" or "entity"
    relationship_type = Column(String, nullable=False) # ISSUED_TO, STUDIED_AT, EMPLOYED_AT, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
