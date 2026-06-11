import os
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from typing import List, Dict, Any

logger = logging.getLogger("neurovault.embeddings")

_sentence_transformer = None
_chroma_client = None
_chroma_collection = None

def get_embedding_model():
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2' (this may download weights on first run)...")
            _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {str(e)}")
            _sentence_transformer = None
    return _sentence_transformer

def get_chroma_collection():
    global _chroma_client, _chroma_collection
    if _chroma_client is None:
        try:
            logger.info(f"Initializing ChromaDB client at {settings.CHROMA_PERSIST_DIR}...")
            _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            # Fetch or create collection
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="neurovault_documents",
                metadata={"hnsw:space": "cosine"} # Use cosine similarity
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            _chroma_collection = None
    return _chroma_collection

class EmbeddingService:
    @staticmethod
    def add_document(document_id: str, user_id: int, summary: str, full_text: str, category: str, doc_type: str) -> bool:
        """
        Calculates embeddings for the document text and stores it in ChromaDB.
        """
        collection = get_chroma_collection()
        model = get_embedding_model()
        
        if collection is None or model is None:
            logger.warning("ChromaDB or SentenceTransformer model is unavailable. Skipping vector storage.")
            return False

        try:
            # We construct a composite text block: Summary + a snippet of key text/fields
            # This makes the retrieval highly effective for direct questions
            text_to_embed = f"Category: {category}\nType: {doc_type}\nSummary: {summary}\nContent:\n{full_text}"
            
            # Compute 384-dimensional vector embedding
            embedding = model.encode(text_to_embed).tolist()
            
            # Insert into ChromaDB collection
            collection.add(
                ids=[document_id],
                embeddings=[embedding],
                metadatas=[{
                    "document_id": document_id,
                    "user_id": user_id,
                    "category": category or "Unclassified",
                    "document_type": doc_type or "Unknown"
                }],
                documents=[text_to_embed]
            )
            logger.info(f"Successfully added document {document_id} to ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to add document to vector store: {str(e)}")
            return False

    @staticmethod
    def delete_document(document_id: str) -> bool:
        """
        Deletes vector index of a document from ChromaDB.
        """
        collection = get_chroma_collection()
        if collection is None:
            return False
        try:
            collection.delete(ids=[document_id])
            logger.info(f"Successfully deleted document {document_id} from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document from vector store: {str(e)}")
            return False

    @staticmethod
    def search(user_id: int, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs semantic search across the user's documents.
        Filters by user_id to prevent data leaks.
        """
        collection = get_chroma_collection()
        model = get_embedding_model()
        
        if collection is None or model is None:
            logger.warning("ChromaDB or Embedding model not loaded. Skipping search.")
            return []

        try:
            # Embed search query
            query_embedding = model.encode(query).tolist()
            
            # Query ChromaDB collection with user_id metadata filter
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"user_id": user_id}
            )
            
            hits = []
            if results and results.get("ids") and len(results["ids"][0]) > 0:
                ids = results["ids"][0]
                distances = results["distances"][0] if "distances" in results else [0.0] * len(ids)
                documents = results["documents"][0] if "documents" in results else [""] * len(ids)
                metadatas = results["metadatas"][0] if "metadatas" in results else [{}] * len(ids)
                
                for i in range(len(ids)):
                    # Distance is cosine distance. 0.0 = identical, 2.0 = opposite.
                    # Convert to similarity score
                    similarity = 1.0 - (distances[i] / 2.0) if distances[i] else 0.5
                    hits.append({
                        "document_id": ids[i],
                        "similarity": similarity,
                        "text": documents[i],
                        "metadata": metadatas[i]
                    })
            return hits
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []
