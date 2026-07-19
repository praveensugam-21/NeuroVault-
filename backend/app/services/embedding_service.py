import os
import re
import logging
import numpy as np
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger("iris.embeddings")

_sentence_transformer = None
_cross_encoder = None
_chroma_client = None
_chroma_collection = None


def get_embedding_model():
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            # SOTA 1024-dimension model BAAI/bge-large-en-v1.5
            logger.info("Loading SOTA SentenceTransformer model 'BAAI/bge-large-en-v1.5'...")
            _sentence_transformer = SentenceTransformer("BAAI/bge-large-en-v1.5")
        except Exception as e:
            logger.error(f"Failed to load SOTA SentenceTransformer: {str(e)}")
            _sentence_transformer = None
    return _sentence_transformer


def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            # SOTA Reranker model BAAI/bge-reranker-large
            logger.info("Loading SOTA CrossEncoder reranker 'BAAI/bge-reranker-large'...")
            _cross_encoder = CrossEncoder("BAAI/bge-reranker-large")
        except Exception as e:
            logger.error(f"Failed to load SOTA CrossEncoder: {str(e)}")
            _cross_encoder = None
    return _cross_encoder


def get_chroma_collection():
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        try:
            logger.info(f"Initializing ChromaDB client at {settings.CHROMA_PERSIST_DIR}...")
            _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            # Use a new collection name 'iris_documents_chunks_bge_large' to force fresh 1024-dimension schema
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="iris_documents_chunks_bge_large",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            _chroma_collection = None
    return _chroma_collection


class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        return self._split(text, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = separators[0]
        splits = text.split(separator) if separator else list(text)

        chunks = []
        current_chunk = []
        current_len = 0

        for split in splits:
            joint_len = current_len + len(split) + (len(separator) if current_chunk else 0)
            if joint_len <= self.chunk_size:
                current_chunk.append(split)
                current_len = joint_len
            else:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                if len(split) > self.chunk_size:
                    chunks.extend(self._split(split, separators[1:]))
                    current_chunk = []
                    current_len = 0
                else:
                    overlap_chunk = []
                    overlap_len = 0
                    for prev in reversed(current_chunk):
                        prev_joint_len = overlap_len + len(prev) + (len(separator) if overlap_chunk else 0)
                        if prev_joint_len <= self.chunk_overlap:
                            overlap_chunk.insert(0, prev)
                            overlap_len = prev_joint_len
                        else:
                            break
                    current_chunk = overlap_chunk + [split]
                    current_len = overlap_len + len(split) + (len(separator) if len(current_chunk) > 1 else 0)

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks


class EmbeddingService:

    @staticmethod
    def _normalize_user_id(user_id) -> str:
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
        Backward-compatibility layer. Automatically routes single doc uploads
        to the chunk-level indexing pipeline.
        """
        return EmbeddingService.add_document_chunks(
            document_id=document_id,
            user_id=user_id,
            full_text=f"Summary: {summary}\nContent:\n{full_text}",
            category=category,
            doc_type=doc_type
        )

    @staticmethod
    def add_document_chunks(
        document_id: str,
        user_id: int,
        full_text: str,
        category: str,
        doc_type: str,
        extracted_fields: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Splits document text into semantic chunks, prepends document context and extracted fields,
        generates vector embeddings using SOTA BGE model, and stores them in ChromaDB.
        """
        collection = get_chroma_collection()
        model = get_embedding_model()

        if collection is None or model is None:
            logger.warning("ChromaDB or SentenceTransformer unavailable. Skipping vector storage.")
            return False

        uid_str = EmbeddingService._normalize_user_id(user_id)

        try:
            # Delete any existing chunks for this document first
            try:
                collection.delete(where={"document_id": document_id})
            except Exception:
                pass

            # Chunk the document text recursively
            splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
            raw_chunks = splitter.split_text(full_text)
            
            if not raw_chunks:
                logger.warning(f"No text extracted to chunk for document {document_id}.")
                return False

            # Format extracted fields into a flat string for semantic boosting
            fields_str = ""
            if extracted_fields:
                fields_str = ", ".join(
                    f"{k}: {v}"
                    for k, v in extracted_fields.items()
                    if v and not isinstance(v, (dict, list))
                )

            ids = []
            embeddings = []
            metadatas = []
            documents = []

            for idx, chunk_text in enumerate(raw_chunks):
                # Detect section names (heuristic: check if chunk starts with capitalized section header)
                section = "General"
                header_match = re.search(r"^(Skills|Experience|Education|Projects|Summary|Profile|Contact|Publications|Certifications|Interests)\b", chunk_text, re.IGNORECASE)
                if header_match:
                    section = header_match.group(1).title()

                # Upgrade A: Prepend structural metadata and clean extracted fields to every chunk
                metadata_part = f" | Metadata: {fields_str}" if fields_str else ""
                context_prefix = (
                    f"[Document: {doc_type or 'Unknown Document'} | "
                    f"Category: {category or 'Unclassified'}"
                    f"{metadata_part}]\n\n"
                )
                enriched_chunk_text = context_prefix + chunk_text

                chunk_id = f"{document_id}_chunk_{idx}"
                # Generate SOTA BGE embedding (1024-dimensional)
                embedding = model.encode(enriched_chunk_text).tolist()

                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(enriched_chunk_text)
                metadatas.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "user_id": uid_str,
                    "chunk_index": idx,
                    "page_number": 1,
                    "section": section,
                    "category": category or "Unclassified",
                    "document_type": doc_type or "Unknown"
                })

            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            logger.info(f"Indexed document {document_id} as {len(ids)} chunks with SOTA context-prefix + metadata for user {uid_str}.")
            return True
        except Exception as e:
            logger.error(f"Failed to add document chunks to vector store: {str(e)}")
            return False

    @staticmethod
    def delete_document(document_id: str) -> bool:
        """Deletes all chunk vectors of a document from ChromaDB."""
        collection = get_chroma_collection()
        if collection is None:
            return False
        try:
            collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted all vector chunks for document {document_id} from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document from vector store: {str(e)}")
            return False

    @staticmethod
    def clean_query(query: str) -> str:
        """
        Upgrade B: Clean query by stripping common question headers and stopwords
        to keep the vector embedding focused on search keywords.
        """
        # Lowercase and replace non-alphanumeric with spaces (keep letters, numbers, spaces)
        cleaned = query.lower()
        # Strip common search boilerplate
        boilerplate = [
            r"\bwhat\b", r"\bis\b", r"\bmy\b", r"\bthe\b", r"\bshow\b", r"\blist\b",
            r"\bplease\b", r"\bfind\b", r"\blook\b", r"\bup\b", r"\bdetails\b",
            r"\binfo\b", r"\binformation\b", r"\bdocument\b", r"\bof\b", r"\bget\b",
            r"\bgive\b", r"\bme\b", r"\bfiles\b", r"\babout\b", r"\bcan\b", r"\byou\b",
            r"\bhow\b", r"\bwhere\b", r"\bdo\b", r"\bhave\b", r"\bany\b"
        ]
        for pattern in boilerplate:
            cleaned = re.sub(pattern, "", cleaned)
        
        # Clean extra spacing
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned if cleaned else query

    @staticmethod
    def detect_routing_target(query: str) -> Optional[str]:
        """
        Upgrade C: Detect document type keywords in the query to trigger
        dynamic metadata routing (filtering).
        """
        q = query.lower()
        mapping = {
            "pan": "PAN Card",
            "aadhaar": "Aadhaar Card",
            "aadhar": "Aadhaar Card",
            "licence": "Driving Licence",
            "license": "Driving Licence",
            "dl": "Driving Licence",
            "marksheet": "Marksheet",
            "10th": "Class 10 Marksheet",
            "12th": "Class 12 Marksheet",
            "resume": "Resume",
            "cv": "Resume",
            "bank statement": "Bank Statement",
            "electricity": "Electricity Bill",
            "rc": "Vehicle RC"
        }
        for kw, doc_type in mapping.items():
            if kw in q:
                return doc_type
        return None

    @staticmethod
    def search(user_id: int, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        SOTA RAG Retrieval Engine with hybrid routing pipeline:
        1. Clean query of stopwords.
        2. Detect query routing hints and construct target where metadata filters.
        3. Query candidates semantically using BGE 1024-dim model.
        4. Calculate lexical overlap for hybrid scoring.
        5. Re-rank results using a high-capacity BGE Cross-Encoder reranker.
        6. Apply MMR diversity filter.
        """
        collection = get_chroma_collection()
        model = get_embedding_model()

        if collection is None or model is None:
            logger.warning("ChromaDB or embedding model unavailable. Skipping search.")
            return []

        uid_str = EmbeddingService._normalize_user_id(user_id)

        try:
            # Check total chunks count for user
            try:
                existing = collection.get(where={"user_id": uid_str})
                total_user_chunks = len(existing.get("ids", []))
            except Exception:
                total_user_chunks = 0

            if total_user_chunks == 0:
                return []

            # Upgrade B: Clean query to focus semantic embeddings
            cleaned_query = EmbeddingService.clean_query(query)
            logger.info(f"Original Query: '{query}' | Cleaned: '{cleaned_query}'")

            # Upgrade C: Construct dynamic metadata routing filter
            where_clause: Dict[str, Any] = {"user_id": uid_str}
            routing_doc_type = EmbeddingService.detect_routing_target(query)
            if routing_doc_type:
                logger.info(f"Dynamic Routing Triggered: Filtering for document_type = '{routing_doc_type}'")
                # Chroma DB where query filters
                where_clause = {
                    "$and": [
                        {"user_id": uid_str},
                        {"document_type": routing_doc_type}
                    ]
                }

            # Retrieve larger candidate set (top 25) for reranking
            candidate_k = min(25, total_user_chunks)
            query_embedding = model.encode(cleaned_query).tolist()

            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=candidate_k,
                    where=where_clause
                )
            except Exception as e:
                logger.warning(f"Metadata filtered query failed: {e}. Falling back to default search.")
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=candidate_k,
                    where={"user_id": uid_str}
                )

            candidates = []
            if results and results.get("ids") and len(results["ids"][0]) > 0:
                ids = results["ids"][0]
                
                dist_list = results.get("distances")
                distances = dist_list[0] if dist_list is not None else [0.5] * len(ids)
                
                docs_list = results.get("documents")
                documents = docs_list[0] if docs_list is not None else [""] * len(ids)
                
                meta_list = results.get("metadatas")
                metadatas = meta_list[0] if meta_list is not None else [{}] * len(ids)
                
                embed_list = results.get("embeddings")
                embeddings = embed_list[0] if embed_list is not None else None

                # Generate BGE embeddings for candidates if they weren't returned
                if embeddings is None or len(embeddings) == 0:
                    embeddings = [model.encode(doc).tolist() for doc in documents]

                for i in range(len(ids)):
                    similarity = max(0.0, 1.0 - (distances[i] / 2.0)) if distances[i] is not None else 0.5
                    
                    # Lexical Keyword Overlap Score
                    query_tokens = set(re.findall(r'\w+', cleaned_query.lower()))
                    chunk_tokens = re.findall(r'\w+', documents[i].lower())
                    keyword_matches = sum(1 for t in chunk_tokens if t in query_tokens)
                    keyword_score = keyword_matches / len(query_tokens) if query_tokens else 0.0
                    
                    # Combine Vector + Lexical match
                    hybrid_score = (0.7 * similarity) + (0.3 * keyword_score)

                    candidates.append({
                        "document_id": metadatas[i].get("document_id"),
                        "chunk_id": ids[i],
                        "similarity": round(similarity, 4),
                        "hybrid_score": round(hybrid_score, 4),
                        "text": documents[i],
                        "embedding": embeddings[i],
                        "metadata": metadatas[i]
                    })

            if not candidates:
                return []

            # Cross-Encoder Reranking using SOTA reranker model
            cross_encoder = get_cross_encoder()
            if cross_encoder:
                try:
                    pairs = [[query, item["text"]] for item in candidates]
                    rerank_scores = cross_encoder.predict(pairs)
                    for i, score in enumerate(rerank_scores):
                        candidates[i]["rerank_score"] = float(score)
                    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
                    logger.info("SOTA Cross-Encoder reranking applied.")
                except Exception as e:
                    logger.warning(f"SOTA Cross-Encoder reranking failed: {e}. Falling back to hybrid score.")
                    candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
            else:
                candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

            # MMR Diversity Selection
            selected_indices = EmbeddingService._apply_mmr(
                query_embedding=query_embedding,
                candidate_embeddings=[item["embedding"] for item in candidates],
                lambda_param=0.6,
                top_k=min(top_k, len(candidates))
            )

            hits = []
            for idx in selected_indices:
                item = candidates[idx]
                hits.append({
                    "document_id": item["document_id"],
                    "chunk_id": item["chunk_id"],
                    "similarity": item["similarity"],
                    "text": item["text"],
                    "metadata": item["metadata"]
                })

            logger.info(f"SOTA RAG Pipeline: Retrieved {len(hits)} diverse chunk hits.")
            return hits

        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []

    @staticmethod
    def _apply_mmr(
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        lambda_param: float = 0.6,
        top_k: int = 5
    ) -> List[int]:
        if not candidate_embeddings:
            return []

        q = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)

        q_norm = q / np.linalg.norm(q)
        c_norms = np.linalg.norm(candidates, axis=1, keepdims=True)
        c_norms[c_norms == 0] = 1.0
        candidates_norm = candidates / c_norms

        sim_to_query = np.dot(candidates_norm, q_norm)

        selected = []
        remaining = list(range(len(candidate_embeddings)))

        first_idx = int(np.argmax(sim_to_query))
        selected.append(first_idx)
        remaining.remove(first_idx)

        while len(selected) < top_k and remaining:
            best_mmr = -float('inf')
            best_idx = -1

            selected_candidates = candidates_norm[selected]

            for idx in remaining:
                cand = candidates_norm[idx]
                sim_to_selected = np.max(np.dot(selected_candidates, cand))

                mmr_score = (lambda_param * sim_to_query[idx]) - ((1.0 - lambda_param) * sim_to_selected)

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx

            if best_idx == -1:
                break

            selected.append(best_idx)
            remaining.remove(best_idx)

        return selected

    @staticmethod
    def get_all_user_documents(user_id: int) -> List[str]:
        collection = get_chroma_collection()
        if collection is None:
            return []
        uid_str = EmbeddingService._normalize_user_id(user_id)
        try:
            result = collection.get(where={"user_id": uid_str})
            doc_ids = {m.get("document_id") for m in result.get("metadatas", []) if m.get("document_id")}
            return list(doc_ids)
        except Exception as e:
            logger.error(f"Failed to get all user documents: {str(e)}")
            return []
