import pytest
from app.services.document_processor import DocumentProcessor
from app.services.rag_pipeline import RAGPipeline
from app.database import SessionLocal

def test_aadhaar_classification_and_extraction():
    ocr_sample = "GOVERNMENT OF INDIA UNIQUE IDENTIFICATION AUTHORITY OF INDIA Aadhaar Card Name: Praveen Kumar DOB: 15/08/1995 Gender: Male Aadhaar: 9876 5432 1098 Address: Bangalore, Karnataka"
    res = DocumentProcessor.process_document("aadhaar.png", "image", ocr_sample)
    
    assert res["category"] == "Identity Documents"
    assert res["document_type"] == "Aadhaar Card"
    assert res["confidence_score"] >= 0.85
    assert res["extracted_fields"]["name"] == "Praveen Kumar"
    assert res["extracted_fields"]["aadhaar_number"] == "987654321098"
    assert "UIDAI" in res["entities"]["ORG"]

def test_pan_classification_and_extraction():
    ocr_sample = "INCOME TAX DEPARTMENT Permanent Account Number Card Name: Praveen Kumar Father: Ramesh Kumar DOB: 15/08/1995 PAN: ABCDE1234F"
    res = DocumentProcessor.process_document("pan_card.jpg", "image", ocr_sample)
    
    assert res["category"] == "Identity Documents"
    assert res["document_type"] == "PAN Card"
    assert res["extracted_fields"]["pan_number"] == "ABCDE1234F"
    assert "Income Tax Department" in res["entities"]["ORG"]

def test_marksheet_extraction():
    ocr_sample = "CBSE Board Roll No: 4810294 Class 10 Marksheet Name: Praveen Kumar Year: 2011 Percentage: 88%"
    res = DocumentProcessor.process_document("marksheet_10.pdf", "pdf", ocr_sample)
    
    assert res["category"] == "Academic Records"
    assert res["document_type"] == "Class 10 Marksheet"
    assert res["extracted_fields"]["percentage"] == 88.0
    assert res["extracted_fields"]["roll_number"] == "4810294"

def test_local_rag_fallback_queries():
    # We test that our local RAG helper resolves queries with citations correctly.
    # We simulate a DB session mock to pass into it.
    from unittest.mock import MagicMock
    from app.models.document import Document
    
    mock_db = MagicMock()
    
    # Mock Document
    doc = Document(
        id="doc-pan-uuid",
        name="My PAN Card",
        file_path="uploads/pan.png",
        file_type="image",
        category="Identity Documents",
        document_type="PAN Card",
        summary="PAN Card of Praveen Kumar",
        extracted_json='{"pan_number": "ABCDE1234F", "name": "Praveen Kumar"}',
        is_locked=False
    )
    
    mock_db.query().filter().first.return_value = doc
    
    citations = [{
        "document_id": "doc-pan-uuid",
        "document_name": "My PAN Card",
        "category": "Identity Documents",
        "snippet": "PAN Card of Praveen Kumar"
    }]
    
    res = RAGPipeline._answer_with_local_rules("What is my PAN number?", citations, mock_db)
    
    assert "ABCDE1234F" in res["answer"]
    assert "My PAN Card" in res["answer"]
    assert res["citations"][0]["document_id"] == "doc-pan-uuid"
