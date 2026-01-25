"""
Pytest configuration and shared fixtures for RAG testing.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for unit tests."""
    client = MagicMock()
    client.search.return_value = []
    client.recommend.return_value = []
    client.count.return_value = MagicMock(count=0)
    return client


@pytest.fixture
def mock_vectorstore():
    """Mock QdrantVectorStore for unit tests."""
    vs = MagicMock()
    vs.similarity_search_with_score.return_value = []
    vs.similarity_search.return_value = []
    return vs


@pytest.fixture
def mock_llm():
    """Mock LLM for unit tests."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content="Mocked LLM response", response_metadata={}
    )
    return llm


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit tests."""
    redis = MagicMock()
    redis.ping.return_value = True
    redis.get.return_value = None
    redis.set.return_value = True
    return redis


@pytest.fixture
def sample_documents():
    """Sample documents for testing.

    Returns:
        List of document dictionaries with content, metadata, and score.
    """
    return [
        {
            "content": "STEI ITB memiliki 5 program studi: Informatika, Teknik Elektro, Sistem Informasi, Teknik Tenaga Listrik, dan Teknik Telekomunikasi.",
            "metadata": {"category": "academics", "source": "stei-itb.ac.id"},
            "score": 0.95,
        },
        {
            "content": "Biaya kuliah ITB berkisar antara Rp15-25 juta per tahun tergantung program studi dan kelompok UKT.",
            "metadata": {"category": "fees", "source": "finance.itb.ac.id"},
            "score": 0.88,
        },
        {
            "content": "Syarat lulus S1 ITB: menyelesaikan 144 SKS, IPK minimal 2.00, lulus Tugas Akhir, dan memenuhi beban SKS setiap semester.",
            "metadata": {"category": "academics", "source": "akademik.itb.ac.id"},
            "score": 0.92,
        },
    ]


@pytest.fixture
def sample_qdrant_points():
    """Sample Qdrant points for testing.

    Returns:
        List of point dictionaries with vector, payload, and id.
    """
    return [
        {
            "id": "doc1",
            "vector": [0.1] * 1536,
            "payload": {
                "page_content": "STEI ITB memiliki 5 program studi...",
                "metadata": {"category": "academics", "source": "stei-itb.ac.id"},
            },
        },
        {
            "id": "doc2",
            "vector": [0.2] * 1536,
            "payload": {
                "page_content": "Biaya kuliah ITB berkisar antara Rp15-25 juta...",
                "metadata": {"category": "fees", "source": "finance.itb.ac.id"},
            },
        },
    ]


@pytest.fixture
def mock_retrieval_result():
    """Mock retrieval result for testing.

    Returns:
        JSON string with mock documents.
    """
    import json

    return json.dumps(
        {
            "query_used": "program studi STEI",
            "expanded_queries": ["program studi STEI", "jurusan STEI", "prodi STEI"],
            "documents": [
                {
                    "content": "STEI ITB memiliki 5 program studi...",
                    "metadata": {"category": "academics", "source": "stei-itb.ac.id"},
                    "score": 0.95,
                }
            ],
        },
        ensure_ascii=False,
    )


@pytest.fixture
def evaluator_llm():
    """LLM for evaluating similarity (LLM-as-judge).

    Uses gpt-4o-mini for cost-effective evaluation.
    """
    from langchain_openai import ChatOpenAI
    import os

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,  # Deterministic for consistent grading
        api_key=os.getenv("OPENAI_API_KEY", "fake-key-for-testing"),
    )


@pytest.fixture
def real_vectorstore():
    """Use existing Qdrant with real ITB data.

    Connects to running Qdrant instance and uses real ITB collection.
    Skips if Qdrant is not running or collection doesn't exist.
    """
    from qdrant_client import QdrantClient
    from langchain_qdrant import QdrantVectorStore
    from agents.models import embeddings
    import os

    # Get configuration from environment
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb")

    # Initialize client
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)

    # Check if Qdrant is running and collection exists
    try:
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]

        if collection_name not in collection_names:
            pytest.skip(
                f"Qdrant collection '{collection_name}' not found. "
                f"Available: {collection_names}. Start docker-compose first."
            )
    except Exception as e:
        pytest.skip(
            f"Cannot connect to Qdrant at {qdrant_url}: {e}. "
            "Start docker-compose first."
        )

    # Create vector store
    vs = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )

    return vs


@pytest.fixture
def qa_evaluator_llm():
    """Cheap LLM for evaluating RAG answers (LLM-as-judge).

    Uses OpenRouter with qwen2.5-72b-instruct for cost-effective evaluation.
    """
    import os
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model="qwen/qwen2.5-72b-instruct",
        temperature=0,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        timeout=60,
    )


@pytest.fixture
def relevance_evaluator(qa_evaluator_llm):
    """Manual relevance evaluator using cheap LLM.

    Returns a function that evaluates if answer addresses the question.
    Uses qa_evaluator_llm (qwen2.5-72b-instruct).

    Threshold: >= 0.7
    """

    def evaluate(answer: str, question: str) -> dict:
        """Evaluate answer relevance to question."""
        prompt = f"""Rate the relevance of the following answer to the question on a scale of 0 to 1.

Question: {question}
Answer: {answer}

Provide ONLY a JSON with this format:
{{"score": <float between 0 and 1>, "reasoning": "<brief explanation>"}}"""

        response = qa_evaluator_llm.invoke(prompt)

        import json
        import re

        # Extract JSON from response
        json_match = re.search(r"\{.*?\}", response.content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except:
                pass

        # Default fallback
        return {"score": 0.5, "reasoning": "Failed to parse evaluation"}

    return evaluate


@pytest.fixture
def faithfulness_evaluator(qa_evaluator_llm):
    """Manual faithfulness evaluator using cheap LLM.

    Returns a function that evaluates if answer is grounded in context.
    Uses qa_evaluator_llm (qwen2.5-72b-instruct).

    Threshold: >= 0.7
    """

    def evaluate(answer: str, context: str) -> dict:
        """Evaluate answer faithfulness to context."""
        prompt = f"""Rate how faithful the following answer is to the provided context on a scale of 0 to 1.
Faithfulness means: The answer should be directly supported by the context, not hallucinated.

Context: {context}
Answer: {answer}

Provide ONLY a JSON with this format:
{{"score": <float between 0 and 1>, "reasoning": "<brief explanation>"}}"""

        response = qa_evaluator_llm.invoke(prompt)

        import json
        import re

        # Extract JSON from response
        json_match = re.search(r"\{.*?\}", response.content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except:
                pass

        # Default fallback
        return {"score": 0.5, "reasoning": "Failed to parse evaluation"}

    return evaluate


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (slow, requires Docker)",
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (skipped in CI by default)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, mocked dependencies)"
    )
