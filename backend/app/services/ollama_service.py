import httpx
import logging
from app.config import settings

logger = logging.getLogger("iris.ollama")


class OllamaService:

    @staticmethod
    def is_available() -> bool:
        """
        Quick health check — returns True only if Ollama is reachable and has models loaded.
        Fails fast (2-second timeout) so it doesn't stall the request pipeline.
        """
        if not settings.OLLAMA_BASE_URL or any(x in settings.OLLAMA_BASE_URL.lower() for x in ["disabled", "none", "false", "empty"]):
            return False
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return len(models) > 0
        except Exception:
            pass
        return False

    @staticmethod
    def generate_completion(prompt: str, format_json: bool = False) -> str:
        """
        Queries the local Ollama REST API to generate text completions.
        Returns empty string on any failure — callers must handle the fallback.
        """
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        if format_json:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=float(settings.OLLAMA_TIMEOUT)) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                else:
                    logger.error(f"Ollama error {response.status_code}: {response.text[:300]}")
                    return ""
        except Exception as e:
            logger.error(f"Failed to communicate with Ollama: {str(e)}")
            return ""
