"""
IRIS OCR Field Extractor — Expert PII Extraction Layer
=======================================================
Uses a precision-engineered expert prompt to extract structured identity
fields from raw OCR text via Ollama (primary) or Gemini (fallback).

The prompt enforces strict rules:
  - ONLY extracts from the provided context
  - NEVER guesses, infers, or hallucinates
  - Returns null for any field below 95% confidence
  - Validates Aadhaar (12 digits), PIN (6 digits), PAN format, etc.

Supported Documents:
  Aadhaar Card, PAN Card, Passport, Driving License,
  Voter ID, and other government-issued identity documents.
"""
import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("iris.ocr_extractor")

# ── The Expert OCR Extraction Prompt ─────────────────────────────────────────
# Uses the user's precision prompt exactly, with {{retrieved_context}} replaced
# at call time.
_EXPERT_EXTRACTION_PROMPT = """You are an expert OCR Document Information Extraction AI specializing in identity documents such as Aadhaar Card, PAN Card, Passport, Driving License, Voter ID, and other government-issued documents.

Your task is to extract information ONLY from the provided OCR context.

The OCR text may contain:
- Broken words
- Missing characters
- Duplicate lines
- Incorrect spellings
- Random symbols
- OCR noise
- Incorrect line breaks
- Multiple occurrences of the same field

Your job is to identify the correct information ONLY from the provided context.

=========================
STRICT RULES
=========================

1. NEVER use outside knowledge.
2. NEVER guess missing characters.
3. NEVER autocomplete names.
4. NEVER infer addresses.
5. NEVER infer state names.
6. NEVER infer district names.
7. NEVER infer city names.
8. NEVER infer dates.
9. NEVER create information.
10. NEVER modify OCR text unless another occurrence of the SAME FIELD clearly confirms the correct value.
11. NEVER combine two different values.
12. NEVER fill missing values from memory.
13. NEVER answer from general knowledge.
14. ONLY use information explicitly available in the OCR context.
15. If multiple occurrences of the same field exist:
   - Compare every occurrence.
   - Select the clearest occurrence.
   - Prefer the occurrence with the least OCR errors.
   - If ambiguity remains, return null.
16. If confidence is below 95%, return null.
17. Preserve original capitalization.
18. Preserve original spacing.
19. Preserve Aadhaar spacing exactly (XXXX XXXX XXXX).
20. Preserve address line order.
21. Ignore QR codes.
22. Ignore barcodes.
23. Ignore logos.
24. Ignore Government slogans.
25. Ignore decorative text.
26. Ignore repeated headers.
27. Ignore repeated footers.
28. Ignore watermark text.
29. Ignore unrelated numbers.
30. Ignore enrollment IDs unless specifically requested.
31. Return ONLY requested fields.
32. Never explain your reasoning.
33. Never summarize.
34. Never add notes.
35. Never add comments.
36. Output ONLY valid JSON.

=========================
FIELD EXTRACTION RULES
=========================

NAME
- Extract only the card holder name.
- Do not include father name.
- Do not include address.

FATHER_NAME
- Extract only father name.

MOTHER_NAME
- Extract only if explicitly present.

DOB
- Extract exactly as written.
- Do not change format.

YEAR_OF_BIRTH
- Extract only if DOB is unavailable.

GENDER
- Male
- Female
- Transgender
- Otherwise null

AADHAAR_NUMBER
- Must contain 12 digits.
- Preserve XXXX XXXX XXXX format.
- If unreadable return null.

PAN_NUMBER
- Preserve exactly.

PASSPORT_NUMBER
- Preserve exactly.

DRIVING_LICENSE_NUMBER
- Preserve exactly.

VOTER_ID
- Preserve exactly.

ENROLLMENT_NUMBER
- Extract exactly if present.

MOBILE_NUMBER
- Extract only if explicitly visible.

EMAIL
- Extract only if explicitly visible.

ADDRESS
- Preserve original line order.
- Preserve OCR spelling.
- Preserve punctuation.
- Do not merge lines.

HOUSE_NUMBER
- Extract only if visible.

STREET
- Extract only if visible.

LOCALITY
- Extract only if visible.

CITY
- Extract only if visible.

DISTRICT
- Extract only if visible.

STATE
- Extract only if visible.

PINCODE
- Must contain exactly 6 digits.
- Otherwise return null.

=========================
VALIDATION
=========================

Aadhaar Number: Must contain exactly 12 digits.
PIN Code: Must contain exactly 6 digits.
DOB: Must be exactly as printed.
Gender: Must be Male, Female or Transgender.
Phone Number: Should contain 10 digits if present.

If validation fails: Return null for that field.

=========================
OUTPUT FORMAT
=========================

Return ONLY valid JSON. No markdown. No explanations. No notes. No comments.

Use this schema exactly:

{
  "name": null,
  "father_name": null,
  "mother_name": null,
  "dob": null,
  "year_of_birth": null,
  "gender": null,
  "aadhaar_number": null,
  "pan_number": null,
  "passport_number": null,
  "driving_license_number": null,
  "voter_id": null,
  "enrollment_number": null,
  "mobile_number": null,
  "email": null,
  "address": null,
  "house_number": null,
  "street": null,
  "locality": null,
  "city": null,
  "district": null,
  "state": null,
  "pincode": null
}

Before producing the JSON:
- Read the entire OCR context.
- Compare duplicate occurrences.
- Select the clearest occurrence.
- Never guess. Never infer. Never hallucinate. Never use external knowledge.
- If uncertain, return null.

OCR Context:

{ocr_context}"""


# ── Empty result template ─────────────────────────────────────────────────────
_EMPTY_RESULT: Dict[str, Any] = {
    "name": None,
    "father_name": None,
    "mother_name": None,
    "dob": None,
    "year_of_birth": None,
    "gender": None,
    "aadhaar_number": None,
    "pan_number": None,
    "passport_number": None,
    "driving_license_number": None,
    "voter_id": None,
    "enrollment_number": None,
    "mobile_number": None,
    "email": None,
    "address": None,
    "house_number": None,
    "street": None,
    "locality": None,
    "city": None,
    "district": None,
    "state": None,
    "pincode": None,
}


class OCRExtractor:
    """
    Expert OCR Field Extractor.

    Call OCRExtractor.extract(ocr_text) to get structured identity fields
    from raw OCR text. Tries Ollama first, Gemini second, and returns
    an empty null-filled result if both are unavailable.
    """

    @classmethod
    def extract(cls, ocr_text: str) -> Dict[str, Any]:
        """
        Extract structured PII fields from OCR text using the expert prompt.

        Priority:
          1. Ollama (local, fast, private)
          2. Gemini API (with automatic PII masking handled at caller level)
          3. Empty null-filled result (safe fallback)

        Returns:
            Dict matching the exact schema defined in _EMPTY_RESULT.
        """
        if not ocr_text or not ocr_text.strip():
            logger.warning("OCRExtractor.extract called with empty OCR text.")
            return dict(_EMPTY_RESULT)

        prompt = _EXPERT_EXTRACTION_PROMPT.replace("{ocr_context}", ocr_text.strip())

        # ── Try Ollama (primary — fast, fully local) ──────────────────────────
        try:
            from app.services.ollama_service import OllamaService
            if OllamaService.is_available():
                logger.info("OCR Extraction: Sending expert prompt to Ollama...")
                raw = OllamaService.generate_completion(prompt, format_json=True)
                if raw:
                    result = cls._parse_and_validate(raw)
                    if result:
                        logger.info("OCR Extraction via Ollama: SUCCESS")
                        return result
                    logger.warning("Ollama returned unparseable JSON for OCR extraction.")
        except Exception as e:
            logger.warning(f"Ollama OCR extraction failed: {e}")

        # ── Try Gemini (secondary — cloud, masked) ───────────────────────────
        try:
            from app.services.gemini_service import GeminiService
            if GeminiService.is_available():
                logger.info("OCR Extraction: Sending expert prompt to Gemini...")
                raw = GeminiService.generate_completion(prompt)
                if raw:
                    result = cls._parse_and_validate(raw)
                    if result:
                        logger.info("OCR Extraction via Gemini: SUCCESS")
                        return result
                    logger.warning("Gemini returned unparseable JSON for OCR extraction.")
        except Exception as e:
            logger.warning(f"Gemini OCR extraction failed: {e}")

        # ── Safe fallback ────────────────────────────────────────────────────
        logger.info("OCR Extraction: Both LLMs unavailable. Returning empty result.")
        return dict(_EMPTY_RESULT)

    @classmethod
    def _parse_and_validate(cls, raw: str) -> Optional[Dict[str, Any]]:
        """
        Parse the LLM's JSON response and apply strict field-level validation.

        Validation rules:
          - aadhaar_number: exactly 12 digits (allows spaces)
          - pincode: exactly 6 digits
          - pan_number: exactly AAAAA0000A format
          - gender: must be Male / Female / Transgender
          - mobile_number: 10 digits
          - email: valid email pattern

        Returns the validated dict, or None if the JSON cannot be parsed.
        """
        if not raw:
            return None

        # Strip markdown code fences if LLM wraps in ```json ... ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract first {...} block from the text
            match = re.search(r"\{[\s\S]+\}", cleaned)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from LLM OCR response.")
                    return None
            else:
                return None

        # Start with the empty template so all keys are always present
        result = dict(_EMPTY_RESULT)

        # Copy non-null values from the LLM response
        for key in _EMPTY_RESULT:
            val = data.get(key)
            if val is None or str(val).strip() in ("", "null", "None"):
                result[key] = None
            elif isinstance(val, dict):
                # Address sometimes comes back as a nested dict — flatten to string
                parts = [str(v) for v in val.values() if v is not None and str(v).strip()]
                result[key] = ", ".join(parts) if parts else None
            elif isinstance(val, (int, float)):
                result[key] = val
            else:
                result[key] = str(val).strip()

        # ── Validate Aadhaar Number (12 digits) ───────────────────────────────
        if result.get("aadhaar_number"):
            digits = re.sub(r"\s", "", str(result["aadhaar_number"]))
            if re.fullmatch(r"\d{12}", digits):
                # Enforce XXXX XXXX XXXX format
                result["aadhaar_number"] = f"{digits[:4]} {digits[4:8]} {digits[8:]}"
            else:
                logger.debug(f"Aadhaar validation failed for: {result['aadhaar_number']}")
                result["aadhaar_number"] = None

        # ── Validate PAN Number ────────────────────────────────────────────────
        if result.get("pan_number"):
            pan = str(result["pan_number"]).strip().upper()
            if re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan):
                result["pan_number"] = pan
            else:
                logger.debug(f"PAN validation failed for: {pan}")
                result["pan_number"] = None

        # ── Validate PIN Code (exactly 6 digits) ──────────────────────────────
        if result.get("pincode"):
            pin = re.sub(r"\s", "", str(result["pincode"]))
            if re.fullmatch(r"\d{6}", pin):
                result["pincode"] = pin
            else:
                logger.debug(f"Pincode validation failed for: {result['pincode']}")
                result["pincode"] = None

        # ── Validate Gender ───────────────────────────────────────────────────
        if result.get("gender"):
            g = str(result["gender"]).strip().capitalize()
            if g in ("Male", "Female", "Transgender"):
                result["gender"] = g
            else:
                result["gender"] = None

        # ── Validate Mobile Number (10 digits) ────────────────────────────────
        if result.get("mobile_number"):
            digits = re.sub(r"[\s\-\+]", "", str(result["mobile_number"]))
            # Strip leading +91 or 0
            digits = re.sub(r"^(?:\+91|91|0)", "", digits)
            if re.fullmatch(r"[6-9]\d{9}", digits):
                result["mobile_number"] = digits
            else:
                result["mobile_number"] = None

        # ── Validate Email ────────────────────────────────────────────────────
        if result.get("email"):
            if not re.fullmatch(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", str(result["email"])):
                result["email"] = None

        return result

    @classmethod
    def to_legacy_fields(cls, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps the OCRExtractor's flat schema to the legacy extracted_fields
        format used by the rest of the IRIS document pipeline
        (rag_pipeline.py, local rules engine, summary builder, etc.).

        Key mappings:
          - driving_license_number -> dl_number  (legacy RAG pipeline key)
          - mobile_number          -> phone       (legacy RAG pipeline key)
          - address sub-fields are stored individually AND combined into address string
        """
        fields: Dict[str, Any] = {}

        # Simple 1:1 field mappings
        simple_mapping = {
            "name":                   "name",
            "father_name":            "father_name",
            "mother_name":            "mother_name",
            "dob":                    "dob",
            "year_of_birth":          "year_of_birth",
            "gender":                 "gender",
            "aadhaar_number":         "aadhaar_number",
            "pan_number":             "pan_number",
            "passport_number":        "passport_number",
            "driving_license_number": "dl_number",
            "voter_id":               "voter_id",
            "enrollment_number":      "enrollment_number",
            "mobile_number":          "phone",
            "email":                  "email",
            "house_number":           "house_number",
            "street":                 "street",
            "locality":               "locality",
            "city":                   "city",
            "district":               "district",
            "state":                  "state",
            "pincode":                "pincode",
        }

        for src_key, dst_key in simple_mapping.items():
            val = extracted.get(src_key)
            if val is not None:
                fields[dst_key] = val

        # Build a clean address string from the address field or sub-fields
        address_val = extracted.get("address")
        if address_val and isinstance(address_val, str) and not address_val.startswith("{"):
            # Direct string address from LLM
            fields["address"] = address_val
        else:
            # Reconstruct from sub-fields
            addr_parts = [
                extracted.get("house_number"),
                extracted.get("street"),
                extracted.get("locality"),
                extracted.get("city"),
                extracted.get("district"),
                extracted.get("state"),
                extracted.get("pincode"),
            ]
            joined = ", ".join(p for p in addr_parts if p)
            if joined:
                fields["address"] = joined

        return fields
