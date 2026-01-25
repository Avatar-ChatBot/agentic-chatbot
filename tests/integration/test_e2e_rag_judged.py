"""
Integration tests with LLM-as-judge evaluation.

Uses real Qdrant data and cheap OpenRouter LLM (qwen2.5-72b-instruct)
for automated answer quality evaluation.
"""

import pytest
from unittest.mock import patch
from agents.rag import process_rag


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_simple_question_judged(real_vectorstore, relevance_evaluator):
    """Test RAG with program studi question - LLM-as-judge evaluates relevance."""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        response = process_rag(
            message="Apa program studi di STEI?",
            thread_id="test-thread-simple-judged",
            emotion="neutral",
        )

        # Verify response structure
        assert "answer" in response
        assert "sources" in response

        # Use LLM-as-judge to evaluate relevance
        question = "Apa program studi di STEI?"
        answer = response["answer"]

        evaluation = relevance_evaluator(answer=answer, question=question)
        score = evaluation.get("score", 0.5)
        reasoning = evaluation.get("reasoning", "")

        print(f"\nAnswer: {answer[:150]}...")
        print(f"Relevance Score: {score}")
        print(f"Reasoning: {reasoning}")

        # Assertion: Relevance must be >= 0.7
        assert score >= 0.7, f"Relevance too low: {score}. Reasoning: {reasoning}"


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_fee_question_judged(real_vectorstore, relevance_evaluator):
    """Test RAG with fee question - LLM-as-judge evaluates relevance."""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        response = process_rag(
            message="Berapa biaya kuliah di ITB?",
            thread_id="test-thread-fees-judged",
            emotion="neutral",
        )

        # Verify response structure
        assert "answer" in response
        answer = response["answer"]

        # Use LLM-as-judge to evaluate relevance
        question = "Berapa biaya kuliah di ITB?"
        evaluation = relevance_evaluator(answer=answer, question=question)
        score = evaluation.get("score", 0.5)

        print(f"\nAnswer: {answer[:150]}...")
        print(f"Relevance Score: {score}")

        # Assertion: Relevance must be >= 0.7
        assert score >= 0.7, f"Relevance too low: {score}"


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_with_sources_faithfulness(real_vectorstore, faithfulness_evaluator):
    """Test RAG answer faithfulness to retrieved sources."""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        response = process_rag(
            message="Apa program studi di STEI?",
            thread_id="test-thread-faithfulness",
            emotion="neutral",
        )

        # Verify response structure
        assert "answer" in response
        assert "sources" in response

        # Use LLM-as-judge to evaluate faithfulness (grounded in sources)
        answer = response["answer"]

        # Build context from sources
        if response["sources"]:
            context = "\n\n".join(
                [
                    f"{s.get('title', '')}: {s.get('quote', '')}"
                    for s in response["sources"][:2]
                ]
            )
        else:
            context = "No sources provided"

        evaluation = faithfulness_evaluator(answer=answer, context=context)
        score = evaluation.get("score", 0.5)
        reasoning = evaluation.get("reasoning", "")

        print(f"\nAnswer: {answer[:150]}...")
        print(f"Faithfulness Score: {score}")
        print(f"Reasoning: {reasoning}")

        # Assertion: Faithfulness must be >= 0.7
        assert score >= 0.7, f"Faithfulness too low: {score}. Reasoning: {reasoning}"


@pytest.mark.integration
@pytest.mark.slow
def test_e2e_rag_complex_query_judged(real_vectorstore, relevance_evaluator):
    """Test RAG with complex multi-part question."""
    from agents.rag import vectorstore

    with patch("agents.rag.vectorstore", real_vectorstore):
        # Complex question with conjunction (tests query decomposition)
        response = process_rag(
            message="Apa biaya kuliah dan syarat pendaftaran di ITB?",
            thread_id="test-thread-complex-judged",
            emotion="neutral",
        )

        # Verify response structure
        assert "answer" in response
        answer = response["answer"]

        # Use LLM-as-judge to evaluate relevance
        question = "Apa biaya kuliah dan syarat pendaftaran di ITB?"
        evaluation = relevance_evaluator(answer=answer, question=question)
        score = evaluation.get("score", 0.5)
        reasoning = evaluation.get("reasoning", "")

        print(f"\nAnswer: {answer[:150]}...")
        print(f"Relevance Score: {score}")
        print(f"Reasoning: {reasoning}")

        # Assertion: Relevance must be >= 0.7
        assert score >= 0.7, (
            f"Relevance too low: {score}. Answer may not address all parts of the question."
        )
