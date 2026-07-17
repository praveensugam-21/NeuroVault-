import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.schemas.chat import ChatQuery, ChatResponse, ChatCitation
from app.services.pii_masker import PIIMasker
from app.services.gemini_service import GeminiService
from app.services.ollama_service import OllamaService
from app.services.rag_pipeline import RAGPipeline
from app.services.embedding_service import EmbeddingService

print("All imports OK")

# Test Pydantic schema with int document_id (the actual bug)
citation = ChatCitation(
    document_id=42,
    document_name="Aadhaar Card.pdf",
    category="Identity Documents",
    snippet="Name: Praveen Sugam",
    similarity=0.92,
    section="General",
    chunk_index=0
)
print(f"ChatCitation OK - document_id: {citation.document_id} (type: {type(citation.document_id).__name__})")

resp = ChatResponse(
    answer="Your name is Praveen Sugam.",
    citations=[citation],
    retrieval_method="ollama_chunks"
)
print(f"ChatResponse OK - answer: {len(resp.answer)} chars, citations: {len(resp.citations)}")

print()
print("=== LLM ROUTING ===")
gemini = GeminiService.is_available()
ollama = OllamaService.is_available()
print(f"Gemini: {'ACTIVE' if gemini else 'INACTIVE (key invalid -> fallback)'}")
print(f"Ollama: {'ACTIVE' if ollama else 'INACTIVE'}")
if not gemini and ollama:
    print("Pipeline will route to: Ollama (correct!)")
elif gemini:
    print("Pipeline will route to: Gemini API")
else:
    print("Pipeline will route to: Local Rules Engine")
