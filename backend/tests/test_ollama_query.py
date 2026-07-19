"""
Integration test for RAGPipeline query against the local test database.
Uses the conftest.py SQLite database.
Mocks out the vector search to run instantly without downloading large models.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

import pytest
from unittest.mock import patch
from app.services.rag_pipeline import RAGPipeline


def test_rag_query_returns_answer(db):
    """
    RAGPipeline.answer_query should always return a structured response
    even when the vault is empty (falls back to local rules engine).
    """
    # Patch the EmbeddingService search method to return empty hits instantly
    # so we don't trigger BGE model downloads on the main thread during tests
    with patch("app.services.embedding_service.EmbeddingService.search", return_value=[]):
        result = RAGPipeline.answer_query(
            db=db,
            user_id=999,  # Non-existent user — vault will be empty, triggers empty vault block
            question="What documents do I have?",
            history=[]
        )

        assert isinstance(result, dict), "Expected a dict response"
        assert "answer" in result, "Expected 'answer' key in response"
        assert isinstance(result["answer"], str), "Answer should be a string"
        assert len(result["answer"]) > 0, "Answer should not be empty"
        assert "citations" in result, "Expected 'citations' key in response"
        assert isinstance(result["citations"], list), "Citations should be a list"
        retrieval_method = result.get("retrieval_method", "")
        assert retrieval_method, "Expected a non-empty retrieval_method"

        print(f"\n[RAG Test] Retrieval Method: {retrieval_method}")
        print(f"[RAG Test] Answer length: {len(result['answer'])} chars")
        print(f"[RAG Test] Citations: {len(result['citations'])}")


def test_rag_query_with_history(db):
    """
    RAGPipeline.answer_query should handle multi-turn history gracefully.
    """
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you with your documents?"},
    ]
    with patch("app.services.embedding_service.EmbeddingService.search", return_value=[]):
        result = RAGPipeline.answer_query(
            db=db,
            user_id=999,
            question="Show me my documents",
            history=history,
        )
        assert isinstance(result.get("answer"), str)
        assert len(result["answer"]) > 0
