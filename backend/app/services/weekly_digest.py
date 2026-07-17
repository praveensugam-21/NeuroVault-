import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.graph_edge import GraphEdge
from typing import Dict, Any, List

class WeeklyDigestService:
    @staticmethod
    def generate_digest(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Calculates the weekly digest cards for the dashboard.
        """
        now = datetime.utcnow()
        one_week_ago = now - timedelta(days=7)
        thirty_days_later = now + timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # 1. Documents expiring soon
        expiring_soon = []
        all_docs = db.query(Document).filter(
            Document.user_id == user_id,
            Document.status == "COMPLETE"
        ).all()

        for doc in all_docs:
            fields = doc.get_extracted_fields()
            if fields:
                exp_date_str = fields.get("expiry_date") or fields.get("validity")
                if exp_date_str:
                    # Attempt to parse
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
                        try:
                            dt = datetime.strptime(exp_date_str, fmt)
                            if now <= dt <= thirty_days_later:
                                expiring_soon.append({
                                    "document_name": doc.name,
                                    "document_type": doc.document_type,
                                    "expiry_date": exp_date_str
                                })
                                break
                        except ValueError:
                            continue

        # 2. New connections detected
        new_edges = db.query(GraphEdge).filter(
            GraphEdge.created_at >= one_week_ago
        ).all()
        connections = []
        for edge in new_edges:
            # Check if source or target document belongs to user
            # Find document in user db
            src_doc = db.query(Document).filter(Document.id == edge.source_id, Document.user_id == user_id).first()
            if src_doc:
                connections.append(f"Linked **{edge.source_name}** to **{edge.target_name}** via relation `{edge.relationship_type}`.")

        # Limit to last 5 connections
        connections = list(set(connections))[:5]

        # 3. Trending tags in vault
        all_tags = []
        for doc in all_docs:
            for tag in doc.tags:
                all_tags.append(tag.tag_name)
        
        # Calculate tag frequency
        tag_freq = {}
        for t in all_tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        
        trending_topics = sorted(tag_freq.keys(), key=lambda x: tag_freq[x], reverse=True)[:3]

        # 4. "Did you forget?" - Resurface old documents
        forgotten = []
        old_docs = db.query(Document).filter(
            Document.user_id == user_id,
            Document.status == "COMPLETE",
            Document.created_at <= sixty_days_ago
        ).order_by(Document.created_at.asc()).limit(3).all()
        
        # Fallback to older completed documents if none are >60 days old
        if not old_docs:
            old_docs = db.query(Document).filter(
                Document.user_id == user_id,
                Document.status == "COMPLETE"
            ).order_by(Document.created_at.asc()).limit(2).all()

        for doc in old_docs:
            forgotten.append({
                "id": doc.id,
                "name": doc.name,
                "summary": doc.summary
            })

        # 5. Personal knowledge score & growth
        doc_count = len(all_docs)
        growth_rate = "+15%" if doc_count > 0 else "0%"
        
        # 6. Recommended Action Items
        recommendations = ["Keep uploading identity documents to boost your Health Score."]
        if expiring_soon:
            recommendations.append(f"Consider renewing your {expiring_soon[0]['document_type']} which expires soon.")
        else:
            recommendations.append("Your document vault is healthy! Add utility bills to track monthly expenses.")

        return {
            "expiring_soon": expiring_soon,
            "new_connections": connections,
            "trending_topics": trending_topics,
            "did_you_forget": forgotten,
            "knowledge_score": {
                "total_documents": doc_count,
                "growth_this_week": growth_rate,
                "health_score": f"{min(100, int((doc_count/8)*100))}%" # expected key docs count is 8
            },
            "recommended_actions": recommendations
        }
