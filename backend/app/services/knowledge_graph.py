import json
import logging
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.entity import Entity
from app.models.graph_edge import GraphEdge
from typing import Dict, Any, List

logger = logging.getLogger("neurovault.graph")

class KnowledgeGraphService:
    @staticmethod
    def link_document_entities(db: Session, document: Document, entities_dict: Dict[str, List[str]]):
        """
        Scans all entities of a document and links them to:
        1. Entity value nodes (e.g. name of person, name of organization)
        2. Other documents belonging to the same user with overlapping entities.
        """
        user_id = document.user_id
        doc_id = document.id
        doc_name = document.name
        doc_type = document.document_type or "Document"
        category = document.category or "General"

        # First, save entities to the Entity table in the DB
        for ent_type, values in entities_dict.items():
            for val in values:
                if not val:
                    continue
                # Save entity mapping
                db_entity = Entity(
                    document_id=doc_id,
                    entity_type=ent_type,
                    entity_value=val
                )
                db.add(db_entity)
        db.commit()

        # Let's create primary direct document-to-entity links
        # E.g. Passport -> ISSUED_TO -> John Doe (PERSON)
        # E.g. Marksheet -> ISSUED_BY -> CBSE (ORG)
        # E.g. Offer Letter -> EMPLOYED_AT -> Tech Solutions (ORG)
        for ent_type, values in entities_dict.items():
            for val in values:
                if not val:
                    continue
                rel_type = "RELATED_TO"
                if ent_type == "PERSON":
                    rel_type = "ISSUED_TO"
                elif ent_type == "ORG":
                    if category == "Academic Records":
                        rel_type = "STUDIED_AT" if "school" in val.lower() or "college" in val.lower() or "university" in val.lower() else "ISSUED_BY"
                    elif category == "Professional Documents":
                        rel_type = "EMPLOYED_AT"
                    else:
                        rel_type = "ISSUED_BY"
                
                # Check if edge already exists to prevent duplicate entries
                exists = db.query(GraphEdge).filter(
                    GraphEdge.source_id == doc_id,
                    GraphEdge.target_id == val,
                    GraphEdge.relationship_type == rel_type
                ).first()
                
                if not exists:
                    edge = GraphEdge(
                        source_id=doc_id,
                        target_id=val, # Target is the entity string
                        source_name=doc_name,
                        target_name=val,
                        source_type="document",
                        target_type="entity",
                        relationship_type=rel_type
                    )
                    db.add(edge)

        # Check for overlaps with OTHER documents of the same user
        other_docs = db.query(Document).filter(
            Document.user_id == user_id,
            Document.id != doc_id,
            Document.status == "COMPLETE"
        ).all()

        for other in other_docs:
            other_id = other.id
            other_name = other.name
            other_type = other.document_type or "Document"
            other_fields = {}
            if other.extracted_json:
                try:
                    other_fields = json.loads(other.extracted_json)
                except Exception:
                    pass

            this_fields = {}
            if document.extracted_json:
                try:
                    this_fields = json.loads(document.extracted_json)
                except Exception:
                    pass

            # A. PRECEDES and FOLLOWS timeline logic for school mark sheets
            if category == "Academic Records" and other.category == "Academic Records":
                this_year = this_fields.get("year")
                other_year = other_fields.get("year")
                if isinstance(this_year, int) and isinstance(other_year, int):
                    if this_year > other_year:
                        # Other precedes this
                        KnowledgeGraphService._create_double_edge(
                            db, other_id, other_name, doc_id, doc_name, "PRECEDES", "FOLLOWS"
                        )
                    elif this_year < other_year:
                        # This precedes other
                        KnowledgeGraphService._create_double_edge(
                            db, doc_id, doc_name, other_id, other_name, "PRECEDES", "FOLLOWS"
                        )

            # B. CONTRADICTS check (e.g. mismatching Date of Births)
            this_name = this_fields.get("name") or this_fields.get("student_name") or this_fields.get("patient_name") or this_fields.get("owner_name")
            other_name_val = other_fields.get("name") or other_fields.get("student_name") or other_fields.get("patient_name") or other_fields.get("owner_name")
            
            if this_name and other_name_val and this_name.strip().lower() == other_name_val.strip().lower():
                this_dob = this_fields.get("dob")
                other_dob = other_fields.get("dob")
                if this_dob and other_dob and this_dob != other_dob:
                    # Mismatching date of births for same person!
                    KnowledgeGraphService._create_double_edge(
                        db, doc_id, doc_name, other_id, other_name, "CONTRADICTS", "CONTRADICTS"
                    )

            # C. Overlapping named entities (e.g. same Organization, same Person name)
            other_entities = db.query(Entity).filter(Entity.document_id == other_id).all()
            for ent in other_entities:
                for this_ent_type, this_ent_vals in entities_dict.items():
                    for val in this_ent_vals:
                        if val and ent.entity_value.lower() == val.lower() and ent.entity_type == this_ent_type:
                            # Both documents reference the same entity
                            # Link them via a RELATED_TO connection
                            KnowledgeGraphService._create_double_edge(
                                db, doc_id, doc_name, other_id, other_name, "RELATED_TO", "RELATED_TO"
                            )

        db.commit()

    @staticmethod
    def _create_double_edge(db: Session, id1: str, name1: str, id2: str, name2: str, rel1_to_2: str, rel2_to_1: str):
        """
        Helper to draw graph edges in both directions if not already present.
        """
        # Edge 1 to 2
        e1 = db.query(GraphEdge).filter(
            GraphEdge.source_id == id1,
            GraphEdge.target_id == id2,
            GraphEdge.relationship_type == rel1_to_2
        ).first()
        if not e1:
            edge = GraphEdge(
                source_id=id1,
                target_id=id2,
                source_name=name1,
                target_name=name2,
                source_type="document",
                target_type="document",
                relationship_type=rel1_to_2
            )
            db.add(edge)

        # Edge 2 to 1 (if different)
        if rel1_to_2 != rel2_to_1 or id1 != id2:
            e2 = db.query(GraphEdge).filter(
                GraphEdge.source_id == id2,
                GraphEdge.target_id == id1,
                GraphEdge.relationship_type == rel2_to_1
            ).first()
            if not e2:
                edge = GraphEdge(
                    source_id=id2,
                    target_id=id1,
                    source_name=name2,
                    target_name=name1,
                    source_type="document",
                    target_type="document",
                    relationship_type=rel2_to_1
                )
                db.add(edge)

    @staticmethod
    def get_user_graph(db: Session, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generates the nodes and edges representations matching Pydantic schemas.
        """
        # Get all completed documents of the user
        documents = db.query(Document).filter(
            Document.user_id == user_id,
            Document.status == "COMPLETE"
        ).all()
        
        doc_ids = [doc.id for doc in documents]
        
        # Collect edges where source is one of the user's documents
        edges_db = db.query(GraphEdge).filter(
            GraphEdge.source_id.in_(doc_ids)
        ).all()

        nodes = []
        edges = []
        node_ids_added = set()

        # Add document nodes
        for doc in documents:
            node_id = doc.id
            if node_id not in node_ids_added:
                # Color code category matching for UI stylesheet
                cat_tag = "General"
                if doc.category:
                    cat_tag = doc.category.split(" ")[0] # e.g. "Identity"
                
                nodes.append({
                    "id": node_id,
                    "label": doc.name,
                    "type": "document",
                    "category": cat_tag
                })
                node_ids_added.add(node_id)

        # Process edges and collect entity nodes dynamically
        for edge in edges_db:
            # Check target node
            # If target is another document, make sure it belongs to the user
            if edge.target_type == "document" and edge.target_id not in doc_ids:
                continue
                
            # If target is an entity node, add it to nodes list if not present
            if edge.target_type == "entity" and edge.target_id not in node_ids_added:
                nodes.append({
                    "id": edge.target_id,
                    "label": edge.target_name,
                    "type": "entity",
                    "category": "EntityName"
                })
                node_ids_added.add(edge.target_id)

            # Add Edge
            edges.append({
                "id": f"edge-{edge.id}",
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.relationship_type
            })

        return {
            "nodes": nodes,
            "edges": edges
        }
