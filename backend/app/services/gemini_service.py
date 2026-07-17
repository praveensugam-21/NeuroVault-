"""
IRIS Gemini Service — Cloud AI Integration (google-genai SDK v2)
================================================================
Wraps the official Google Generative AI SDK to provide structured
completions via the Gemini API. All data sent through this service
has been pre-processed by the local PII masking layer.

Uses: google-genai (new official SDK — replaces deprecated google.generativeai)
"""
import logging
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("iris.gemini")

# ── Generation config — optimised for accurate, structured document Q&A ───────
_GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    top_p=0.9,
    top_k=40,
    max_output_tokens=2048,
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
    ],
)


class GeminiService:
    _client: "genai.Client | None" = None
    _verified: bool = False     # True only after a successful real API call
    _broken: bool = False       # True if key was tested and failed — skip retrying

    @classmethod
    def _get_client(cls) -> "genai.Client | None":
        """
        Returns the singleton Gemini client, initialising it on first call.
        Returns None if GEMINI_API_KEY is not set.
        """
        if cls._broken:
            return None
        if cls._client is not None:
            return cls._client
        if not settings.GEMINI_API_KEY:
            logger.debug("GEMINI_API_KEY is not configured. Gemini will be skipped.")
            return None
        try:
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Gemini client object created (key not yet verified).")
            return cls._client
        except Exception as e:
            logger.error(f"Failed to create Gemini client: {e}")
            cls._broken = True
            return None

    @classmethod
    def is_available(cls) -> bool:
        """
        Returns True only when Gemini is both configured AND the API key is verified valid.
        On first call, performs a minimal live probe to validate the key.
        """
        if cls._broken:
            return False
        if cls._verified:
            return True
        if not settings.GEMINI_API_KEY:
            return False

        # Validate the key with a tiny probe call
        client = cls._get_client()
        if not client:
            return False

        try:
            probe = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents="Reply with only the word: READY",
                config=types.GenerateContentConfig(max_output_tokens=100, temperature=0.0),
            )
            if probe and probe.text:
                cls._verified = True
                logger.info("Gemini API key verified successfully. Service is active.")
                return True
            else:
                logger.warning("Gemini probe returned empty response. Marking as unavailable.")
                cls._broken = True
                return False
        except Exception as e:
            logger.warning(f"Gemini API key validation failed: {e}. Falling back to Ollama/local rules.")
            cls._broken = True
            return False

    @classmethod
    def generate_completion(cls, prompt: str) -> str:
        """
        Calls Gemini 1.5 Flash to generate a text completion.
        The prompt must already have PII masked by PIIMasker before calling this.

        Returns:
            The generated text, or an empty string on any failure.
        """
        client = cls._get_client()
        if not client:
            return ""

        try:
            logger.info(f"Calling Gemini API ({settings.GEMINI_MODEL})...")
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=_GENERATION_CONFIG,
            )
            if response and response.text:
                logger.info("Gemini API call successful.")
                return response.text.strip()

            logger.warning("Gemini API returned an empty or blocked response.")
            return ""
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            # Mark broken so future calls don't waste time
            cls._broken = True
            return ""
