# RAG Pipeline Tests

This directory contains unit tests, integration tests, and evaluation utilities for ITB RAG chatbot.

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Unit Tests Only (Fast)
```bash
pytest tests/unit/ -v
```

### Run Integration Tests Only (Slower, requires Docker)
```bash
pytest tests/integration/ -v -m integration
```

### Run with Coverage Report
```bash
pytest tests/ --cov=agents --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── data/                            # Test data and synthetic cases
│   └── synthetic_test_cases.json
├── unit/                            # Fast unit tests (mocked dependencies)
│   ├── test_rag_retrieval.py
│   ├── test_rag_generation.py
│   └── test_rag_evaluation.py
└── integration/                     # E2E tests with real components
    └── test_e2e_rag.py
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import patch, MagicMock

def test_feature_name():
    """One-line description of what\"s being tested."""
    # Arrange
    mock_dependency = MagicMock()
    
    # Act
    result = function_under_test(mock_dependency)
    
    # Assert
    assert result == expected_value
    mock_dependency.assert_called_once()
```

### Mocking External Dependencies

Unit tests use `@patch` and `MagicMock` to avoid real API calls:

```python
from unittest.mock import patch

@patch("agents.models.vectorstore")
def test_with_mocked_vectorstore():
    # Test logic without real Qdrant connection
    pass
```

### Integration Tests

Integration tests use testcontainers for real Qdrant:

```python
import pytest
from testcontainers.qdrant import QdrantContainer

@pytest.fixture(scope="session")
def qdrant_container():
    with QdrantContainer() as qdrant:
        yield qdrant.get_client()
```

## Evaluation

Tests use LangChain evaluators to measure semantic similarity:

- **Faithfulness**: Is answer grounded in retrieved context? (Threshold: >= 0.70)
- **Relevance**: Does answer address the question? (Threshold: >= 0.75)

Evaluators are configured in `tests/conftest.py` and run in test functions.

## Test Categories

- **Retrieval Tests**: Test document fetching, query expansion, deduplication
- **Generation Tests**: Test LLM generation, JSON parsing, thread_id usage
- **Evaluation Tests**: Test LangChain evaluator setup and scoring
- **Integration Tests**: Full end-to-end pipeline testing with real Qdrant

## Dependencies

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Test dependencies include:
- pytest: Test framework
- pytest-asyncio: Async support
- pytest-cov: Coverage reporting
- testcontainers[qdrant]: Qdrant container for integration tests
- openai-responses: OpenAI mocking for tests

## Notes

- Unit tests use mocked dependencies (Qdrant, LLM, Redis)
- Integration tests require Docker running for testcontainers
- Evaluation tests use gpt-4o-mini as LLM-as-judge
- Tests can be marked with `@pytest.mark.slow` to skip during CI
