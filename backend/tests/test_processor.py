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

def test_all_fallback_schemas():
    # Aadhaar Card
    aadhaar_ocr = "Aadhaar Card Name: Praveen Kumar DOB: 15/08/1995 Aadhaar: 1234 5678 9012"
    res = DocumentProcessor.process_document("aadhaar.png", "image", aadhaar_ocr)
    assert res["extracted_fields"]["dob"] == "1995-08-15"
    assert "aadhaar_number" in res["extracted_fields"]
    assert "address" in res["extracted_fields"]

    # PAN Card
    pan_ocr = "PAN Card Name: Praveen Kumar Father: Ramesh Kumar DOB: 15/08/1995 PAN: ABCDE1234F"
    res = DocumentProcessor.process_document("pan.png", "image", pan_ocr)
    assert res["extracted_fields"]["dob"] == "1995-08-15"
    assert "pan_number" in res["extracted_fields"]

    # Driving Licence
    dl_ocr = "Driving Licence Name: Praveen Kumar DOB: 15/08/1995 Expiry: 14/08/2035 DL: KA0320150089473"
    res = DocumentProcessor.process_document("dl.png", "image", dl_ocr)
    assert res["extracted_fields"]["dob"] == "1995-08-15"
    assert res["extracted_fields"]["expiry_date"] == "2035-08-14"

    # Class 10 Marksheet
    marksheet_ocr = "CBSE Marksheet Name: Praveen Kumar Roll No: 4810294 Year: 2011 Percentage: 88%"
    res = DocumentProcessor.process_document("marksheet.png", "image", marksheet_ocr)
    assert res["extracted_fields"]["student_name"] == "Praveen Kumar"
    assert res["extracted_fields"]["school_name"] == "Kendriya Vidyalaya ASC Centre"
    assert res["extracted_fields"]["board"] == "CBSE Board"
    assert res["extracted_fields"]["year"] == 2011

    # Resume
    resume_ocr = "Resume of Praveen Kumar"
    res = DocumentProcessor.process_document("resume.pdf", "pdf", resume_ocr)
    assert res["extracted_fields"]["name"] == "Praveen Kumar"
    assert res["extracted_fields"]["experience"][0]["company_name"] == "Tech Solutions Inc"

    # Offer Letter
    offer_ocr = "Offer Letter joining date: 01/07/2020 CTC: 12,000,000"
    res = DocumentProcessor.process_document("offer.pdf", "pdf", offer_ocr)
    assert res["extracted_fields"]["joining_date"] == "2020-07-01"
    assert res["extracted_fields"]["role"] == "Senior Software Engineer"

    # Bank Statement
    bank_ocr = "Bank Statement account 910248239014 balance 45250.75"
    res = DocumentProcessor.process_document("bank.pdf", "pdf", bank_ocr)
    assert res["category"] == "Financial Documents"
    assert res["document_type"] == "Bank Statement"
    assert res["extracted_fields"]["account_number"] == "910248239014"
    assert res["extracted_fields"]["balance"] == 45250.75

    # Vehicle RC
    rc_ocr = "Vehicle RC Owner Name: Praveen Kumar Expiry: 12/06/2035"
    res = DocumentProcessor.process_document("rc.png", "image", rc_ocr)
    assert res["extracted_fields"]["expiry_date"] == "2035-06-12"
    assert res["extracted_fields"]["registration_date"] == "2020-06-13"

    # Unrelated / Unclassified Document
    unrelated_ocr = "Here is a recipe for chocolate chip cookies. You will need 2 cups of flour, 1 cup of sugar, and chocolate chips. Bake at 350 degrees."
    res = DocumentProcessor.process_document("recipe.txt", "text", unrelated_ocr)
    assert res["category"] == "Unclassified (Review Needed)"
    assert res["document_type"] == "Unclassified"
    assert res["confidence_score"] == 0.40
    assert "ocr_snippet" in res["extracted_fields"]
    assert "recipe" in res["extracted_fields"]["ocr_snippet"]


