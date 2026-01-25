"""
End-to-end integration tests for RAG pipeline using real Qdrant instance.

Tests against real ITB collection (informasi-umum-itb) with full pipeline.
"""

import pytest
from unittest.mock import patch
from agents.rag import process_rag


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_simple_question(real_vectorstore):
    """Test end-to-end RAG with simple question."""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        response = process_rag(
            message="Apa program studi di STEI?",
            thread_id="test-thread-simple",
            emotion="neutral",
        )

        # Verify response structure
        assert "answer" in response
        assert "sources" in response

        # Verify answer contains expected content
        answer = response["answer"]
        assert "program studi" in answer.lower() or "prodi" in answer.lower()

        print(f"\nAnswer: {answer[:100]}...")


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_fee_question(real_vectorstore):
    """Test end-to-end RAG with fee question."""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        response = process_rag(
            message="Berapa biaya kuliah di ITB?",
            thread_id="test-thread-fees",
            emotion="neutral",
        )

        assert "answer" in response
        answer = response["answer"]

        # Verify answer contains fee-related terms
        assert "biaya" in answer.lower() or "pembayaran" in answer.lower()

        print(f"\nAnswer: {answer[:100]}...")


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_apa_itu_itb(real_vectorstore):
    """Test question: Apa itu ITB?"""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        response = process_rag(
            message="Apa itu ITB?",
            thread_id="test-thread-question",
            emotion="neutral",
        )

        assert "answer" in response
        answer = response["answer"]

        # Verify answer is in Indonesian
        assert any(
            word in answer.lower() for word in ["institut", "teknologi", "bandung"]
        )

        print(f"\nAnswer: {answer[:100]}...")
