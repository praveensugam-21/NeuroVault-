import os
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from typing import List, Dict, Any

logger = logging.getLogger("iris.embeddings")

_sentence_transformer = None
_chroma_client = None
_chroma_collection = None


def get_embedding_model():
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
            _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {str(e)}")
            _sentence_transformer = None
    return _sentence_transformer


def get_chroma_collection():
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        try:
            logger.info(f"Initializing ChromaDB client at {settings.CHROMA_PERSIST_DIR}...")
            _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="iris_documents",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            _chroma_collection = None
    return _chroma_collection


class EmbeddingService:

    @staticmethod
    def _normalize_user_id(user_id) -> str:
        """
        Normalize user_id to string for consistent ChromaDB metadata filtering.
        ChromaDB metadata values must be consistent types — always store as str.
        """
        return str(user_id)

    @staticmethod
    def add_document(
        document_id: str,
        user_id: int,
        summary: str,
        full_text: str,
        category: str,
        doc_type: str
    ) -> bool:
        """
        Calculates embeddings for the document text and stores it in ChromaDB.
        user_id is stored as a string to ensure consistent filtering.
        """
        collection = get_chroma_collection()
        model = get_embedding_model()

        if collection is None or model is None:
            logger.warning("ChromaDB or SentenceTransformer unavailable. Skipping vector storage.")
            return False

        uid_str = EmbeddingService._normalize_user_id(user_id)

        try:
            # Build a rich composite text: summary + key fields + raw text snippet
            text_to_embed = (
                f"Category: {category}\n"
                f"Type: {doc_type}\n"
                f"Summary: {summary}\n"
                f"Content:\n{full_text[:3000]}"   # cap to 3000 chars for embedding window
            )

            embedding = model.encode(text_to_embed).tolist()

            # Delete existing entry first (update = delete + re-add)
            try:
                collection.delete(ids=[document_id])
            except Exception:
                pass  # Ignore if document wasn't previously indexed

            collection.add(
                ids=[document_id],
                embeddings=[embedding],
                metadatas=[{
                    "document_id": document_id,
                    "user_id": uid_str,          # Always string
                    "category": category or "Unclassified",
                    "document_type": doc_type or "Unknown",
                }],
                documents=[text_to_embed]
            )
            logger.info(f"Successfully indexed document {document_id} for user {uid_str}.")
            return True
        except Exception as e:
            logger.error(f"Failed to add document to vector store: {str(e)}")
            return False

    @staticmethod
    def delete_document(document_id: str) -> bool:
        """Deletes a document's vector from ChromaDB."""
        collection = get_chroma_collection()
        if collection is None:
            return False
        try:
            collection.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id} from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document from vector store: {str(e)}")
            return False

    @staticmethod
    def search(user_id: int, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        Performs semantic search across the user's documents.
        user_id is normalized to string to match stored metadata.
        Returns up to top_k results sorted by similarity.
        """
        collection = get_chroma_collection()
        model = get_embedding_model()

        if collection is None or model is None:
            logger.warning("ChromaDB or embedding model unavailable. Skipping vector search.")
            return []

        uid_str = EmbeddingService._normalize_user_id(user_id)

        try:
            # Check how many docs exist for user before querying
            try:
                existing = collection.get(where={"user_id": uid_str})
                total_user_docs = len(existing.get("ids", []))
            except Exception:
                total_user_docs = 0

            if total_user_docs == 0:
                logger.info(f"No documents indexed in ChromaDB for user {uid_str}.")
                return []

            # Clamp top_k to available docs to avoid ChromaDB error
            effective_k = min(top_k, total_user_docs)

            query_embedding = model.encode(query).tolist()

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=effective_k,
                where={"user_id": uid_str}   # Filter by string user_id
            )

            hits = []
            if results and results.get("ids") and len(results["ids"][0]) > 0:
                ids = results["ids"][0]
                distances = results.get("distances", [[0.0] * len(ids)])[0]
                documents = results.get("documents", [[]] * len(ids))[0]
                metadatas = results.get("metadatas", [[]] * len(ids))[0]

                for i in range(len(ids)):
                    # Convert cosine distance (0=identical, 2=opposite) to similarity (0-1)
                    similarity = max(0.0, 1.0 - (distances[i] / 2.0)) if distances[i] is not None else 0.5
                    hits.append({
                        "document_id": ids[i],
                        "similarity": round(similarity, 4),
                        "text": documents[i] if documents else "",
                        "metadata": metadatas[i] if metadatas else {},
                    })

            logger.info(f"Vector search returned {len(hits)} hits for user {uid_str}.")
            return hits

        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []

    @staticmethod
    def get_all_user_documents(user_id: int) -> List[str]:
        """
        Returns all document IDs indexed in ChromaDB for a user.
        Used as SQL fallback when vector search fails.
        """
        collection = get_chroma_collection()
        if collection is None:
            return []
        uid_str = EmbeddingService._normalize_user_id(user_id)
        try:
            result = collection.get(where={"user_id": uid_str})
            return result.get("ids", [])
        except Exception as e:
            logger.error(f"Failed to get all user documents: {str(e)}")
            return []
