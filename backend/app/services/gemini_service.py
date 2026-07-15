"""
IRIS Gemini Service — Cloud AI Integration (google-genai SDK v2)
================================================================
Wraps the official Google Generative AI SDK to provide structured
completions via the Gemini API. All data sent through this service
has been pre-processed by the local PII masking layer.

Uses: google-genai (the new official SDK — replaces deprecated google.generativeai)
"""
import logging
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("iris.gemini")

# ── Generation config — optimised for accurate, structured document Q&A ───────
_GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.2,        # Low = more accurate, less hallucinatory
    top_p=0.9,
    top_k=40,
    max_output_tokens=2048,
    safety_settings=[
        types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_ONLY_HIGH",
        ),
    ],
)


class GeminiService:
    _client: genai.Client = None

    @classmethod
    def _get_client(cls) -> "genai.Client | None":
        """
        Returns the singleton Gemini client, initialising it on first call.
        Returns None if GEMINI_API_KEY is not configured.
        """
        if cls._client is not None:
            return cls._client

        if not settings.GEMINI_API_KEY:
            logger.debug("GEMINI_API_KEY is not set. Gemini calls will be skipped.")
            return None

        try:
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Google Gemini client initialised successfully (google-genai SDK).")
            return cls._client
        except Exception as e:
            logger.error(f"Failed to initialise Gemini client: {e}")
            return None

    @classmethod
    def is_available(cls) -> bool:
        """Returns True if the Gemini client is ready to accept requests."""
        return cls._get_client() is not None

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
            logger.info("Calling Gemini API (gemini-1.5-flash)...")
            response = client.models.generate_content(
                model="gemini-1.5-flash",
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
            return ""
