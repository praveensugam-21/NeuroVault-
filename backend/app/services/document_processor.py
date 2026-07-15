import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from app.config import settings

logger = logging.getLogger("iris.processor")

_spacy_nlp = None


def get_spacy_nlp():
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            try:
                _spacy_nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.info("spaCy model not found. Downloading...")
                os.system("python -m spacy download en_core_web_sm")
                _spacy_nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.error(f"Failed to load spaCy: {e}")
            _spacy_nlp = None
    return _spacy_nlp


# ── Classification Thresholds ─────────────────────────────────────────────────
MIN_CONFIDENCE_THRESHOLD = 0.55  # Minimum score to classify as a known type


# Identity document types that benefit from the expert OCR extractor
_IDENTITY_DOC_TYPES = {
    "Aadhaar Card", "PAN Card", "Driving Licence", "Passport", "Voter ID"
}


class DocumentProcessor:

    @staticmethod
    def process_document(
        file_path: str,
        file_type: str,
        ocr_text: str,
        original_name: str = None
    ) -> Dict[str, Any]:
        """
        Main entry point: classifies the document and extracts fields.

        Pipeline:
          1. Classify document type using rule-based confidence scoring.
          2. For identity documents: run the expert OCRExtractor prompt
             (Ollama -> Gemini -> empty fallback) to extract precise PII fields.
          3. Merge expert-extracted fields over regex-extracted fields.
          4. For non-identity documents: use the full regex extraction pipeline.
        """
        filename = (original_name or os.path.basename(file_path)).lower()
        return DocumentProcessor._process_with_rules(filename, ocr_text)

    # ── Ollama Integration (preserved, disabled) ─────────────────────────────

    @staticmethod
    def _process_with_ollama(ocr_text: str) -> Dict[str, Any]:
        from app.services.ollama_service import OllamaService

        prompt = f"""
You are the IRIS document metadata extraction engine.
Analyze this document OCR text and return a JSON object.

=== CRITICAL RULE ===
If the document does NOT clearly match one of the known types, set:
  "document_type": "Unknown Document"
  "category": "Unclassified"
  "confidence_score": a value below 0.45
DO NOT guess. Use "Unknown Document" whenever unsure.
====================

Output valid JSON ONLY (no markdown wrappers).

Schema:
1. "category": One of: "Identity Documents", "Academic Records", "Professional Documents",
   "Financial Documents", "Medical Records", "Property & Legal", "Vehicle Documents", "Unclassified"
2. "document_type": One of the known sub-types or "Unknown Document"
3. "confidence_score": Float 0.0-1.0
4. "extracted_fields": Dict of fields actually found in the document (never invent values)
5. "summary_card": 2-3 sentence summary
6. "auto_tags": List of hashtags
7. "action_items": {{"expiry_date": null or ISO date, "tasks": []}}
8. "entities": {{"PERSON": [], "ORG": [], "DATE": [], "ID_NUMBER": [], "GPE": []}}
9. "anomalies": List of quality alerts

Document OCR Text:
{ocr_text}
"""
        response_text = OllamaService.generate_completion(prompt, format_json=True)
        if not response_text:
            raise RuntimeError("Ollama returned empty response.")

        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)

        return json.loads(response_text)

    @staticmethod
    def _validate_ollama_result(
        result: Dict[str, Any],
        ocr_text: str,
        filename: str
    ) -> Dict[str, Any]:
        """Cross-validate Ollama's classification against document signals."""
        doc_type = result.get("document_type", "Unknown Document")
        combined = f"{filename} {ocr_text.lower()}"
        upper_text = ocr_text.upper()

        evidence_rules = {
            "PAN Card": lambda: (
                any(kw in combined for kw in ["permanent account number", "income tax department", "pan card"])
                or (bool(re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", upper_text)) and "pan" in combined)
            ),
            "Aadhaar Card": lambda: (
                any(kw in combined for kw in ["aadhaar", "aadhar", "uidai", "unique identification"])
                or bool(re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", ocr_text))
            ),
            "Driving Licence": lambda: (
                any(kw in combined for kw in ["driving licence", "driving license", "dl number", " rto "])
            ),
            "Bank Statement": lambda: (
                any(kw in combined for kw in ["account statement", "bank statement", "ifsc", "opening balance"])
            ),
            "Electricity Bill": lambda: (
                any(kw in combined for kw in ["electricity", "units consumed", "kwh", "bescom", "tneb"])
            ),
            "Vehicle RC": lambda: (
                any(kw in combined for kw in ["registration certificate", "vehicle registration", "chassis number"])
            ),
        }

        if doc_type in evidence_rules and not evidence_rules[doc_type]():
            logger.warning(f"Ollama classified as '{doc_type}' but evidence not found. Overriding to Unknown.")
            result["document_type"] = "Unknown Document"
            result["category"] = "Unclassified"
            result["confidence_score"] = 0.30
            result["extracted_fields"] = {"ocr_snippet": ocr_text[:400]}
            result["summary_card"] = "Document could not be classified with sufficient confidence."
            result["auto_tags"] = ["#unclassified", "#review-required"]
            result["anomalies"] = [f"Classification overridden: '{doc_type}' had no supporting evidence."]

        return result

    # ── Rule-Based Pipeline ───────────────────────────────────────────────────

    @staticmethod
    def _process_with_rules(filename: str, ocr_text: str) -> Dict[str, Any]:
        """
        Confidence-scored multi-signal document classifier.
        Each document type accumulates a score from multiple independent signals.
        Only classifies when score >= MIN_CONFIDENCE_THRESHOLD.
        Never invents or injects fake field values.
        """
        ocr_lower = ocr_text.lower() if ocr_text else ""
        ocr_upper = ocr_text.upper() if ocr_text else ""
        combined = f"{filename} {ocr_lower}"

        # Score each candidate type
        scores: Dict[str, float] = {}

        # ── Aadhaar Card ──────────────────────────────────────────────────────
        aadhaar_score = 0.0
        if any(kw in combined for kw in ["aadhaar", "aadhar", "adhar"]):
            aadhaar_score += 0.45
        if any(kw in combined for kw in ["uidai", "unique identification authority"]):
            aadhaar_score += 0.35
        if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", ocr_text or ""):
            aadhaar_score += 0.25
        if re.search(r"\b\d{12}\b", ocr_text or "") and "aadhaar" in combined:
            aadhaar_score += 0.15
        if "enrolment" in combined or "enrollment" in combined:
            aadhaar_score += 0.10
        scores["Aadhaar Card"] = min(aadhaar_score, 1.0)

        # ── PAN Card ──────────────────────────────────────────────────────────
        pan_score = 0.0
        if "permanent account number" in combined:
            pan_score += 0.50
        if "income tax department" in combined or "income tax dept" in combined:
            pan_score += 0.30
        if "pan card" in combined:
            pan_score += 0.35
        _pan_regex = re.search(r"\b([A-Z]{5}\d{4}[A-Z])\b", ocr_upper)
        if _pan_regex and "pan" in combined:
            pan_score += 0.25
        # NEGATIVE: Never classify as PAN if it has aadhaar/bank signals
        if any(kw in combined for kw in ["aadhaar", "bank", "statement"]):
            pan_score -= 0.40
        scores["PAN Card"] = max(min(pan_score, 1.0), 0.0)

        # ── Driving Licence ───────────────────────────────────────────────────
        dl_score = 0.0
        if any(kw in combined for kw in ["driving licence", "driving license"]):
            dl_score += 0.50
        if "dl number" in combined or "dlno" in combined:
            dl_score += 0.30
        if " rto " in combined or "regional transport" in combined:
            dl_score += 0.25
        if re.search(r"\b[A-Z]{2}\d{13}\b", ocr_upper):
            dl_score += 0.20
        if any(kw in combined for kw in ["mcwg", "lmv", "vehicle class", "transport authority"]):
            dl_score += 0.15
        scores["Driving Licence"] = min(dl_score, 1.0)

        # ── Class 10 Marksheet ────────────────────────────────────────────────
        m10_score = 0.0
        if any(kw in combined for kw in ["class x", "class 10", "sslc", "secondary school leaving", "matriculation"]):
            m10_score += 0.45
        if any(kw in combined for kw in ["marksheet", "mark sheet", "marks card"]):
            m10_score += 0.30
        if any(kw in combined for kw in ["cbse", "icse", "state board", "board of secondary"]):
            m10_score += 0.20
        if re.search(r"roll\s*(no|number)?[:\s]+\d+", combined):
            m10_score += 0.10
        scores["Class 10 Marksheet"] = min(m10_score, 1.0)

        # ── Class 12 Marksheet ────────────────────────────────────────────────
        m12_score = 0.0
        if any(kw in combined for kw in ["class xii", "class 12", "higher secondary", "intermediate", "hs examination"]):
            m12_score += 0.45
        if any(kw in combined for kw in ["marksheet", "mark sheet", "marks card"]):
            m12_score += 0.30
        if any(kw in combined for kw in ["cbse", "icse", "state board", "board of secondary"]):
            m12_score += 0.20
        if re.search(r"roll\s*(no|number)?[:\s]+\d+", combined):
            m12_score += 0.10
        scores["Class 12 Marksheet"] = min(m12_score, 1.0)

        # ── Degree Certificate ────────────────────────────────────────────────
        deg_score = 0.0
        if any(kw in combined for kw in ["degree certificate", "bachelor of", "master of", "b.tech", "m.tech", "b.sc", "m.sc", "b.e.", "m.e."]):
            deg_score += 0.50
        if any(kw in combined for kw in ["university", "convocation", "chancellor", "registrar"]):
            deg_score += 0.30
        if any(kw in combined for kw in ["awarded", "conferred", "degree"]):
            deg_score += 0.20
        # NEGATIVE: A degree certificate almost never contains personal skills lists, resume summaries, or job experience.
        if any(kw in combined for kw in ["skills", "experience", "resume", "cv", "projects", "interests", "objective", "work experience"]):
            deg_score -= 0.45
        scores["Degree Certificate"] = max(min(deg_score, 1.0), 0.0)

        # ── Resume / CV ───────────────────────────────────────────────────────
        resume_score = 0.0
        if any(kw in combined for kw in ["curriculum vitae", "resume"]):
            resume_score += 0.55
        if any(kw in combined for kw in ["work experience", "professional experience", "employment history"]):
            resume_score += 0.35
        has_email = bool(re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", ocr_text or ""))
        has_phone = bool(re.search(r"\b[6-9]\d{9}\b", ocr_text or ""))
        if has_email:
            resume_score += 0.15
        if has_phone:
            resume_score += 0.15
        if any(kw in combined for kw in ["skills", "objective", "career summary", "references", "projects"]):
            resume_score += 0.15
        # NEGATIVE: A resume must contain contact info (email/phone). If not, penalize.
        if not (has_email or has_phone):
            resume_score -= 0.50
        # NEGATIVE: If it contains typical project report academic markers.
        if any(kw in combined for kw in ["project report", "table of contents", "submitted in partial", "figure", "table", "documentation", "system design", "implementation"]):
            resume_score -= 0.40
        scores["Resume"] = max(min(resume_score, 1.0), 0.0)


        # ── Offer Letter ──────────────────────────────────────────────────────
        offer_score = 0.0
        if any(kw in combined for kw in ["offer letter", "appointment letter", "letter of appointment"]):
            offer_score += 0.55
        if any(kw in combined for kw in ["cost to company", "ctc", "annual compensation"]):
            offer_score += 0.30
        if any(kw in combined for kw in ["joining date", "date of joining", "commencement date"]):
            offer_score += 0.20
        if any(kw in combined for kw in ["designation", "role", "position"]):
            offer_score += 0.10
        scores["Offer Letter"] = min(offer_score, 1.0)

        # ── Pay Slip ──────────────────────────────────────────────────────────
        pay_score = 0.0
        if any(kw in combined for kw in ["payslip", "pay slip", "salary slip", "pay stub"]):
            pay_score += 0.55
        if any(kw in combined for kw in ["basic salary", "basic pay", "gross salary", "net salary"]):
            pay_score += 0.30
        if any(kw in combined for kw in ["pf deduction", "provident fund", "esi", "tds deduction"]):
            pay_score += 0.20
        if any(kw in combined for kw in ["employee id", "emp id", "month of"]):
            pay_score += 0.10
        scores["Pay Slip"] = min(pay_score, 1.0)

        # ── Bank Statement ────────────────────────────────────────────────────
        bank_score = 0.0
        if any(kw in combined for kw in ["account statement", "bank statement", "statement of account"]):
            bank_score += 0.55
        if any(kw in combined for kw in ["opening balance", "closing balance", "available balance"]):
            bank_score += 0.30
        if any(kw in combined for kw in ["ifsc", "micr", "rtgs", "neft", "imps"]):
            bank_score += 0.20
        if re.search(r"\b\d{9,18}\b", ocr_text or "") and any(kw in combined for kw in ["account", "acct"]):
            bank_score += 0.10
        scores["Bank Statement"] = min(bank_score, 1.0)

        # ── Prescription ──────────────────────────────────────────────────────
        rx_score = 0.0
        if any(kw in combined for kw in ["prescription", "rx", "℞"]):
            rx_score += 0.50
        if any(kw in combined for kw in ["tablet", "capsule", "syrup", "dosage", "dose", "mg"]):
            rx_score += 0.25
        if re.search(r"dr\.?\s+[A-Z][a-z]+", ocr_text or "", re.IGNORECASE):
            rx_score += 0.20
        if any(kw in combined for kw in ["clinic", "hospital", "patient", "diagnosis"]):
            rx_score += 0.15
        scores["Prescription"] = min(rx_score, 1.0)

        # ── Electricity Bill ──────────────────────────────────────────────────
        elec_score = 0.0
        if any(kw in combined for kw in ["electricity bill", "electric bill", "power bill"]):
            elec_score += 0.55
        if any(kw in combined for kw in ["units consumed", "kwh", "unit consumed"]):
            elec_score += 0.35
        if any(kw in combined for kw in ["bescom", "tneb", "msedcl", "cesc", "discom", "electricity board"]):
            elec_score += 0.30
        if any(kw in combined for kw in ["consumer number", "consumer no", "meter number", "meter no"]):
            elec_score += 0.20
        scores["Electricity Bill"] = min(elec_score, 1.0)

        # ── Vehicle RC ────────────────────────────────────────────────────────
        rc_score = 0.0
        if any(kw in combined for kw in ["registration certificate", "vehicle registration cert"]):
            rc_score += 0.55
        if any(kw in combined for kw in ["chassis number", "chasis number"]):
            rc_score += 0.35
        if any(kw in combined for kw in ["engine number", "engine no"]):
            rc_score += 0.25
        if re.search(r"\b[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}\b", ocr_upper):
            rc_score += 0.15
        scores["Vehicle RC"] = min(rc_score, 1.0)

        # ── Insurance Policy ──────────────────────────────────────────────────
        ins_score = 0.0
        if any(kw in combined for kw in ["insurance policy", "policy number", "sum insured"]):
            ins_score += 0.50
        if any(kw in combined for kw in ["premium", "beneficiary", "nominee", "insured amount"]):
            ins_score += 0.30
        if any(kw in combined for kw in ["lic", "hdfc life", "icici prudential", "bajaj allianz"]):
            ins_score += 0.20
        scores["Insurance Policy"] = min(ins_score, 1.0)

        # ── Select best classification ────────────────────────────────────────
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score < MIN_CONFIDENCE_THRESHOLD:
            return DocumentProcessor._build_unknown_result(ocr_text)

        # Route to extraction builder
        return DocumentProcessor._build_classified_result(
            best_type, best_score, ocr_text, ocr_lower, ocr_upper, combined
        )

    @staticmethod
    def _build_classified_result(
        doc_type: str,
        confidence: float,
        ocr_text: str,
        ocr_lower: str,
        ocr_upper: str,
        combined: str
    ) -> Dict[str, Any]:
        """Build the full result dict for a classified document type."""
        category_map = {
            "Aadhaar Card": "Identity Documents",
            "PAN Card": "Identity Documents",
            "Driving Licence": "Identity Documents",
            "Class 10 Marksheet": "Academic Records",
            "Class 12 Marksheet": "Academic Records",
            "Degree Certificate": "Academic Records",
            "Resume": "Professional Documents",
            "Offer Letter": "Professional Documents",
            "Pay Slip": "Professional Documents",
            "Bank Statement": "Financial Documents",
            "Prescription": "Medical Records",
            "Electricity Bill": "Property & Legal",
            "Vehicle RC": "Vehicle Documents",
            "Insurance Policy": "Property & Legal",
        }

        tag_map = {
            "Aadhaar Card": ["#identity", "#aadhaar", "#uidai", "#government"],
            "PAN Card": ["#identity", "#pan", "#tax", "#government"],
            "Driving Licence": ["#identity", "#driving", "#dl", "#rto"],
            "Class 10 Marksheet": ["#academic", "#marksheet", "#class10"],
            "Class 12 Marksheet": ["#academic", "#marksheet", "#class12"],
            "Degree Certificate": ["#academic", "#degree", "#university"],
            "Resume": ["#professional", "#resume", "#cv"],
            "Offer Letter": ["#professional", "#offer-letter", "#employment"],
            "Pay Slip": ["#professional", "#payslip", "#salary"],
            "Bank Statement": ["#financial", "#bank", "#statement"],
            "Prescription": ["#medical", "#prescription", "#health"],
            "Electricity Bill": ["#utility", "#electricity", "#bill"],
            "Vehicle RC": ["#vehicle", "#rc", "#registration"],
            "Insurance Policy": ["#insurance", "#policy", "#financial"],
        }

        category = category_map.get(doc_type, "Unclassified")
        auto_tags = tag_map.get(doc_type, ["#document"])
        entities = {"PERSON": [], "ORG": [], "DATE": [], "ID_NUMBER": [], "GPE": []}
        action_items = {"expiry_date": None, "tasks": []}
        anomalies = []

        extracted_fields = DocumentProcessor._extract_fields_for_type(doc_type, ocr_text, ocr_lower, ocr_upper)

        # Build entities from extracted fields (only confirmed values)
        name = (
            extracted_fields.get("name")
            or extracted_fields.get("student_name")
            or extracted_fields.get("patient_name")
            or extracted_fields.get("owner_name")
            or extracted_fields.get("consumer_name")
        )
        if name:
            entities["PERSON"].append(name)

        id_val = (
            extracted_fields.get("aadhaar_number")
            or extracted_fields.get("pan_number")
            or extracted_fields.get("dl_number")
            or extracted_fields.get("roll_number")
            or extracted_fields.get("registration_number")
            or extracted_fields.get("account_number")
            or extracted_fields.get("consumer_number")
        )
        if id_val:
            entities["ID_NUMBER"].append(id_val)

        org = extracted_fields.get("bank_name") or extracted_fields.get("school_name") or extracted_fields.get("company_name")
        if org:
            entities["ORG"].append(org)

        for date_key in ["dob", "expiry_date", "joining_date", "date"]:
            d = extracted_fields.get(date_key)
            if d:
                entities["DATE"].append(d)

        # Action items from expiry
        expiry = extracted_fields.get("expiry_date") or extracted_fields.get("due_date")
        if expiry:
            action_items["expiry_date"] = expiry
            action_items["tasks"].append(f"Review expiry/due date: {expiry}")

        # Summary card
        summary = DocumentProcessor._build_summary(doc_type, extracted_fields, confidence)

        if not extracted_fields:
            anomalies.append("No fields could be extracted from this document — OCR quality may be low.")

        return {
            "category": category,
            "document_type": doc_type,
            "confidence_score": round(confidence, 3),
            "extracted_fields": extracted_fields,
            "summary_card": summary,
            "auto_tags": auto_tags,
            "action_items": action_items,
            "entities": entities,
            "anomalies": anomalies
        }

    @staticmethod
    def _extract_fields_for_type(
        doc_type: str,
        ocr_text: str,
        ocr_lower: str,
        ocr_upper: str
    ) -> Dict[str, Any]:
        """
        Extract fields from document text.

        For identity documents (Aadhaar, PAN, DL, Passport, Voter ID):
          - Runs the expert OCRExtractor prompt first (LLM-based precision extraction).
          - Falls back to / merges with regex patterns for any null fields.

        For all other document types:
          - Uses the regex-based pipeline only.

        Never returns hardcoded or invented values.
        """
        fields: Dict[str, Any] = {}
        if not ocr_text:
            return fields

        # ── Expert extraction for identity documents ──────────────────────────
        if doc_type in _IDENTITY_DOC_TYPES:
            try:
                from app.services.ocr_extractor import OCRExtractor
                logger.info(f"Running expert OCR extractor for '{doc_type}'...")
                expert_raw = OCRExtractor.extract(ocr_text)
                expert_fields = OCRExtractor.to_legacy_fields(expert_raw)
                # Only keep non-null expert fields
                fields.update({k: v for k, v in expert_fields.items() if v is not None})
                logger.info(f"Expert OCR extractor returned {len(fields)} fields for '{doc_type}'.")
            except Exception as e:
                logger.warning(f"Expert OCR extractor failed for '{doc_type}': {e}. Falling back to regex.")

        if doc_type == "Aadhaar Card":
            # Regex fills any field the expert extractor left as null
            if not fields.get("name"):
                name = DocumentProcessor._rex(ocr_text, [
                    r"(?:Name|NAME)[:\s]+([A-Za-z][A-Za-z\s]{2,35})(?=\n|\r|DOB|Gender|Aadhaar|$)",
                    r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})$"
                ])
                if name: fields["name"] = name

            if not fields.get("dob"):
                dob = DocumentProcessor._rex(ocr_text, [
                    r"(?:DOB|Date of Birth|Birth)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
                    r"(?:DOB|Birth)[:\s]+([\d]{4}-[\d]{2}-[\d]{2})"
                ])
                if dob: fields["dob"] = DocumentProcessor._to_iso_date(dob)

            if not fields.get("aadhaar_number"):
                aadhaar_no = DocumentProcessor._rex(ocr_text, [
                    r"(\d{4}\s\d{4}\s\d{4})",
                    r"(?:Aadhaar|No)[:\s]*(\d{12})"
                ])
                if aadhaar_no:
                    digits = aadhaar_no.replace(" ", "")
                    fields["aadhaar_number"] = f"{digits[:4]} {digits[4:8]} {digits[8:]}"

            if not fields.get("gender"):
                if re.search(r"\bfemale\b", ocr_lower): fields["gender"] = "Female"
                elif re.search(r"\bmale\b", ocr_lower): fields["gender"] = "Male"
                elif re.search(r"\btransgender\b", ocr_lower): fields["gender"] = "Transgender"

            if not fields.get("address"):
                addr = DocumentProcessor._rex(ocr_text, [
                    r"(?:Address|ADDR)[:\s]+(.{10,120})(?=\n\n|Aadhaar|$)",
                ])
                if addr: fields["address"] = addr.strip()

        elif doc_type == "PAN Card":
            if not fields.get("pan_number"):
                pan_no = DocumentProcessor._rex(ocr_upper, [r"\b([A-Z]{5}\d{4}[A-Z])\b"])
                if pan_no: fields["pan_number"] = pan_no

            if not fields.get("name"):
                name = DocumentProcessor._rex(ocr_text, [
                    r"(?:Name|NAME)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|Father|DOB|$)",
                ])
                if name: fields["name"] = name.strip()

            if not fields.get("father_name"):
                father = DocumentProcessor._rex(ocr_text, [
                    r"(?:Father|Father'?s Name|FATHER)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|DOB|PAN|$)",
                ])
                if father: fields["father_name"] = father.strip()

            if not fields.get("dob"):
                dob = DocumentProcessor._rex(ocr_text, [
                    r"(?:DOB|Date of Birth)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
                ])
                if dob: fields["dob"] = DocumentProcessor._to_iso_date(dob)

        elif doc_type == "Driving Licence":
            if not fields.get("dl_number"):
                dl_no = DocumentProcessor._rex(ocr_text, [
                    r"(?:DL No|DL Number|Licence No|Licence Number)[:\s]+([A-Z]{2}\d{2}[\s-]?\d{11,13})",
                    r"([A-Z]{2}\d{13})"
                ])
                if dl_no: fields["dl_number"] = dl_no.replace(" ", "").replace("-", "")

            if not fields.get("name"):
                name = DocumentProcessor._rex(ocr_text, [
                    r"(?:Name|NAME)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|DOB|Expiry|DL|$)",
                ])
                if name: fields["name"] = name.strip()

            if not fields.get("dob"):
                dob = DocumentProcessor._rex(ocr_text, [
                    r"(?:DOB|Date of Birth)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
                ])
                if dob: fields["dob"] = DocumentProcessor._to_iso_date(dob)

            if not fields.get("expiry_date"):
                expiry = DocumentProcessor._rex(ocr_text, [
                    r"(?:Validity|Valid Till|Expiry Date|Expires?)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
                ])
                if expiry: fields["expiry_date"] = DocumentProcessor._to_iso_date(expiry)

            classes = re.findall(r"\b(MCWG|LMV|HGMV|HPMV|MGV|PSV|TC|TRANS)\b", ocr_upper)
            if classes and not fields.get("vehicle_classes"):
                fields["vehicle_classes"] = list(set(classes))


        elif doc_type in ("Class 10 Marksheet", "Class 12 Marksheet"):
            student_name = DocumentProcessor._rex(ocr_text, [
                r"(?:Name of Candidate|Name of Student|Student Name|NAME)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|Roll|Board|$)",
            ])
            if student_name: fields["student_name"] = student_name.strip()

            roll = DocumentProcessor._rex(ocr_text, [
                r"(?:Roll No|Roll Number|Roll)[:\s]+(\d{4,10})",
            ])
            if roll: fields["roll_number"] = roll

            board = DocumentProcessor._rex(ocr_text, [
                r"(CBSE|ICSE|ISC|State Board|SSLC Board|[A-Z]{2,6}\s?Board)",
            ])
            if board: fields["board"] = board

            school = DocumentProcessor._rex(ocr_text, [
                r"(?:School|Institution|College)[:\s]+([A-Za-z][A-Za-z\s,\.]{4,60})(?=\n|Roll|$)",
            ])
            if school: fields["school_name"] = school.strip()

            year = DocumentProcessor._rex(ocr_text, [
                r"(?:Year of Passing|Year|Exam Year)[:\s]*(20\d{2}|19\d{2})",
                r"(20\d{2}|19\d{2})"
            ])
            if year:
                try: fields["year"] = int(year)
                except: pass

            pct = DocumentProcessor._rex(ocr_text, [
                r"(?:Percentage|Total Percentage|Overall)[:\s]*([\d]{2,3}(?:\.\d{1,2})?)",
            ])
            if pct:
                try: fields["percentage"] = float(pct)
                except: pass

            total = DocumentProcessor._rex(ocr_text, [
                r"(?:Total Marks|Max Marks|Maximum Marks)[:\s]*(\d{3,4})",
            ])
            if total:
                try: fields["total_marks"] = int(total)
                except: pass

            obtained = DocumentProcessor._rex(ocr_text, [
                r"(?:Marks Obtained|Total Obtained)[:\s]*(\d{3,4})",
            ])
            if obtained:
                try: fields["marks_obtained"] = int(obtained)
                except: pass

        elif doc_type == "Degree Certificate":
            student_name = DocumentProcessor._rex(ocr_text, [
                r"(?:awarded to|conferred upon|certify that)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|has|with|$)",
            ])
            if student_name: fields["student_name"] = student_name.strip()

            degree = DocumentProcessor._rex(ocr_text, [
                r"(?:degree of|Bachelor of|Master of|Doctor of|B\.Tech|M\.Tech|B\.Sc|M\.Sc)\s+([A-Za-z\s&]{2,50})",
            ])
            if degree: fields["degree"] = degree.strip()

            univ = DocumentProcessor._rex(ocr_text, [
                r"([A-Za-z\s]{3,40}(?:University|Institute of Technology|College))(?=\n|\.)",
            ])
            if univ: fields["university"] = univ.strip()

            year = DocumentProcessor._rex(ocr_text, [r"(20\d{2}|19\d{2})"])
            if year:
                try: fields["year"] = int(year)
                except: pass

        elif doc_type == "Resume":
            email = DocumentProcessor._rex(ocr_text, [
                r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"
            ])
            if email: fields["email"] = email

            phone = DocumentProcessor._rex(ocr_text, [
                r"(?:\+91[\s-]?)?(?:0)?([6-9]\d{9})",
                r"(\+\d{1,3}[\s-]\d{10})"
            ])
            if phone: fields["phone"] = phone

            # Heuristic name extraction: Check first 3 lines for alphabetic-only name-like patterns
            name = None
            lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
            for line in lines[:3]:
                clean_line = re.sub(r"\s+", " ", line).strip()
                if (re.match(r"^[a-zA-Z\s\.\-\']{2,40}$", clean_line) 
                        and not any(w in clean_line.lower() for w in ["email", "phone", "resume", "cv", "curriculum", "address", "contact", "profile"])):
                    name = clean_line
                    break
            
            if name: 
                fields["name"] = name.strip()

        elif doc_type == "Offer Letter":
            company = DocumentProcessor._rex(ocr_text, [
                r"(?:Company|Organisation|Employer)[:\s]+([A-Za-z][A-Za-z\s&\.]{2,50})(?=\n|Ltd|Pvt|Inc|$)",
                r"([A-Za-z][A-Za-z\s&\.]{3,40}(?:Limited|Pvt\. Ltd|Inc|LLP))"
            ])
            if company: fields["company_name"] = company.strip()

            role = DocumentProcessor._rex(ocr_text, [
                r"(?:Designation|Position|Role|Title)[:\s]+([A-Za-z][A-Za-z\s,]{2,50})(?=\n|CTC|Salary|$)",
            ])
            if role: fields["role"] = role.strip()

            ctc = DocumentProcessor._rex(ocr_text, [
                r"(?:CTC|Cost to Company|Annual|Compensation)[:\s]+(?:Rs\.?|INR|₹)?\s?([\d,\.]+(?:\s?(?:Lakhs?|lpa|LPA|per annum))?)",
            ])
            if ctc: fields["ctc"] = ctc.strip()

            joining = DocumentProcessor._rex(ocr_text, [
                r"(?:Joining Date|Date of Joining|Commencement)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
                r"(?:Joining Date|Date of Joining)[:\s]+([\d]{4}-[\d]{2}-[\d]{2})",
            ])
            if joining: fields["joining_date"] = DocumentProcessor._to_iso_date(joining)

        elif doc_type == "Pay Slip":
            emp_name = DocumentProcessor._rex(ocr_text, [
                r"(?:Employee Name|Name)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|Emp|$)",
            ])
            if emp_name: fields["employee_name"] = emp_name.strip()

            emp_id = DocumentProcessor._rex(ocr_text, [
                r"(?:Employee ID|Emp ID|Emp Code)[:\s]+([A-Za-z0-9\-]+)",
            ])
            if emp_id: fields["employee_id"] = emp_id.strip()

            gross = DocumentProcessor._rex(ocr_text, [
                r"(?:Gross Salary|Gross Pay|Gross)[:\s]+(?:Rs\.?|INR|₹)?\s?([\d,\.]+)",
            ])
            if gross: fields["gross_salary"] = gross.replace(",", "")

            net = DocumentProcessor._rex(ocr_text, [
                r"(?:Net Salary|Net Pay|Net Amount)[:\s]+(?:Rs\.?|INR|₹)?\s?([\d,\.]+)",
            ])
            if net: fields["net_salary"] = net.replace(",", "")

            month = DocumentProcessor._rex(ocr_text, [
                r"(?:Pay Period|Month|Salary for)[:\s]+([A-Za-z]+\s+\d{4}|\d{4}-\d{2})",
            ])
            if month: fields["pay_period"] = month

        elif doc_type == "Bank Statement":
            bank_name = DocumentProcessor._rex(ocr_text, [
                r"([A-Za-z\s]+(?:Bank|Financial Services|Co-operative))(?=\s|\n|\.)",
            ])
            if bank_name: fields["bank_name"] = bank_name.strip()

            acc_no = DocumentProcessor._rex(ocr_text, [
                r"(?:Account No|Acct No|Account Number)[:\s]+(\d{9,18})",
                r"(?:A/C No|AC No)[:\s]+(\d{9,18})",
            ])
            if acc_no: fields["account_number"] = acc_no

            ifsc = DocumentProcessor._rex(ocr_text, [
                r"(?:IFSC|IFSC Code)[:\s]+([A-Z]{4}0[A-Z0-9]{6})",
            ])
            if ifsc: fields["ifsc_code"] = ifsc

            balance = DocumentProcessor._rex(ocr_text, [
                r"(?:Closing Balance|Available Balance|Balance)[:\s]+(?:Rs\.?|INR|₹)?\s?([\d,\.]+)",
            ])
            if balance:
                try: fields["balance"] = float(balance.replace(",", ""))
                except: pass

        elif doc_type == "Prescription":
            patient = DocumentProcessor._rex(ocr_text, [
                r"(?:Patient Name|Patient|Name)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|Age|DOB|$)",
            ])
            if patient: fields["patient_name"] = patient.strip()

            doctor = DocumentProcessor._rex(ocr_text, [
                r"(?:Dr\.?|Doctor)[:\s]+([A-Za-z][A-Za-z\s\.]{2,40})(?=\n|MBBS|MD|$)",
                r"(Dr\.\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)"
            ])
            if doctor: fields["doctor_name"] = doctor.strip()

            rx_date = DocumentProcessor._rex(ocr_text, [
                r"(?:Date|Dated)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
            ])
            if rx_date: fields["date"] = DocumentProcessor._to_iso_date(rx_date)

            clinic = DocumentProcessor._rex(ocr_text, [
                r"([A-Za-z\s]+(?:Clinic|Hospital|Medical Centre|Health))(?=\n|,)",
            ])
            if clinic: fields["hospital_clinic"] = clinic.strip()

        elif doc_type == "Electricity Bill":
            consumer_name = DocumentProcessor._rex(ocr_text, [
                r"(?:Consumer Name|Name)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|Consumer|$)",
            ])
            if consumer_name: fields["consumer_name"] = consumer_name.strip()

            consumer_no = DocumentProcessor._rex(ocr_text, [
                r"(?:Consumer No|Consumer Number|Consumer ID)[:\s]+(\d{6,15})",
            ])
            if consumer_no: fields["consumer_number"] = consumer_no

            units = DocumentProcessor._rex(ocr_text, [
                r"(?:Units Consumed|Units)[:\s]+([\d\.]+)\s*(?:kWh|KWH|kwh|units?)",
            ])
            if units:
                try: fields["units_consumed"] = float(units)
                except: pass

            amount = DocumentProcessor._rex(ocr_text, [
                r"(?:Amount Due|Total Amount|Net Amount|Net Payable)[:\s]+(?:Rs\.?|INR|₹)?\s?([\d,\.]+)",
            ])
            if amount:
                try: fields["amount_due"] = float(amount.replace(",", ""))
                except: pass

            due_date = DocumentProcessor._rex(ocr_text, [
                r"(?:Due Date|Last Date|Pay Before)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
            ])
            if due_date: fields["due_date"] = DocumentProcessor._to_iso_date(due_date)

            meter = DocumentProcessor._rex(ocr_text, [
                r"(?:Meter No|Meter Number)[:\s]+([A-Za-z0-9\-]+)",
            ])
            if meter: fields["meter_number"] = meter

        elif doc_type == "Vehicle RC":
            reg_no = DocumentProcessor._rex(ocr_text, [
                r"(?:Registration No|Reg No|Regd No)[:\s]+([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})",
                r"\b([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})\b"
            ])
            if reg_no: fields["registration_number"] = reg_no

            owner = DocumentProcessor._rex(ocr_text, [
                r"(?:Owner Name|Owner|Registered Owner)[:\s]+([A-Za-z][A-Za-z\s]{2,40})(?=\n|S/O|D/O|$)",
            ])
            if owner: fields["owner_name"] = owner.strip()

            chassis = DocumentProcessor._rex(ocr_text, [
                r"(?:Chassis No|Chassis Number|CHS No)[:\s]+([A-Za-z0-9]{10,20})",
            ])
            if chassis: fields["chassis_number"] = chassis

            engine = DocumentProcessor._rex(ocr_text, [
                r"(?:Engine No|Engine Number|ENG No)[:\s]+([A-Za-z0-9]{6,20})",
            ])
            if engine: fields["engine_number"] = engine

            expiry = DocumentProcessor._rex(ocr_text, [
                r"(?:Valid Upto|Validity|Expiry Date|Registration Valid)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
            ])
            if expiry: fields["expiry_date"] = DocumentProcessor._to_iso_date(expiry)

            make_model = DocumentProcessor._rex(ocr_text, [
                r"(?:Make|Maker)[:\s]+([A-Za-z][A-Za-z\s]{1,30})(?=\n|Model|$)",
            ])
            if make_model: fields["make"] = make_model.strip()

            model = DocumentProcessor._rex(ocr_text, [
                r"(?:Model)[:\s]+([A-Za-z0-9][A-Za-z0-9\s\-]{1,30})(?=\n|Fuel|$)",
            ])
            if model: fields["model"] = model.strip()

        elif doc_type == "Insurance Policy":
            policy_no = DocumentProcessor._rex(ocr_text, [
                r"(?:Policy No|Policy Number)[:\s]+([A-Za-z0-9\-\/]+)",
            ])
            if policy_no: fields["policy_number"] = policy_no

            insurer = DocumentProcessor._rex(ocr_text, [
                r"([A-Za-z\s]+(?:Insurance|Life|Assurance|General)(?:\s+(?:Co|Company|Ltd))?)",
            ])
            if insurer: fields["insurer"] = insurer.strip()

            sum_insured = DocumentProcessor._rex(ocr_text, [
                r"(?:Sum Insured|Sum Assured|Coverage)[:\s]+(?:Rs\.?|INR|₹)?\s?([\d,\.]+)",
            ])
            if sum_insured:
                try: fields["sum_insured"] = float(sum_insured.replace(",", ""))
                except: pass

            expiry = DocumentProcessor._rex(ocr_text, [
                r"(?:Expiry Date|Policy Expiry|Valid Until)[:\s]+([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
            ])
            if expiry: fields["expiry_date"] = DocumentProcessor._to_iso_date(expiry)

        return fields

    @staticmethod
    def _build_unknown_result(ocr_text: str) -> Dict[str, Any]:
        """Return a safe Unknown Document result."""
        entities = {"PERSON": [], "ORG": [], "DATE": [], "ID_NUMBER": [], "GPE": []}
        nlp_entities = DocumentProcessor._extract_local_entities(ocr_text)
        entities.update(nlp_entities)

        return {
            "category": "Unclassified",
            "document_type": "Unknown Document",
            "confidence_score": 0.30,
            "extracted_fields": {
                "ocr_snippet": ocr_text[:400] if ocr_text else "No text extracted."
            },
            "summary_card": (
                "This document could not be classified with sufficient confidence. "
                "The text has been archived. Please review and manually categorize if needed."
            ),
            "auto_tags": ["#unclassified", "#review-required"],
            "action_items": {"expiry_date": None, "tasks": []},
            "entities": entities,
            "anomalies": ["Document type could not be determined with sufficient confidence (score below threshold)."]
        }

    @staticmethod
    def _rex(text: str, patterns: List[str]) -> Optional[str]:
        """
        Try multiple regex patterns in order and return first match group 1.
        Returns None if no pattern matches.
        """
        if not text:
            return None
        for pattern in patterns:
            try:
                m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if m:
                    val = m.group(1).strip()
                    if val:
                        return val
            except Exception:
                continue
        return None

    @staticmethod
    def _to_iso_date(date_str: str) -> Optional[str]:
        """Parse various date formats to YYYY-MM-DD."""
        if not date_str:
            return None
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y",
                   "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"]
        clean = date_str.strip()
        for fmt in formats:
            try:
                return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # Try YYYY/MM/DD
        m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", clean)
        if m:
            return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
        return None

    @staticmethod
    def _build_summary(doc_type: str, fields: Dict[str, Any], confidence: float) -> str:
        """Build a natural language summary from only confirmed field values."""
        parts = [f"Classified as {doc_type} with {int(confidence * 100)}% confidence."]

        name = (
            fields.get("name") or fields.get("student_name")
            or fields.get("patient_name") or fields.get("owner_name")
            or fields.get("employee_name") or fields.get("consumer_name")
        )
        if name:
            parts.append(f"Associated with: {name}.")

        for date_key, label in [("expiry_date", "Expires"), ("due_date", "Due"), ("dob", "Date of Birth"), ("joining_date", "Joining")]:
            if fields.get(date_key):
                parts.append(f"{label}: {fields[date_key]}.")
                break

        id_val = (
            fields.get("aadhaar_number") or fields.get("pan_number") or fields.get("dl_number")
            or fields.get("roll_number") or fields.get("registration_number")
        )
        if id_val:
            parts.append(f"ID: {id_val}.")

        # Contact Details (Resumes, general)
        email = fields.get("email")
        phone = fields.get("phone")
        if email:
            parts.append(f"Email: {email}.")
        if phone:
            parts.append(f"Phone: {phone}.")

        # Academic Details
        univ = fields.get("university") or fields.get("school_name")
        deg = fields.get("degree")
        if deg and univ:
            parts.append(f"Degree: {deg} from {univ}.")
        elif deg:
            parts.append(f"Degree: {deg}.")
        elif univ:
            parts.append(f"Institution: {univ}.")

        # Professional Details
        comp = fields.get("company_name")
        role = fields.get("role") or fields.get("designation")
        if role and comp:
            parts.append(f"Position: {role} at {comp}.")
        elif role:
            parts.append(f"Position: {role}.")
        elif comp:
            parts.append(f"Employer: {comp}.")

        if len(parts) == 1:
            parts.append("Limited text could be extracted — OCR quality may be low.")

        return " ".join(parts)

    @staticmethod
    def _extract_local_entities(text: str) -> Dict[str, List[str]]:
        """Extract named entities via spaCy or fallback regex."""
        results: Dict[str, List[str]] = {
            "PERSON": [], "ORG": [], "DATE": [], "ID_NUMBER": [], "GPE": []
        }
        if not text:
            return results

        nlp = get_spacy_nlp()
        if nlp:
            try:
                doc = nlp(text[:8000])
                seen = {k: set() for k in results}
                for ent in doc.ents:
                    if ent.label_ in results:
                        val = ent.text.strip()
                        norm = val.lower()
                        if val and len(val) > 1 and norm not in seen[ent.label_]:
                            results[ent.label_].append(val)
                            seen[ent.label_].add(norm)
                return results
            except Exception as e:
                logger.warning(f"spaCy entity extraction failed: {e}")

        # Regex fallback
        dates = re.findall(r"(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)", text)
        results["DATE"] = list(set(dates))[:5]

        ids = re.findall(r"\b([A-Z]{3,5}\d{4,12}[A-Z]?)\b", text)
        results["ID_NUMBER"] = list(set(ids))[:5]

        return results
