import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.services.security import SecurityService
from typing import Dict, Any, List

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Analytics"])

@router.get("/stats")
def get_dashboard_stats(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes dashboard summary statistics:
    - Counts by category
    - Overall completed files count
    - Recent uploads list
    - Document Health Score (expected key documents uploaded)
    """
    documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.status == "COMPLETE"
    ).all()
    
    total_completed = len(documents)

    # 1. Categories counts
    category_counts = {}
    for doc in documents:
        cat = doc.category or "Unclassified"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # 2. Recent uploads
    recent_db = db.query(Document).filter(
        Document.user_id == current_user.id
    ).order_by(Document.created_at.desc()).limit(5).all()

    recent_uploads = []
    for r in recent_db:
        recent_uploads.append({
            "id": r.id,
            "name": r.name,
            "file_type": r.file_type,
            "category": r.category,
            "status": r.status,
            "created_at": r.created_at
        })

    # 3. Document Health Score
    # We define 8 key documents that every Indian user should ideally store:
    # Aadhaar, PAN, DL, Class 10 mark sheet, Class 12 mark sheet, Resume, Bank Statement, Vehicle RC.
    key_doc_types = [
        "Aadhaar Card", "PAN Card", "Driving Licence", 
        "Class 10 Marksheet", "Class 12 Marksheet", 
        "Resume", "Bank Statement", "Vehicle RC"
    ]
    
    uploaded_keys = set()
    for doc in documents:
        if doc.document_type in key_doc_types:
            uploaded_keys.add(doc.document_type)

    health_score = int((len(uploaded_keys) / len(key_doc_types)) * 100) if key_doc_types else 0

    return {
        "total_documents": total_completed,
        "category_counts": category_counts,
        "recent_uploads": recent_uploads,
        "health_score": health_score,
        "missing_key_documents": [k for k in key_doc_types if k not in uploaded_keys]
    }

@router.get("/timelines")
def get_timelines(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Builds the Academic and Career visual timelines.
    - Academic timeline: mark sheets and certificates sorted by year.
    - Career timeline: offer letters, pay slips, and work items sorted chronologically.
    """
    documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.status == "COMPLETE"
    ).all()

    academic_timeline = []
    career_timeline = []

    for doc in documents:
        fields = doc.get_extracted_fields()

        # Parse Academic
        if doc.category == "Academic Records":
            year = fields.get("year") or doc.created_at.year
            academic_timeline.append({
                "id": doc.id,
                "name": doc.name,
                "document_type": doc.document_type,
                "year": year,
                "detail": f"Completed at {fields.get('school_name', 'Institution')} with {fields.get('percentage', fields.get('gpa_cgpa', 'N/A'))}%"
            })

        # Parse Professional
        elif doc.category == "Professional Documents":
            # Sort by joining date or created_at
            joining = fields.get("joining_date") or doc.created_at.strftime("%d/%m/%Y")
            career_timeline.append({
                "id": doc.id,
                "name": doc.name,
                "document_type": doc.document_type,
                "date": joining,
                "company": fields.get("company_name", fields.get("company", "Organization")),
                "designation": fields.get("role", fields.get("designation", "Employment")),
                "ctc": fields.get("ctc")
            })

    # Sort academic by year ascending
    academic_sorted = sorted(academic_timeline, key=lambda x: str(x["year"]))

    # Sort career timeline (rough chronological fallback)
    # Parse DD/MM/YYYY dates if possible
    def parse_timeline_date(item):
        date_str = item["date"]
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return datetime.min

    career_sorted = sorted(career_timeline, key=parse_timeline_date)

    return {
        "academic": academic_sorted,
        "career": career_sorted
    }

@router.get("/expiry-alerts")
def get_expiry_alerts(
    current_user: User = Depends(SecurityService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns lists of documents with upcoming expirations.
    """
    documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.status == "COMPLETE"
    ).all()

    alerts = []
    for doc in documents:
        fields = doc.get_extracted_fields()
        if fields:
            expiry_str = fields.get("expiry_date") or fields.get("validity")
            if expiry_str:
                # Check if date is upcoming
                # Calculate days remaining
                days_left = None
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(expiry_str, fmt)
                        delta = dt - datetime.utcnow()
                        days_left = delta.days
                        break
                    except ValueError:
                        continue
                
                if days_left is not None:
                    alerts.append({
                        "document_id": doc.id,
                        "name": doc.name,
                        "document_type": doc.document_type,
                        "expiry_date": expiry_str,
                        "days_remaining": days_left,
                        "priority": "high" if days_left < 30 else "medium" if days_left < 90 else "low"
                    })

    # Sort by days remaining ascending
    alerts_sorted = sorted(alerts, key=lambda x: x["days_remaining"])
    return alerts_sorted
