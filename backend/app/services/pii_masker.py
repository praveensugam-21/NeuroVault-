"""
IRIS PII Masker — Local Privacy Enforcement Layer
===================================================
Detects and masks Personally Identifiable Information (PII) from text
before transmitting to any external AI API. All masking and unmasking
happens 100% locally on this machine.

Supported PII Types:
  - Aadhaar Numbers (spaced and raw)
  - PAN Card Numbers
  - Passport Numbers
  - Bank Account Numbers (common Indian patterns)
  - Email Addresses
  - Indian Mobile Phone Numbers (with/without +91)
"""
import re
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger("iris.pii_masker")


class PIIMasker:
    # ── Aadhaar: 12 digits spaced (1234 5678 9012) or raw (123456789012) ──────
    AADHAAR_SPACED_PATTERN = re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b')
    AADHAAR_RAW_PATTERN    = re.compile(r'\b\d{12}\b')

    # ── PAN: 5 alpha + 4 digits + 1 alpha (case-insensitive match) ────────────
    PAN_PATTERN = re.compile(r'\b[A-Za-z]{5}\d{4}[A-Za-z]\b')

    # ── Passport: Indian passport format (1 letter + 7 digits) ───────────────
    PASSPORT_PATTERN = re.compile(r'\b[A-Z][0-9]{7}\b')

    # ── Bank Account: 9–18 digit numbers (common Indian bank formats) ─────────
    # Must be prefixed by a keyword to avoid false positives (e.g. chunk_index numbers)
    BANK_ACCOUNT_PATTERN = re.compile(
        r'(?:account\s*(?:number|no\.?|#)?[\s:]+)(\d{9,18})',
        re.IGNORECASE
    )

    # ── Email: standard RFC-compatible pattern ────────────────────────────────
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

    # ── Phone: Indian mobile numbers (with or without +91 / 0) ───────────────
    PHONE_PATTERN = re.compile(r'(?:\+91[\-\s]?|\b)[6-9]\d{9}\b')

    # ── Driving Licence: Indian DL format (State code + 13 digits approx) ─────
    DL_PATTERN = re.compile(r'\b[A-Z]{2}\d{2}\s?\d{11}\b')

    @classmethod
    def mask_text(
        cls,
        text: str,
        mapping: Optional[Dict[str, str]] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Scans input text for all supported PII patterns and replaces each
        unique value with a deterministic placeholder token.

        Args:
            text: The raw text to mask.
            mapping: An existing placeholder -> original-value dict to extend.
                     Pass this across multiple calls to maintain a single session map.

        Returns:
            A tuple of (masked_text, updated_mapping).
        """
        if text is None:
            return "", mapping if mapping is not None else {}

        if mapping is None:
            mapping = {}

        masked_text = text

        def _replace(pattern: re.Pattern, prefix: str, current_text: str, group: int = 0) -> str:
            """Find all pattern matches and replace with stable placeholders."""
            for m in sorted(set(pattern.findall(current_text)), key=len, reverse=True):
                raw_value = m.strip() if isinstance(m, str) else m[group].strip()
                full_match = m if isinstance(m, str) else pattern.search(current_text).group(0)

                # Reuse existing placeholder for the same raw value
                existing_key = next(
                    (k for k, v in mapping.items() if v == raw_value), None
                )
                if existing_key:
                    placeholder = existing_key
                else:
                    placeholder = f"[{prefix}_{len(mapping)}]"
                    mapping[placeholder] = raw_value

                current_text = current_text.replace(full_match, placeholder, 1)

            return current_text

        # Order matters: longer/more specific patterns first to avoid partial replacements
        masked_text = _replace(cls.AADHAAR_SPACED_PATTERN, "AADHAAR", masked_text)
        masked_text = _replace(cls.AADHAAR_RAW_PATTERN,    "AADHAAR", masked_text)
        masked_text = _replace(cls.PAN_PATTERN,            "PAN",     masked_text)
        masked_text = _replace(cls.PASSPORT_PATTERN,       "PASSPORT",masked_text)
        masked_text = _replace(cls.DL_PATTERN,             "DL",      masked_text)
        masked_text = _replace(cls.EMAIL_PATTERN,          "EMAIL",   masked_text)
        masked_text = _replace(cls.PHONE_PATTERN,          "PHONE",   masked_text)

        # Bank account: capture the number group only
        for m in cls.BANK_ACCOUNT_PATTERN.finditer(masked_text):
            raw_value = m.group(1).strip()
            existing_key = next(
                (k for k, v in mapping.items() if v == raw_value), None
            )
            if existing_key:
                placeholder = existing_key
            else:
                placeholder = f"[BANK_ACCT_{len(mapping)}]"
                mapping[placeholder] = raw_value
            # Replace only the captured number part inside the full match
            masked_text = masked_text.replace(m.group(0), m.group(0).replace(raw_value, placeholder), 1)

        return masked_text, mapping

    @classmethod
    def unmask_text(cls, text: str, mapping: Dict[str, str]) -> str:
        """
        Restores all placeholder tokens back to their original values using
        the session mapping generated by mask_text().

        Args:
            text: The LLM response text containing placeholder tokens.
            mapping: The placeholder -> original-value dict from mask_text().

        Returns:
            The fully reconstructed text with original values restored.
        """
        if not text or not mapping:
            return text or ""

        unmasked_text = text
        # Sort by length descending to avoid partial key replacement
        # e.g., [AADHAAR_10] replaced before [AADHAAR_1]
        for key in sorted(mapping.keys(), key=len, reverse=True):
            unmasked_text = unmasked_text.replace(key, mapping[key])

        return unmasked_text
