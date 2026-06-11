import os
import logging
from PIL import Image
from app.config import settings

logger = logging.getLogger("neurovault.ocr")
logging.basicConfig(level=logging.INFO)

# Global variables for lazy loading local OCR
_easyocr_reader = None

def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader (this may take a moment on first load)...")
            # Set download_enabled=True to fetch model files if not present.
            # We initialize for English (en) and Hindi (hi) which is common for Indian documents.
            _easyocr_reader = easyocr.Reader(['en', 'hi'], gpu=False)
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {str(e)}")
            _easyocr_reader = None
    return _easyocr_reader

class OCRService:
    @staticmethod
    def extract_text_from_file(file_path: str, file_type: str) -> str:
        """
        Runs OCR or direct text extraction based on file type.
        Supports: images, PDFs, plain text.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        # If it's a plain text file, read directly
        if file_type.lower() == "text":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read text file directly: {str(e)}")
                return ""

        # For PDFs and Images:
        # Check if we can use Gemini (primary)
        if settings.GEMINI_API_KEY:
            try:
                return OCRService._extract_via_gemini(file_path, file_type)
            except Exception as e:
                logger.warning(f"Gemini OCR failed, falling back to local OCR: {str(e)}")

        # Fallback to local OCR if allowed
        if settings.ENABLE_LOCAL_OCR:
            try:
                return OCRService._extract_via_local_ocr(file_path)
            except Exception as e:
                logger.error(f"Local OCR extraction failed: {str(e)}")
                return ""

        logger.warning("No OCR keys or local engines available. Returning empty text.")
        return ""

    @staticmethod
    def _extract_via_gemini(file_path: str, file_type: str) -> str:
        """
        Uses Gemini 1.5 Flash to extract raw readable text from the file.
        """
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Load model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = (
            "You are an advanced OCR engine. Read this document image or file and output "
            "all readable text inside it verbatim. Keep table layouts and structures as plain text."
        )

        # Gemini supports PDF directly if sent as bytes
        if file_type.lower() == "pdf":
            with open(file_path, "rb") as f:
                pdf_data = f.read()
            
            response = model.generate_content([
                prompt,
                {
                    "mime_type": "application/pdf",
                    "data": pdf_data
                }
            ])
        else:
            # Assume image file
            image = Image.open(file_path)
            response = model.generate_content([prompt, image])
            
        return response.text if response.text else ""

    @staticmethod
    def _extract_via_local_ocr(file_path: str) -> str:
        """
        Uses EasyOCR to scan local image file.
        """
        reader = get_easyocr_reader()
        if not reader:
            raise RuntimeError("EasyOCR is not available.")

        # EasyOCR works on image file path
        # Let's perform readtext
        results = reader.readtext(file_path, detail=0)
        # Combine lines of text
        return "\n".join(results)
