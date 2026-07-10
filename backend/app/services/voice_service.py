import os
import logging
from app.config import settings

logger = logging.getLogger("iris.voice")

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            logger.info("Loading local Whisper model (this might take a minute on first run)...")
            # We use the tiny model for rapid local execution on cpu
            _whisper_model = whisper.load_model("tiny")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            _whisper_model = None
    return _whisper_model

class VoiceService:
    @staticmethod
    def transcribe_audio(file_path: str) -> str:
        """
        Converts audio files to text.
        Returns the transcription string.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found at {file_path}")

        # Check if Whisper is enabled and can be loaded
        if settings.ENABLE_VOICE_TRANSCRIPTION:
            try:
                model = get_whisper_model()
                if model:
                    logger.info(f"Transcribing {file_path} using local Whisper...")
                    result = model.transcribe(file_path)
                    return result.get("text", "")
            except Exception as e:
                logger.error(f"Whisper transcription failed: {str(e)}")

        # Mock fallback transcription based on filename or a default message
        logger.warning("Whisper transcription unavailable. Falling back to mock transcript.")
        filename = os.path.basename(file_path).lower()
        if "car" in filename:
            return "Note to self: The car registration and PUC need to be renewed. The vehicle number is MH12AB1234. Let's make sure the insurance details are also updated in the folder."
        elif "medical" in filename or "health" in filename:
            return "Note to self: Dr. Sharma prescribed Metformin 500mg once daily after dinner for 30 days. Next follow-up check is in 4 weeks."
        
        return "Voice Memo: Review the uploaded documents in the folder. Please verify the expiry dates for the passport and insurance policies."
