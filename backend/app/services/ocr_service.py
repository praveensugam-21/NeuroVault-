import os
import logging
from PIL import Image
from app.config import settings

logger = logging.getLogger("iris.ocr")
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
            _easyocr_reader = easyocr.Reader(['en', 'hi'], gpu=False, model_storage_directory=settings.MODEL_CACHE_DIR)
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

        # Try text extraction for PDFs (both digital text layer and scanned images)
        if file_type.lower() == "pdf":
            try:
                import fitz  # PyMuPDF is extremely fast and accurate
                import io
                doc_fitz = fitz.open(file_path)
                pdf_text = ""
                
                # 1. Try digital text extraction first via PyMuPDF
                for page_idx in range(len(doc_fitz)):
                    page = doc_fitz.load_page(page_idx)
                    page_text = page.get_text()
                    if page_text:
                        pdf_text += page_text + "\n"
                
                # 2. If it is a scanned PDF (no digital text found) and local OCR is enabled
                if not pdf_text.strip() and settings.ENABLE_LOCAL_OCR:
                    logger.info("No digital text found in PDF. Rendering pages to images for local EasyOCR fallback...")
                    try:
                        reader_easy = get_easyocr_reader()
                        if reader_easy:
                            for page_idx in range(len(doc_fitz)):
                                page = doc_fitz.load_page(page_idx)
                                # Render page at 150 DPI (zoom=2.0) for optimal OCR quality
                                zoom = 2.0
                                mat = fitz.Matrix(zoom, zoom)
                                pix = page.get_pixmap(matrix=mat)
                                img_data = pix.tobytes("png")
                                img = Image.open(io.BytesIO(img_data))
                                
                                results = reader_easy.readtext(img, detail=0)
                                if results:
                                    pdf_text += "\n".join(results) + "\n"
                    except Exception as ocr_err:
                        logger.error(f"PyMuPDF + EasyOCR page rendering fallback failed: {str(ocr_err)}")

                if pdf_text.strip():
                    logger.info("Successfully extracted text from PDF layer.")
                    return pdf_text
            except Exception as e:
                logger.warning(f"PDF text extraction failed: {str(e)}")

        # Run local OCR if allowed
        if settings.ENABLE_LOCAL_OCR:
            try:
                if file_type.lower() == "pdf":
                    logger.warning("Local EasyOCR does not support PDF files directly and pypdf returned no text.")
                    return ""
                return OCRService._extract_via_local_ocr(file_path)
            except Exception as e:
                logger.error(f"Local OCR extraction failed: {str(e)}")
                return ""

        logger.warning("No local OCR engines available. Returning empty text.")
        return ""

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
