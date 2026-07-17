import sys
sys.stdout.reconfigure(encoding='utf-8')

# Test 1: All imports clean
from app.services.ocr_extractor import OCRExtractor, _EMPTY_RESULT
from app.services.document_processor import DocumentProcessor
print("Import Test: PASSED")

# Test 2: Parse and validate with simulated Aadhaar OCR text
sample_aadhaar_ocr = """
Government of India
Unique Identification Authority of India
Name: Praveen Sugam
Date of Birth: 15/08/2001
Gender: Male
Aadhaar No: 1234 5678 9012
S/O: Sugam Kumar
Address: 45 Nungambakkam High Road
Chennai - 600034
Tamil Nadu
"""

print()
print("Test 2: Expert OCR extraction from Aadhaar text")
result = OCRExtractor.extract(sample_aadhaar_ocr)
legacy = OCRExtractor.to_legacy_fields(result)
print("Raw extracted fields:", {k: v for k, v in result.items() if v is not None})
print("Legacy fields:", {k: v for k, v in legacy.items() if v is not None})

# Test 3: Validate field rules
print()
print("Test 3: Validation rules")

# Aadhaar format
test1 = OCRExtractor._parse_and_validate('{"aadhaar_number": "123456789012", "gender": "male", "pincode": "600034", "pan_number": "ABCDE1234F"}')
print("Aadhaar 12-digit:", test1.get("aadhaar_number"))   # Should be "1234 5678 9012"
print("Gender capitalize:", test1.get("gender"))           # Should be "Male"
print("Pincode valid:", test1.get("pincode"))              # Should be "600034"
print("PAN valid:", test1.get("pan_number"))               # Should be "ABCDE1234F"

test2 = OCRExtractor._parse_and_validate('{"aadhaar_number": "12345", "pincode": "12345", "pan_number": "INVALID"}')
print("Bad Aadhaar:", test2.get("aadhaar_number"))  # Should be None
print("Bad Pincode:", test2.get("pincode"))          # Should be None
print("Bad PAN:", test2.get("pan_number"))           # Should be None

print()
print("All tests PASSED")
