import json
from app.database import SessionLocal
from app.models.document import Document
from app.services.embedding_service import get_chroma_collection

def inspect():
    collection = get_chroma_collection()
    if collection is None:
        print("ChromaDB is unavailable.")
        return

    try:
        # Fetch all chunks
        results = collection.get()
        ids = results.get("ids", [])
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])

        print(f"\n============================================================")
        print(f"📊 CHROMADB CHUNK-LEVEL INDEX: {len(ids)} CHUNKS FOUND")
        print(f"============================================================\n")

        for i in range(min(10, len(ids))):
            print(f"Vector ID:  {ids[i]}")
            print(f"   ├─ Doc ID:      {metadatas[i].get('document_id')}")
            print(f"   ├─ Section:     {metadatas[i].get('section')}")
            print(f"   ├─ Chunk Index: {metadatas[i].get('chunk_index')}")
            print(f"   └─ Snippet:")
            # print first 150 chars of chunk text
            snippet = documents[i].replace("\n", " ")
            print(f"      \"{snippet[:150]}...\"")
            print("-" * 60)

        if len(ids) > 10:
            print(f"... and {len(ids) - 10} more chunks.")

    except Exception as e:
        print(f"Error querying ChromaDB: {e}")

if __name__ == "__main__":
    inspect()
