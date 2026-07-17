import json
import logging
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.entity import Entity
from app.models.graph_edge import GraphEdge
from typing import Dict, Any, List

logger = logging.getLogger("iris.graph")


def _normalize_entity(value: str) -> str:
    """Normalize entity value for deduplication: lowercase, strip whitespace."""
    return value.strip().lower()


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

        # Deduplicate and filter entities before saving
        deduped_entities: Dict[str, List[str]] = {}
        for ent_type, values in entities_dict.items():
            seen_normalized = set()
            clean_vals = []
            for val in values:
                if not val or len(val.strip()) < 2:
                    continue
                norm = _normalize_entity(val)
                if norm in seen_normalized:
                    continue
                seen_normalized.add(norm)
                clean_vals.append(val.strip())
            if clean_vals:
                deduped_entities[ent_type] = clean_vals

        # Save deduplicated entities to the Entity table
        for ent_type, values in deduped_entities.items():
            for val in values:
                # Skip if this entity already exists for this document
                existing = db.query(Entity).filter(
                    Entity.document_id == doc_id,
                    Entity.entity_type == ent_type,
                    Entity.entity_value == val
                ).first()
                if not existing:
                    db_entity = Entity(
                        document_id=doc_id,
                        entity_type=ent_type,
                        entity_value=val
                    )
                    db.add(db_entity)
        db.commit()

        # Create document-to-entity graph edges with semantic relationship types
        for ent_type, values in deduped_entities.items():
            for val in values:
                rel_type = KnowledgeGraphService._get_relationship_type(ent_type, category)

                # Use normalized value as node ID to prevent duplicate entity nodes
                entity_node_id = f"entity::{_normalize_entity(val)}"

                exists = db.query(GraphEdge).filter(
                    GraphEdge.source_id == doc_id,
                    GraphEdge.target_id == entity_node_id,
                    GraphEdge.relationship_type == rel_type
                ).first()

                if not exists:
                    edge = GraphEdge(
                        source_id=doc_id,
                        target_id=entity_node_id,
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
            other_fields = other.get_extracted_fields()
            this_fields = document.get_extracted_fields()

            # A. PRECEDES/FOLLOWS for academic mark sheets
            if category == "Academic Records" and other.category == "Academic Records":
                this_year = this_fields.get("year")
                other_year = other_fields.get("year")
                if isinstance(this_year, int) and isinstance(other_year, int):
                    if this_year > other_year:
                        KnowledgeGraphService._create_double_edge(
                            db, other_id, other.name, doc_id, doc_name, "PRECEDES", "FOLLOWS"
                        )
                    elif this_year < other_year:
                        KnowledgeGraphService._create_double_edge(
                            db, doc_id, doc_name, other_id, other.name, "PRECEDES", "FOLLOWS"
                        )

            # B. CONTRADICTS check (mismatching Date of Births)
            this_name = (
                this_fields.get("name") or this_fields.get("student_name")
                or this_fields.get("patient_name") or this_fields.get("owner_name")
            )
            other_name_val = (
                other_fields.get("name") or other_fields.get("student_name")
                or other_fields.get("patient_name") or other_fields.get("owner_name")
            )

            if (this_name and other_name_val
                    and this_name.strip().lower() == other_name_val.strip().lower()):
                this_dob = this_fields.get("dob")
                other_dob = other_fields.get("dob")
                if this_dob and other_dob and this_dob != other_dob:
                    KnowledgeGraphService._create_double_edge(
                        db, doc_id, doc_name, other_id, other.name, "CONTRADICTS", "CONTRADICTS"
                    )

            # C. Overlapping named entities → RELATED_TO
            other_entities = db.query(Entity).filter(Entity.document_id == other_id).all()
            for ent in other_entities:
                for this_ent_type, this_ent_vals in deduped_entities.items():
                    for val in this_ent_vals:
                        if (
                            val
                            and ent.entity_type == this_ent_type
                            and _normalize_entity(ent.entity_value) == _normalize_entity(val)
                        ):
                            KnowledgeGraphService._create_double_edge(
                                db, doc_id, doc_name, other_id, other.name, "RELATED_TO", "RELATED_TO"
                            )

        db.commit()

    @staticmethod
    def _get_relationship_type(entity_type: str, category: str) -> str:
        """Return a semantic relationship label based on entity type and document category."""
        if entity_type == "PERSON":
            if category == "Medical Records":
                return "PATIENT_IS"
            elif category in ("Financial Documents", "Property & Legal"):
                return "ACCOUNT_HOLDER"
            return "BELONGS_TO"
        elif entity_type == "ORG":
            if category == "Academic Records":
                return "STUDIED_AT"
            elif category == "Professional Documents":
                return "EMPLOYED_AT"
            return "ISSUED_BY"
        elif entity_type == "GPE":
            return "LOCATED_IN"
        elif entity_type == "DATE":
            return "DATED"
        elif entity_type == "ID_NUMBER":
            return "IDENTIFIED_BY"
        return "RELATED_TO"

    @staticmethod
    def _create_double_edge(
        db: Session,
        id1: str, name1: str,
        id2: str, name2: str,
        rel1_to_2: str, rel2_to_1: str
    ):
        """Helper to draw graph edges in both directions if not already present."""
        e1 = db.query(GraphEdge).filter(
            GraphEdge.source_id == id1,
            GraphEdge.target_id == id2,
            GraphEdge.relationship_type == rel1_to_2
        ).first()
        if not e1:
            db.add(GraphEdge(
                source_id=id1,
                target_id=id2,
                source_name=name1,
                target_name=name2,
                source_type="document",
                target_type="document",
                relationship_type=rel1_to_2
            ))

        if rel1_to_2 != rel2_to_1 or id1 != id2:
            e2 = db.query(GraphEdge).filter(
                GraphEdge.source_id == id2,
                GraphEdge.target_id == id1,
                GraphEdge.relationship_type == rel2_to_1
            ).first()
            if not e2:
                db.add(GraphEdge(
                    source_id=id2,
                    target_id=id1,
                    source_name=name2,
                    target_name=name1,
                    source_type="document",
                    target_type="document",
                    relationship_type=rel2_to_1
                ))

    @staticmethod
    def get_user_graph(db: Session, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Generates the nodes and edges for the knowledge graph visualization."""
        documents = db.query(Document).filter(
            Document.user_id == user_id,
            Document.status == "COMPLETE"
        ).all()

        doc_ids = [doc.id for doc in documents]

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
                cat_tag = "General"
                if doc.category:
                    cat_tag = doc.category.split(" ")[0]
                nodes.append({
                    "id": node_id,
                    "label": doc.name,
                    "type": "document",
                    "category": cat_tag,
                    "document_type": doc.document_type or "Unknown"
                })
                node_ids_added.add(node_id)

        # Process edges and collect entity nodes
        for edge in edges_db:
            if edge.target_type == "document" and edge.target_id not in doc_ids:
                continue

            if edge.target_type == "entity" and edge.target_id not in node_ids_added:
                # Derive entity type from target_id prefix (entity::value)
                nodes.append({
                    "id": edge.target_id,
                    "label": edge.target_name,
                    "type": "entity",
                    "category": "Entity"
                })
                node_ids_added.add(edge.target_id)

            edges.append({
                "id": f"edge-{edge.id}",
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.relationship_type
            })

        return {"nodes": nodes, "edges": edges}
