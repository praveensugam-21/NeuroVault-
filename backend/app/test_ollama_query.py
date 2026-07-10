import json
from app.services.rag_pipeline import RAGPipeline
from app.database import SessionLocal

def test_query():
    db = SessionLocal()
    try:
        user_id = 1
        question = "what skills do I have in my resume?"
        print(f"Sending test query: '{question}'...")
        
        result = RAGPipeline.answer_query(
            db=db,
            user_id=user_id,
            question=question,
            history=[]
        )
        
        print("\n============================================================")
        print("🤖 OLLAMA CHATGPT-LIKE RESPONSE:")
        print("============================================================\n")
        print(result.get("answer"))
        print("\n" + "=" * 60)
        print(f"Retrieval Method: {result.get('retrieval_method')}")
        print(f"Citations Count:  {len(result.get('citations', []))}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error during test query: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_query()
