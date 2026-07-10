from app.services.embedding_service import EmbeddingService
import json

def test():
    user_id = 1
    query = "skills in resume"
    print(f"Searching for: '{query}'...")
    
    hits = EmbeddingService.search(user_id=user_id, query=query, top_k=6)
    print(f"Found {len(hits)} hits:")
    for hit in hits:
        print(f"- Doc: {hit['document_id']} | Similarity: {hit['similarity']} | Section: {hit['metadata'].get('section')} | Snippet: {hit['text'][:100]}...")

if __name__ == "__main__":
    test()
