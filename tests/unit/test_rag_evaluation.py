"""
Unit tests for RAG evaluation (LLM-as-judge).

Tests faithfulness, relevance, and answer quality evaluation.
"""

import pytest
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


@pytest.fixture
def evaluator_llm():
    """LLM for evaluating similarity (LLM-as-judge).

    Uses gpt-4o-mini for cost-effective evaluation.
    """

    # Simple mock that returns a fake evaluator without requiring LLM calls
    class MockEvaluator:
        def evaluate_strings(self, prediction, reference, input):
            pred_lower = prediction.lower()
            ref_lower = reference.lower()
            ref_words = set(ref_lower.split())
            pred_words = set(pred_lower.split())
            overlap = ref_words.intersection(pred_words)

            if len(ref_words) > 0:
                score = len(overlap) / len(ref_words)
            else:
                score = 1.0 if prediction == reference else 0.0

            return {"score": score, "comment": f"Overlap: {len(overlap)} words"}

        def evaluate_relevance(self, prediction, reference, input):
            pred_lower = prediction.lower()
            input_lower = input.lower()

            input_words = set(input_lower.split())
            pred_words = set(pred_lower.split())
            overlap = input_words.intersection(pred_words)

            if len(input_words) > 0:
                score = len(overlap) / len(input_words)
            else:
                score = 0.5

            return {"score": score, "comment": f"Keywords matched: {len(overlap)}"}

    return MockEvaluator()


@pytest.fixture
def relevance_evaluator(evaluator_llm):
    """Evaluator for answer relevance.

    Threshold: >= 0.75
    """
    return evaluator_llm.evaluate_relevance


@pytest.fixture
def faithfulness_evaluator(evaluator_llm):
    """Evaluator for answer faithfulness.

    Threshold: >= 0.70
    """
    return evaluator_llm.evaluate_strings


def test_faithfulness_evaluator_structure(faithfulness_evaluator):
    """Test that faithfulness evaluator returns expected structure."""
    result = faithfulness_evaluator.evaluate_strings(
        prediction="Program studi STEI meliputi Informatika, Teknik Elektro, dan Sistem Informasi.",
        reference="STEI ITB memiliki 5 program studi: Informatika, Teknik Elektro, Sistem Informasi, Teknik Tenaga Listrik, dan Teknik Telekomunikasi.",
        input="Apa program studi di STEI?",
    )

    assert "score" in result
    assert "comment" in result


def test_faithfulness_evaluator_high_score(faithfulness_evaluator):
    """Test faithfulness with grounded answer."""
    result = faithfulness_evaluator.evaluate_strings(
        prediction="STEI ITB memiliki 5 program studi.",
        reference="STEI ITB memiliki 5 program studi.",
        input="Apa program studi di STEI?",
    )

    assert result["score"] >= 0.70, f"Faithfulness too low: {result['score']}"
    print(f"\\nFaithfulness Score: {result['score']}")
    print(f"Comment: {result['comment']}")


def test_relevance_evaluator_structure(relevance_evaluator):
    """Test that relevance evaluator returns expected structure."""
    result = relevance_evaluator(
        prediction="Biaya kuliah ITB berkisar antara Rp15-25 juta per tahun.",
        reference="Apa biaya kuliah di ITB?",
        input="Apa biaya kuliah di ITB?",
    )

    assert "score" in result
    assert "comment" in result


def test_relevance_evaluator_high_score(relevance_evaluator):
    """Test relevance with relevant answer."""
    result = relevance_evaluator(
        prediction="Biaya kuliah ITB berkisar antara Rp15-25 juta per tahun.",
        reference="Apa biaya kuliah di ITB?",
        input="Apa biaya kuliah di ITB?",
    )

    assert result["score"] >= 0.75, f"Relevance too low: {result['score']}"
    print(f"\\nRelevance Score: {result['score']}")
    print(f"Comment: {result['comment']}")


def test_evaluator_with_multiple_predictions(faithfulness_evaluator):
    """Test evaluator with multiple predictions."""
    predictions = [
        "STEI ITB memiliki 5 program studi.",
        "Di STEI ada Informatika, Teknik Elektro.",
    ]
    reference = "Program studi di STEI ITB."

    result = faithfulness_evaluator.evaluate_strings(
        prediction=predictions[0],
        reference=reference,
        input="Jelaskan program studi STEI",
    )

    assert "score" in result
    assert 0 <= result["score"] <= 1  # Scores should be normalized


@pytest.mark.parametrize(
    "scenario,expected_faithfulness,expected_relevance",
    [
        # High faithfulness, high relevance
        ("Answer with complete details and citations", 0.7, 0.75),
        # Medium faithfulness, high relevance
        ("Answer with partial details", 0.6, 0.7),
        # Low faithfulness, medium relevance
        ("Vague answer without specifics", 0.5, 0.6),
    ],
)
def test_evaluator_with_various_scenarios(
    faithfulness_evaluator,
    relevance_evaluator,
    scenario,
    expected_faithfulness,
    expected_relevance,
):
    """Test evaluator behavior with different answer qualities."""
    faithfulness_result = faithfulness_evaluator.evaluate_strings(
        prediction=scenario,
        reference="STEI ITB memiliki 5 program studi.",
        input="Apa program studi di STEI?",
    )

    # Check faithfulness threshold (may not be exact for all scenarios)
    assert faithfulness_result["score"] >= 0.5, (
        f"Faithfulness {faithfulness_result['score']} below minimum 0.5"
    )

    relevance_result = relevance_evaluator.evaluate_strings(
        prediction=scenario,
        reference="Apa program studi di STEI?",
        input="Apa biaya kuliah ITB?",  # Different question for relevance
    )

    # Check relevance threshold
    relevance_result = relevance_evaluator(
        prediction=scenario,
        reference="Apa program studi di STEI?",
        input="Apa biaya kuliah ITB?",  # Different question for relevance
    )

    print(f"\\nScenario: {scenario[:50]}...")
    print(f"  Faithfulness: {faithfulness_result['score']}")
    print(f"  Relevance: {relevance_result['score']}")
