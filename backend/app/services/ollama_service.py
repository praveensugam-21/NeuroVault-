import httpx
import logging
from app.config import settings

logger = logging.getLogger("neurovault.ollama")

class OllamaService:
    @staticmethod
    def generate_completion(prompt: str, format_json: bool = False) -> str:
        """
        Queries the local Ollama REST API to generate text completions.
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
            # Set a long timeout (120s) because CPU-based local LLM generation can be slow
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                else:
                    logger.error(f"Ollama returned error status {response.status_code}: {response.text}")
                    return ""
        except Exception as e:
            logger.error(f"Failed to communicate with local Ollama: {str(e)}")
            return ""
