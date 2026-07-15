"""
IRIS Post-OCR Corrector — Geographic & Text Error Correction
=============================================================
Fixes common OCR character substitution errors in extracted fields,
specifically for Indian geographic data (states, districts, cities)
and identity document text.

Two-layer correction strategy:
  1. Pincode → State/District lookup (authoritative — digits are OCR-accurate)
  2. Fuzzy string matching against known Indian states/UTs (catches "Jamil Nadu" → "Tamil Nadu")

Common OCR character confusions handled:
  T/J, m/n/rn, l/i/1, 0/O, a/o, h/b, u/n, N/H, d/cl, etc.
"""
import difflib
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("iris.post_ocr_corrector")

# ── All Indian States and Union Territories ───────────────────────────────────
_INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

# ── Pincode Prefix → State Mapping ────────────────────────────────────────────
# Based on India Post's official pincode zone system.
# First 2 digits of a 6-digit pincode determine the state.
_PINCODE_PREFIX_TO_STATE: Dict[str, str] = {
    "11": "Delhi",
    "12": "Haryana",
    "13": "Haryana",
    "14": "Punjab",
    "15": "Punjab",
    "16": "Punjab",
    "17": "Himachal Pradesh",
    "18": "Jammu and Kashmir",
    "19": "Jammu and Kashmir",
    "20": "Uttar Pradesh",
    "21": "Uttar Pradesh",
    "22": "Uttar Pradesh",
    "23": "Uttar Pradesh",
    "24": "Uttar Pradesh",
    "25": "Uttar Pradesh",
    "26": "Uttar Pradesh",
    "27": "Uttar Pradesh",
    "28": "Uttar Pradesh",
    "30": "Rajasthan",
    "31": "Rajasthan",
    "32": "Rajasthan",
    "33": "Rajasthan",
    "34": "Rajasthan",
    "36": "Gujarat",
    "37": "Gujarat",
    "38": "Gujarat",
    "39": "Gujarat",
    "40": "Maharashtra",
    "41": "Maharashtra",
    "42": "Maharashtra",
    "43": "Maharashtra",
    "44": "Maharashtra",
    "45": "Madhya Pradesh",
    "46": "Madhya Pradesh",
    "47": "Madhya Pradesh",
    "48": "Madhya Pradesh",
    "49": "Chhattisgarh",
    "50": "Telangana",
    "51": "Telangana",
    "52": "Andhra Pradesh",
    "53": "Andhra Pradesh",
    "56": "Karnataka",
    "57": "Karnataka",
    "58": "Karnataka",
    "59": "Karnataka",
    "60": "Tamil Nadu",
    "61": "Tamil Nadu",
    "62": "Tamil Nadu",
    "63": "Tamil Nadu",
    "64": "Tamil Nadu",
    "67": "Kerala",
    "68": "Kerala",
    "69": "Kerala",
    "70": "West Bengal",
    "71": "West Bengal",
    "72": "West Bengal",
    "73": "West Bengal",
    "74": "West Bengal",
    "75": "Odisha",
    "76": "Odisha",
    "77": "Odisha",
    "78": "Assam",
    "79": "Arunachal Pradesh",
    "80": "Bihar",
    "81": "Bihar",
    "82": "Bihar",
    "83": "Bihar",
    "84": "Bihar",
    "85": "Jharkhand",
    "86": "Jharkhand",
    "87": "Jharkhand",
    "90": "Army Post Office",
    "91": "Army Post Office",
    "92": "Army Post Office",
    "93": "Army Post Office",
    "94": "Army Post Office",
    "95": "Army Post Office",
}

# ── Common OCR word-level corrections for Indian geographic terms ──────────────
# Maps typical OCR noise patterns directly to correct values.
_KNOWN_OCR_CORRECTIONS: Dict[str, str] = {
    # States
    "jamil nadu":     "Tamil Nadu",
    "tamil nady":     "Tamil Nadu",
    "tamilnadu":      "Tamil Nadu",
    "tamii nadu":     "Tamil Nadu",
    "tamil naciu":    "Tamil Nadu",
    "karnatak":       "Karnataka",
    "kamataka":       "Karnataka",
    "karnalaka":      "Karnataka",
    "maharastra":     "Maharashtra",
    "maharashira":    "Maharashtra",
    "uttar pradesh":  "Uttar Pradesh",
    "uttarpradesh":   "Uttar Pradesh",
    "andhra pradesn": "Andhra Pradesh",
    "rajastnan":      "Rajasthan",
    "west begal":     "West Bengal",
    "west bengal":    "West Bengal",
    "himachal pradesn": "Himachal Pradesh",
    "jammnu kashmir": "Jammu and Kashmir",
    "jammu kashmir":  "Jammu and Kashmir",
    "puducheri":      "Puducherry",
    "pondicherry":    "Puducherry",
    # Common city/district mistakes
    "chenai":         "Chennai",
    "chenna1":        "Chennai",
    "coimbatcre":     "Coimbatore",
    "coimbatore":     "Coimbatore",
    "banglore":       "Bangalore",
    "bengaluru":      "Bengaluru",
    "mumhbai":        "Mumbai",
    "bombay":         "Mumbai",
    "hyderahad":      "Hyderabad",
    "kolkatta":       "Kolkata",
    "calcutta":       "Kolkata",
    "deihi":          "Delhi",
    "new deihi":      "New Delhi",
}


class PostOCRCorrector:
    """
    Post-processing corrector for OCR-extracted geographic and identity fields.

    Usage:
        corrected = PostOCRCorrector.correct_fields(extracted_fields)

    The corrected dict is a copy of extracted_fields with fixed values for
    state, district, city, pincode, and address where OCR errors were detected.
    """

    @classmethod
    def correct_fields(cls, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all correction passes to a dict of extracted OCR fields.
        Returns a corrected copy — never modifies the input in place.
        """
        result = dict(fields)

        pincode = cls._clean_pincode(result.get("pincode") or result.get("pincode"))

        # ── Pass 1: Authoritative pincode → state lookup ──────────────────────
        if pincode:
            result["pincode"] = pincode
            pincode_state = cls._state_from_pincode(pincode)
            if pincode_state:
                original_state = result.get("state")
                if original_state != pincode_state:
                    if original_state:
                        logger.info(
                            f"PostOCR: Corrected state '{original_state}' → '{pincode_state}' "
                            f"(from pincode {pincode})"
                        )
                    result["state"] = pincode_state

        # ── Pass 2: Known OCR correction dictionary ───────────────────────────
        for field in ("state", "city", "district", "locality"):
            val = result.get(field)
            if val:
                corrected = cls._apply_known_corrections(val)
                if corrected != val:
                    logger.info(f"PostOCR: Known correction for {field}: '{val}' → '{corrected}'")
                    result[field] = corrected

        # ── Pass 3: Fuzzy state matching (catches remaining OCR noise) ────────
        state_val = result.get("state")
        if state_val:
            fuzzy_state = cls._fuzzy_match_state(state_val)
            if fuzzy_state and fuzzy_state != state_val:
                # Only override if pincode didn't already fix it
                if not pincode or cls._state_from_pincode(pincode) is None:
                    logger.info(
                        f"PostOCR: Fuzzy state correction: '{state_val}' → '{fuzzy_state}'"
                    )
                    result["state"] = fuzzy_state

        # ── Pass 4: Rebuild address string if sub-fields changed ──────────────
        if result.get("address"):
            result["address"] = cls._rebuild_address(result)

        return result

    @classmethod
    def _clean_pincode(cls, raw: Optional[str]) -> Optional[str]:
        """Extract exactly 6 digits from raw pincode string."""
        if not raw:
            return None
        digits = "".join(c for c in str(raw) if c.isdigit())
        return digits if len(digits) == 6 else None

    @classmethod
    def _state_from_pincode(cls, pincode: str) -> Optional[str]:
        """
        Authoritatively determine the Indian state from a 6-digit pincode.
        Uses the first 2 digits which encode the postal circle (state).
        """
        if not pincode or len(pincode) < 2:
            return None
        prefix = pincode[:2]
        return _PINCODE_PREFIX_TO_STATE.get(prefix)

    @classmethod
    def _apply_known_corrections(cls, text: str) -> str:
        """Apply direct dictionary corrections for known OCR noise patterns."""
        normalized = text.strip().lower()
        correction = _KNOWN_OCR_CORRECTIONS.get(normalized)
        return correction if correction else text

    @classmethod
    def _fuzzy_match_state(cls, raw_state: str, cutoff: float = 0.75) -> Optional[str]:
        """
        Fuzzy-match raw_state against all known Indian states/UTs.
        Returns the best match if similarity >= cutoff, else None.

        cutoff=0.75 catches:
          "Jamil Nadu" → "Tamil Nadu"   (similarity ~0.82)
          "Kamataka"   → "Karnataka"    (similarity ~0.80)
          "Maharastra" → "Maharashtra"  (similarity ~0.89)
        """
        if not raw_state:
            return None
        matches = difflib.get_close_matches(
            raw_state.strip(),
            _INDIAN_STATES,
            n=1,
            cutoff=cutoff,
        )
        return matches[0] if matches else None

    @classmethod
    def _rebuild_address(cls, fields: Dict[str, Any]) -> str:
        """
        Rebuild a clean address string from individual sub-fields.
        Preserves original OCR text for street/locality (no fuzzy correction there),
        but uses corrected state/city/pincode values.
        """
        parts = []
        for key in ("house_number", "street", "locality", "city", "district", "state", "pincode"):
            val = fields.get(key)
            if val:
                parts.append(str(val).strip())

        # If no sub-fields, return original address
        if not parts:
            return fields.get("address", "")

        return ", ".join(parts)
