"""
IRIS Gemini Service — Cloud AI Integration (Direct REST API)
============================================================
Provides reliable, timeout-free completions via the Gemini REST API,
bypassing HTTP/2 and gRPC network handshake issues inside Docker/WSL.
All data sent through this service has been pre-processed by the local PII masking layer.
"""
import logging
import httpx
from app.config import settings

logger = logging.getLogger("iris.gemini")


class GeminiService:
    _verified: bool = False     # True only after a successful real API call
    _broken: bool = False       # True if key was tested and failed — skip retrying

    @classmethod
    def is_available(cls) -> bool:
        """
        Returns True when Gemini is configured and not permanently marked as broken.
        """
        if cls._broken:
            return False
        if not settings.GEMINI_API_KEY:
            return False
        return True

    @staticmethod
    def _is_temporary_error(e: Exception) -> bool:
        """Helper to classify if an API call exception is a temporary network/rate-limiting issue."""
        err_str = str(e).lower()
        if "429" in err_str or "503" in err_str:
            return True
        if "rate" in err_str or "quota" in err_str or "exhausted" in err_str:
            return True
        if "timeout" in err_str or "unreachable" in err_str or "conn" in err_str:
            return True
        # Check attributes
        for attr in ["code", "status_code"]:
            if hasattr(e, attr):
                val = getattr(e, attr)
                if val in (429, 503):
                    return True
        return False

    @classmethod
    def generate_completion(cls, prompt: str) -> str:
        """
        Calls Gemini 1.5 Flash via REST to generate a text completion.
        The prompt must already have PII masked by PIIMasker before calling this.

        Returns:
            The generated text, or an empty string on any failure.
        """
        if not settings.GEMINI_API_KEY or cls._broken:
            return ""

        try:
            logger.info(f"Calling Gemini REST API ({settings.GEMINI_MODEL})...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.9,
                    "topK": 40,
                    "maxOutputTokens": 2048
                }
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    cls._verified = True
                    logger.info("Gemini REST API call successful.")
                    return text.strip()
                logger.warning("Gemini REST API returned an empty response.")
                return ""
            else:
                logger.error(f"Gemini REST API failed with status {response.status_code}: {response.text}")
                
                # If it is a permanent authorization/key failure, mark broken
                if response.status_code in (400, 403) and "API_KEY_INVALID" in response.text:
                    cls._broken = True
                    
                # Create a custom exception so the caller can check status code
                class APIError(Exception):
                    def __init__(self, code, message):
                        self.status_code = code
                        super().__init__(message)
                raise APIError(response.status_code, f"Gemini API returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            if not cls._is_temporary_error(e):
                cls._broken = True
            raise e
