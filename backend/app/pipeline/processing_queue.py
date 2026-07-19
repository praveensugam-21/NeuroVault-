import os
import json
import logging
import traceback
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.document import Document, DocumentTag
from app.services.ocr_service import OCRService
from app.services.voice_service import VoiceService
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_graph import KnowledgeGraphService

logger = logging.getLogger("iris.pipeline")


class DocumentPipelineManager:

    @staticmethod
    def run_pipeline(document_id: str, user_id: int):
        """
        Synchronous pipeline entry point for use with FastAPI BackgroundTasks.
        Runs all processing stages sequentially in a background thread.
        """
        db: Session = SessionLocal()
        try:
            DocumentPipelineManager._process_pipeline(db, document_id, user_id)
        finally:
            db.close()

    @staticmethod
    def _process_pipeline(db: Session, document_id: str, user_id: int):
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Pipeline: Document {document_id} not found.")
            return

        try:
            logger.info(f"[Pipeline] Starting processing for '{document.name}' (ID: {document_id})")
            file_path = document.file_path
            file_type = document.file_type

            # ─ Step 1: Image Pre-processing (OpenCV) ────────────────────────────
            if file_type.upper() == "IMAGE":
                try:
                    import cv2
                    img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        denoised = cv2.fastNlMeansDenoising(img, None, 10, 7, 21)
                        logger.info("[Pipeline] OpenCV preprocessing complete.")
                except Exception as e:
                    logger.debug(f"[Pipeline] OpenCV preprocessing skipped: {e}")

            # ─ Step 2: OCR / Voice Transcription ────────────────────────────
            logger.info("[Pipeline] Running OCR / transcription...")
            ocr_text = ""
            try:
                if file_type.upper() == "AUDIO":
                    ocr_text = VoiceService.transcribe_audio(file_path)
                else:
                    ocr_text = OCRService.extract_text_from_file(file_path, file_type)
            except Exception as e:
                logger.warning(f"[Pipeline] OCR failed: {e}. Proceeding with empty text.")

            # ─ Step 3: Classification & Field Extraction ────────────────────
            logger.info("[Pipeline] Classifying document and extracting fields...")
            result = DocumentProcessor.process_document(
                file_path, file_type, ocr_text, original_name=document.name
            )

            category = result.get("category", "Unclassified")
            doc_type = result.get("document_type", "Unknown Document")
            confidence = result.get("confidence_score", 0.30)
            extracted_fields = result.get("extracted_fields", {})
            summary = result.get("summary_card", "")
            auto_tags = result.get("auto_tags", [])
            action_items = result.get("action_items", {"expiry_date": None, "tasks": []})
            entities_dict = result.get("entities", {"PERSON": [], "ORG": [], "DATE": [], "ID_NUMBER": [], "GPE": []})
            fields_json = json.dumps(extracted_fields)

            # ─ Step 4: Vector Embedding (ChromaDB Chunks) ───────────────────
            logger.info("[Pipeline] Generating semantic vector chunk embeddings...")
            try:
                EmbeddingService.add_document_chunks(
                    document_id=document_id,
                    user_id=user_id,
                    full_text=f"Summary: {summary}\nContent:\n{ocr_text}\nMetadata details:\n{fields_json}",
                    category=category,
                    doc_type=doc_type,
                    extracted_fields=extracted_fields
                )
            except Exception as e:
                logger.warning(f"[Pipeline] Vector embedding failed: {e}")

            # ─ Step 5: Knowledge Graph Linking ────────────────────────────
            logger.info("[Pipeline] Updating knowledge graph...")
            try:
                KnowledgeGraphService.link_document_entities(db, document, entities_dict)
            except Exception as e:
                logger.warning(f"[Pipeline] Knowledge graph linking failed: {e}")

            # ─ Step 6: Tag Routing ─────────────────────────────────────────
            for tag_name in auto_tags:
                if tag_name and isinstance(tag_name, str):
                    db_tag = DocumentTag(document_id=document_id, tag_name=tag_name[:128])
                    db.add(db_tag)

            # ─ Step 7: Persist to Database ────────────────────────────────
            document.category = category
            document.document_type = doc_type
            document.confidence_score = confidence
            from app.services.encryption_service import EncryptionService
            document.extracted_json = EncryptionService.encrypt(fields_json)
            document.summary = summary
            document.status = "COMPLETE"
            db.commit()

            logger.info(f"[Pipeline] Completed successfully for document '{document.name}' ({document_id})")

        except Exception as e:
            logger.error(f"[Pipeline] Processing failed for document {document_id}: {e}")
            logger.debug(traceback.format_exc())
            try:
                document.status = "FAILED"
                db.commit()
            except Exception:
                pass
