from pydantic import BaseModel
from typing import List

class GraphNode(BaseModel):
    id: str
    label: str
    type: str # "document" or "entity"
    category: str # "Identity", "Academic", "Professional", "EntityName", etc.

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str # e.g. ISSUED_TO, STUDIED_AT

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
