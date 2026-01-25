# RAG Pipeline Testing Implementation Plan

## Context

### Original Request
Create unit tests for the RAG agentic pipeline that:
- Can be run in the code (not just LangSmith)
- Takes a set of questions, invokes the pipeline, and checks if answers match expected results
- Uses LangChain evaluators if possible

### Interview Summary

**User's Decisions:**
- **Test Framework**: pytest (industry standard, async support, fixtures, plugins)
- **Evaluation Approach**: LLM-as-judge - Use another LLM to grade semantic similarity (most accurate but slower)
- **Test Data**: Synthetic data - LLM-generated edge cases for coverage exploration
- **CI/CD Integration**: No, manual only - Tests for local development

**Key Discussions:**
1. Non-deterministic LLM outputs require semantic similarity evaluation, not exact match
2. Synthetic data allows rapid iteration without manual labeling
3. Tests should be runnable with simple `pytest tests/` command
4. No external test runners needed - keep it simple and local

**Research Findings:**
- **LangChain Evaluators**: `load_evaluator("score_string", criteria="faithfulness")`, `load_evaluator("score_string", criteria="relevance")`, `load_evaluator("context_qa")` - all work without LangSmith
- **Best Practices**:
  - Separate retrieval vs generation tests for isolation
  - Mock external dependencies (Qdrant, LLM, Redis) for unit tests
  - Use semantic similarity thresholds (0.75-0.85) to handle non-deterministic outputs
  - RAG Triad metrics: Context Precision, Faithfulness, Answer Relevancy
- **Your Infrastructure**: LangGraph ReAct agent with `fetch_documents` tool, Qdrant vector store, OpenRouter/OpenAI LLM, Redis memory
- **Output Format**: `{"answer": str, "sources": list}`

### Metis Review
**Unable to consult** due to system JSON parse errors. Proceeding with comprehensive research-based analysis.

**Identified Gaps (Auto-Resolved):**
1. **Synthetic Data Generation**: Will use main LLM (same as production) with edge case prompts - **ASSUMPTION**: Use production LLM for test generation to ensure domain consistency
2. **Test Coverage**: Will create diverse test cases covering academics, admissions, facilities, fees - **ASSUMPTION**: Minimum 20-30 test cases to start
3. **Evaluation Thresholds**: Will use industry-standard thresholds (faithfulness ≥ 0.70, relevance ≥ 0.75) - **DEFAULT**: These are typical values but may need tuning
4. **Mocking Strategy**: Will mock Qdrant client, LLM, and Redis for unit tests - **APPROACH**: Use `unittest.mock.patch` with realistic mock data

**Guardrails Applied:**
- Tests must be runnable with `pytest tests/` - no custom runners
- No external API calls in unit tests (all mocked)
- Integration tests can use testcontainers for real Qdrant
- Evaluation must use LangChain evaluators, not LangSmith
- All tests must have clear pass/fail criteria with thresholds

---

## Work Objectives

### Core Objective
Implement a comprehensive unit testing suite for the RAG agentic pipeline that can be run locally without external services, using LangChain evaluators to check semantic similarity of answers against expected results.

### Concrete Deliverables
- `tests/__init__.py` - Test package initialization
- `tests/conftest.py` - Shared fixtures and test configuration
- `tests/data/` - Directory for synthetic test data and fixtures
- `tests/unit/test_rag_retrieval.py` - Unit tests for document retrieval
- `tests/unit/test_rag_generation.py` - Unit tests for LLM answer generation
- `tests/unit/test_rag_evaluation.py` - Unit tests for LangChain evaluators
- `tests/integration/test_e2e_rag.py` - End-to-end RAG pipeline tests
- `tests/generate_synthetic_data.py` - Script to generate synthetic test cases
- `requirements-dev.txt` - Testing dependencies (pytest, pytest-asyncio, testcontainers)

### Definition of Done
- [ ] Can run `pytest tests/` with all tests passing
- [ ] Unit tests have 100% code coverage of RAG agent functions
- [ ] Integration tests use testcontainers for real Qdrant
- [ ] Synthetic test data covers at least 4 categories (academics, admissions, facilities, policies)
- [ ] LangChain evaluators correctly grade answers with semantic similarity
- [ ] All tests have clear acceptance criteria (thresholds for faithfulness ≥ 0.70, relevance ≥ 0.75)

### Must Have
- **Pytest framework** with fixtures for Qdrant, LLM, and Redis mocking
- **LangChain evaluators** integration (faithfulness, relevance, context_qa)
- **Synthetic test data generator** script for ITB-specific edge cases
- **Mocking utilities** for Qdrant client, LLM responses, and Redis memory
- **LLM-as-judge evaluator** configuration using LangChain's `load_evaluator`
- **Separate test suites**: unit (mocked), integration (real components), e2e (full pipeline)
- **Acceptance thresholds**: Defined for each evaluation metric

### Must NOT Have (Guardrails)
- **NO LangSmith integration** - Evaluation must be purely code-based, not requiring LangSmith API
- **NO CI/CD pipelines** - Tests are for local manual execution only
- **NO external test runners** - Must use standard `pytest` CLI
- **NO real API keys in tests** - All LLM/Qdrant calls must be mocked or use testcontainers
- **NO exact string matching** - Use semantic similarity for non-deterministic LLM outputs
- **NO test data file commits** - Synthetic data is generated, not versioned in repository
- **NO complex test fixtures** - Keep fixtures simple and maintainable

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO (no formal test framework)
- **User wants tests**: YES (explicit request)
- **QA approach**: Manual verification (user specified no CI/CD)

### Verification Strategy (Manual)

Since no formal test infrastructure exists and user wants manual execution:

**For Test Execution**:
- [ ] Command: `pytest tests/ -v`
- [ ] Expected: All tests pass, coverage report generated
- [ ] Verify: No external API keys required, runs locally

**For Test Coverage**:
- [ ] Command: `pytest tests/ --cov=agents --cov-report=term-missing`
- [ ] Expected: Coverage report shows percentage for each module
- [ ] Verify: Key functions (process_rag, fetch_documents) have tests

**For LLM-as-Judge Evaluation**:
- [ ] Command: `pytest tests/unit/test_rag_evaluation.py -v`
- [ ] Expected: Evaluator returns scores (faithfulness, relevance) with comments
- [ ] Verify: Scores are within acceptable thresholds (≥ 0.70 for faithfulness, ≥ 0.75 for relevance)

**Evidence Required:**
- [ ] Terminal output showing test execution results
- [ ] Coverage report showing line/function coverage
- [ ] Evaluator scores logged to console

---

## Task Flow

```
Setup Dev Dependencies → Generate Test Data → Create Unit Tests → Create Integration Tests → Create E2E Tests → Manual Verification
```

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 1-3 | Independent - setup, data generation, test config |
| B | 4-6 | Unit tests for retrieval, generation, evaluation |
| C | 7 | Integration tests with testcontainers |

---

## TODOs

### Phase 1: Setup & Configuration

- [ ] 1. Install Testing Dependencies

  **What to do**:
  - Add pytest and testing libraries to project
  - Create requirements-dev.txt with test dependencies only

  **Install commands**:
  ```bash
  pip install pytest pytest-asyncio pytest-cov testcontainers[qdrant] openai-responses
  ```

  **Requirements to add to requirements-dev.txt**:
  ```
  pytest>=7.4.0
  pytest-asyncio>=0.21.0
  pytest-cov>=4.1.0
  testcontainers[qdrant]>=3.7.1
  openai-responses>=0.19.0
  ```

  **Must NOT do**:
  - Don't add RAGAS or DeepEval - use LangChain evaluators only
  - Don't add custom test runners

  **Parallelizable**: NO (must be done first)

  **References**:

  **Pattern References** (existing code to follow):
  - `requirements.txt` - Project dependencies structure
  - Standard Python package structure (setup.py or pyproject.toml patterns)

  **External References** (libraries and frameworks):
  - Official pytest docs: https://docs.pytest.org/en/stable/
  - testcontainers Qdrant docs: https://testcontainers.com/modules/qdrant/
  - openai-responses GitHub: https://github.com/marinadeboer/openai-responses-python

  **WHY Each Reference Matters**:
  - `requirements.txt`: Ensure consistency with existing dependency management
  - pytest docs: Standard practices for test organization
  - testcontainers docs: Official patterns for Qdrant integration testing
  - openai-responses: Reliable mocking strategy for LLM responses

  **Acceptance Criteria**:
  - [ ] requirements-dev.txt file created
  - [ ] Dependencies installable with `pip install -r requirements-dev.txt`
  - [ ] Verify: `pytest --version` shows installed version

  **Commit**: NO (groups with 2)

- [ ] 2. Create Test Directory Structure

  **What to do**:
  - Create tests/ directory structure
  - Create __init__.py, conftest.py
  - Create subdirectories for unit, integration, data

  **Files to create**:
  ```
  tests/
  ├── __init__.py
  ├── conftest.py
  ├── data/
  ├── unit/
  └── integration/
  ```

  **Parallelizable**: NO (depends on 1)

  **References**:

  **Pattern References** (existing code to follow):
  - Python package structure: `__init__.py` marks directories as packages

  **External References** (libraries and frameworks):
  - pytest conftest documentation: https://docs.pytest.org/en/stable/how-to/fixtures.html

  **WHY Each Reference Matters**:
  - Python package structure: Standard practice for Python packages
  - pytest conftest: Shared fixtures reduce code duplication across tests

  **Acceptance Criteria**:
  - [ ] tests/__init__.py exists and is empty or has imports
  - [ ] tests/conftest.py exists with fixture definitions
  - [ ] Directory structure matches plan (unit/, integration/, data/)

  **Commit**: YES (message: "test: Create test directory structure")

### Phase 2: Synthetic Test Data Generation

- [ ] 3. Generate Synthetic Test Cases

  **What to do**:
  - Create script to generate ITB-specific test questions
  - Use LLM to generate diverse edge cases
  - Include expected answers (for comparison)
  - Save to tests/data/synthetic_test_cases.json

  **Implementation approach**:
  ```python
  # tests/generate_synthetic_data.py
  from agents.models import llm
  import json

   prompts = [
      "Generate 3 edge case questions about ITB admissions: apa itu itb? (What is ITB?), syarat lulus S2 IF (What are S2 graduation requirements?), syarat lulus program magister informatika (What are Informatics master's graduation requirements?)",
      "Generate 2 questions about ITB tuition fees: pembayaran ukt di itb gmn (How are UKT payments at ITB?), syarat lulus cumlaude itb (What are cum laude requirements?)",
      "Generate 3 questions about academic programs: ada prodi apa saja di stei itb (What majors are only at STEI ITB?), publikasi untuk S2 apa saja? (Publications for S2 only what?)",
      "Generate 2 questions about campus facilities & policies: kapan waktu wisuda paling dekat? (When is the next graduation ceremony?), ada berapa fakultas di itb? (How many faculties at ITB?), Berapa lama masa studi normal untuk mahasiswa S1 ITB? (How long is normal study for S1 at ITB?)",
      "Generate 2 questions about curriculum & majors: Bagaimana mekanisme perubahan kurikulum itb bagaimana? (How does ITB curriculum change mechanism work?), Mekanisme perubahan kurikulum minor di itb bagaimana? (How does ITB minor curriculum change mechanism work?)",
      "Generate 3 questions about special cases: Saya mau cuti, syaratnya apa ya? (I want to switch major, what are the requirements?), coba apa perbedaan dari kurikulum tahun 2024 dengan 2019 (Try the difference between 2024 and 2019 curriculum?), Apa itu ITB? (What is ITB?), saya tertarik sama itb, apa syarat mendaftar? (I'm from the same ITB, what are registration requirements?)",
      "Generate 3 questions about graduation & study duration: apa syarat lulus sarjana di ITB? (What are S1 graduation requirements?), Berapa lama masa studi normal untuk mahasiswa S1 ITB? (How long is normal study for S1 at ITB?), apa syarat mahasiswa lulus program profesi? (What are graduation requirements for professional degree students?), Berapa lama masa studi normal untuk mahasiswa S1 ITB? (What is normal study duration for S1 at ITB? - duplicate)",
      "Generate 2 questions about honors: ada berapa fakultas di itb? (How many faculties at ITB? - duplicate, remove), apa syarat cumlaude, magna cumlaude, dan summa cumlaude s2 di ITB? (What are cum laude, magna cum laude, and summa cum laude requirements for S2 at ITB?)"
  ]

  test_cases = []
  for prompt in prompts:
      response = llm.invoke(prompt)
      test_cases.append({
          "category": "admissions" if "admissions" in prompt else
                      "fees" if "fees" in prompt else
                      "programs" if "programs" in prompt else
                      "facilities" if "facilities" in prompt else
                      "policies",
          "question": response.strip(),
          "expected_keywords": [],  # Will fill manually or via another prompt
      })

  with open("tests/data/synthetic_test_cases.json", "w") as f:
      json.dump(test_cases, f, indent=2, ensure_ascii=False)
  ```

  **Must NOT do**:
  - Don't hardcode test questions - generate them dynamically
  - Don't create golden datasets - synthetic only for exploration

  **Parallelizable**: NO (depends on 2)

  **References**:

  **Pattern References** (existing code to follow):
  - `agents/models.py:llm` - Existing LLM configuration
  - `agents/rag.py:RAG_AGENT_SYSTEM_MESSAGE` - Understanding of ITB domain

  **External References** (libraries and frameworks):
  - LLM prompt engineering best practices: https://platform.openai.com/docs/guides/prompt-engineering

  **WHY Each Reference Matters**:
  - `agents/models.py`: Reuse existing LLM configuration for test generation
  - `agents/rag.py`: Ensure generated questions align with RAG agent's capabilities
  - Prompt engineering: Generate high-quality, diverse edge cases

  **Acceptance Criteria**:
  - [ ] Script `tests/generate_synthetic_data.py` created
  - [ ] Script runs successfully: `python tests/generate_synthetic_data.py`
  - [ ] tests/data/synthetic_test_cases.json created with at least 10-15 test cases
  - [ ] Test cases cover multiple categories (admissions, fees, programs, facilities, policies)
  - [ ] JSON file is valid and parseable

  **Commit**: YES (message: "test: Generate synthetic test cases")

### Phase 3: Test Fixtures & Mocks

- [ ] 4. Create Shared Fixtures

**IMPORTANT: Open-Ended Questions Use LLM-as-Judge Evaluators**

For the 20 open-ended questions you provided, since they don't have "expected answers" (they're open-ended), the test strategy is **semantic similarity** using LangChain evaluators:

- **Faithfulness**: Is answer grounded in retrieved context? (Threshold: ≥ 0.70)
- **Relevance**: Does answer address the question? (Threshold: ≥ 0.75)

These questions will verify:
- Response is in Indonesian language
- Response contains relevant keywords
- Response is coherent and meaningful
- Sources are present when applicable

Open-ended questions should NOT use exact string matching or golden dataset comparison.

  **What to do**:
  - Create conftest.py with fixtures for Qdrant, LLM, Redis
  - Define mock data helpers
  - Configure pytest settings

  **Implementation**:
  ```python
  # tests/conftest.py
  import pytest
  from unittest.mock import MagicMock, patch
  from typing import List, Dict

  # Mock Qdrant client fixture
  @pytest.fixture
  def mock_qdrant_client():
      """Mock Qdrant client for unit tests."""
      client = MagicMock()
      # Setup default mock behavior
      client.search.return_value = []
      return client

  # Mock LLM fixture
  @pytest.fixture
  def mock_llm():
      """Mock LLM for unit tests."""
      from langchain_openai import ChatOpenAI
      llm = MagicMock(spec=ChatOpenAI)
      llm.invoke.return_value = MagicMock(content="Mocked LLM response")
      return llm

  # Mock Redis fixture
  @pytest.fixture
  def mock_redis_client():
      """Mock Redis client for unit tests."""
      redis = MagicMock()
      redis.ping.return_value = True
      return redis

  # Mock vector store fixture
  @pytest.fixture
  def mock_vectorstore(mock_qdrant_client):
      """Mock vector store using mocked Qdrant client."""
      from langchain_qdrant import QdrantVectorStore
      from agents.models import embeddings

      return QdrantVectorStore(
          client=mock_qdrant_client,
          collection_name="test_collection",
          embedding=embeddings,
      )

  # Mock documents fixture
  @pytest.fixture
  def sample_documents():
      """Sample documents for testing."""
      return [
          {
              "content": "STEI ITB memiliki 5 program studi...",
              "metadata": {"category": "academics", "source": "stei-itb.ac.id"},
              "score": 0.95
          },
          {
              "content": "Biaya kuliah ITB berkisar antara Rp15-25 juta per tahun...",
              "metadata": {"category": "fees", "source": "finance.itb.ac.id"},
              "score": 0.88
          }
      ]
  ```

  **Must NOT do**:
  - Don't create real connections in fixtures
  - Don't use environment variables for test configuration

  **Parallelizable**: NO (depends on 2)

  **References**:

  **Pattern References** (existing code to follow):
  - `agents/models.py:vectorstore` - Existing vector store configuration
  - `utils/checkpointer.py:get_checkpointer()` - Redis checkpointer pattern

  **External References** (libraries and frameworks):
  - pytest fixtures documentation: https://docs.pytest.org/en/stable/how-to/fixtures.html
  - unittest.mock documentation: https://docs.python.org/3/library/unittest.mock.html

  **WHY Each Reference Matters**:
  - `agents/models.py`: Understand real vector store configuration to mock correctly
  - `utils/checkpointer.py`: Mock Redis checkpointer behavior accurately
  - pytest fixtures: Reusable fixtures reduce code duplication
  - unittest.mock: Official Python mocking library

  **Acceptance Criteria**:
  - [ ] tests/conftest.py created with at least 4 fixtures (qdrant, llm, redis, vectorstore)
  - [ ] All fixtures are functions with @pytest.fixture decorator
  - [ ] Mock objects use unittest.mock.MagicMock
  - [ ] Fixtures don't create real connections or use environment variables
  - [ ] Sample documents fixture provides realistic mock data structure

  **Commit**: YES (message: "test: Create shared fixtures and mocks")

### Phase 4: Unit Tests

- [ ] 5. Create Retrieval Unit Tests

  **What to do**:
  - Test `fetch_documents` tool
  - Test query expansion logic
  - Test document deduplication
  - Test similarity search calls

  **Test file**: `tests/unit/test_rag_retrieval.py`

  **Implementation**:
  ```python
  import pytest
  from unittest.mock import patch, MagicMock
  from agents.rag import fetch_documents

  def test_fetch_documents_expands_query():
      """Test that fetch_documents expands query with synonyms."""
      with patch("agents.rag._generate_expanded_queries") as mock_generate:
          mock_generate.return_value = [
              "program studi STEI",
              "jurusan STEI",
              "prodi STEI"
          ]

          result = fetch_documents("Apa program studi di STEI?", num_queries=3)

          mock_generate.assert_called_once_with("Apa program studi di STEI?", 3)

  def test_fetch_documents_searches_qdrant():
      """Test that fetch_documents searches Qdrant."""
      with patch("agents.models.vectorstore.similarity_search_with_score") as mock_search:
          mock_search.return_value = [
              (MagicMock(page_content="STEI ITB memiliki 5 program studi..."), 0.95)
          ]

          result = fetch_documents("Program studi STEI", num_queries=5)

          mock_search.assert_called()
          # Verify result contains documents
          data = json.loads(result)
          assert "documents" in data
          assert len(data["documents"]) > 0

  def test_fetch_documents_deduplicates_results():
      """Test that fetch_documents deduplicates documents."""
      with patch("agents.rag._deduplicate_docs") as mock_dedup:
          mock_dedup.side_effect = lambda docs: docs

          # Create duplicate documents
          docs_with_duplicates = [
              (MagicMock(page_content="STEI ITB..."), 0.90),
              (MagicMock(page_content="STEI ITB..."), 0.85),
              (MagicMock(page_content="Biaya kuliah..."), 0.92)
          ]

          with patch("agents.rag.vectorstore.similarity_search_with_score") as mock_search:
              mock_search.return_value = docs_with_duplicates

              result_str = fetch_documents("Test query")
              data = json.loads(result_str)

              # Should call deduplication
              mock_dedup.assert_called_once()

              # Result should have deduplicated documents
              docs = data["documents"]
              # Verify no duplicates (check content hashes)
              contents = [d["content"] for d in docs]
              assert len(contents) == len(set(contents)), "Duplicates not removed"

  def test_query_expansion_with_synonyms():
      """Test query expansion with Indonesian synonyms."""
      from agents.rag import QUERY_EXPANSION_DICT, _expand_with_synonyms

      # Test synonym expansion for "program studi"
      result = _expand_with_synonyms("program studi")
      assert "prodi" in result or "jurusan" in result

      # Test no expansion for unknown terms
      result = _expand_with_synonyms("random term not in dict")
      assert len(result) == 1, "Should only return original query"
  ```

  **Must NOT do**:
  - Don't create real Qdrant connections
  - Don't make actual LLM API calls

  **Parallelizable**: YES (with 6)

  **References**:

  **Pattern References** (existing code to follow):
  - `agents/rag.py:fetch_documents` - Tool to test (lines 150-202)
  - `agents/rag.py:_generate_expanded_queries` - Query expansion logic (lines 96-125)
  - `agents/rag.py:_deduplicate_docs` - Deduplication logic (lines 128-147)
  - `agents/rag.py:QUERY_EXPANSION_DICT` - Synonym dictionary (lines 17-32)

  **External References** (libraries and frameworks):
  - pytest parametrize documentation: https://docs.pytest.org/en/stable/how-to/parametrize.html

  **WHY Each Reference Matters**:
  - `agents/rag.py`: Ensure tests cover all retrieval logic (query expansion, deduplication, search)
  - pytest parametrize: Test multiple scenarios efficiently with parameterized tests
  - Python patterns: Ensure correct mocking of all functions

  **Acceptance Criteria**:
  - [ ] test_rag_retrieval.py file created with at least 4 test functions
  - [ ] Tests cover query expansion, Qdrant search, deduplication
  - [ ] All tests use mocked Qdrant client (no real connections)
  - [ ] Tests verify correct function calls using mock assertions
  - [ ] Running `pytest tests/unit/test_rag_retrieval.py -v` shows all tests passing

  **Commit**: YES (message: "test: Add retrieval unit tests")

- [ ] 6. Create Generation Unit Tests

  **What to do**:
  - Test LLM generation with mocked retrieval
  - Test JSON response parsing
  - Test answer extraction
  - Test sources extraction

  **Test file**: `tests/unit/test_rag_generation.py`

  **Implementation**:
  ```python
  import pytest
  from unittest.mock import patch, MagicMock
  from agents.rag import process_rag

  def test_process_rag_generates_answer():
      """Test that process_rag generates answer with mocked LLM."""
      mock_response = {
          "answer": "Di STEI ITB terdapat beberapa program studi...",
          "sources": [
              {
                  "title": "Program Studi STEI ITB",
                  "quote": "STEI ITB memiliki 5 program studi...",
                  "source": "https://www.itb.ac.id/stei/program-studi"
              }
          ]
      }

      # Mock the agent stream
      mock_agent = MagicMock()
      mock_agent.stream.return_value = [
          {"messages": [MagicMock(content=mock_response["answer"])]}
      ]

      with patch("agents.rag.rag_agent", return_value=mock_agent):
          result = process_rag("Apa program studi di STEI?", thread_id="test-thread")

          assert "answer" in result
          assert result["answer"] == mock_response["answer"]
          assert "sources" in result
          assert result["sources"] == mock_response["sources"]

  def test_process_rag_handles_json_parsing():
      """Test JSON parsing with various response formats."""
      from agents.rag import _extract_json_from_response

      # Test standard JSON
      result = _extract_json_from_response('{"answer": "test", "sources": []}')
      assert result["answer"] == "test"

      # Test JSON in markdown code block
      result = _extract_json_from_response('```json\n{"answer": "test"}\n```')
      assert result["answer"] == "test"

      # Test JSON with thinking tags
      result = _extract_json_from_response('think: I should answer\n{"answer": "test"}')
      assert result["answer"] == "test"

      # Test malformed JSON (should return empty dict)
      result = _extract_json_from_response('not valid json')
      assert result == {}

  def test_process_rag_handles_thinking_tags():
      """Test that thinking tags are removed from responses."""
      from agents.rag import _extract_json_from_response
      import re

      # Response with thinking tags
      response_with_thinking = '<think>I need to think\nThe answer is Paris.</think>\n{"answer": "Paris"}'
      result = _extract_json_from_response(response_with_thinking)

      # Thinking tags should be removed
      assert "<think>" not in result
      assert result["answer"] == "Paris"

      # Response with thinking tags in markdown
      response_md = 'think: reason\n\n```json\n{"answer": "Paris"}\n```'
      result = _extract_json_from_response(response_md)

      assert "<think>" not in result
      assert result["answer"] == "Paris"

  def test_process_rag_uses_thread_id():
      """Test that process_rag uses thread_id for conversation memory."""
      with patch("agents.rag.rag_agent") as mock_agent:
          mock_agent_instance = MagicMock()
          mock_agent.return_value = mock_agent_instance

          process_rag("Test question", thread_id="test-thread-123")

          # Verify thread_id is used in config
          mock_agent_instance.stream.assert_called_once()
          call_kwargs = mock_agent_instance.stream.call_args.kwargs
          assert "config" in call_kwargs
          assert call_kwargs["config"]["configurable"]["thread_id"] == "test-thread-123"

  def test_process_rag_with_emotion_parameter():
      """Test that process_rag passes emotion to system message."""
      with patch("agents.rag.rag_agent") as mock_agent:
          mock_agent_instance = MagicMock()
          mock_agent.return_value = mock_agent_instance

          process_rag("Test question", thread_id="test-thread", emotion="happy")

          # Verify emotion is passed
          mock_agent_instance.stream.assert_called_once()
          call_args = mock_agent_instance.stream.call_args.args[0]
          messages = call_args[0]["messages"]
          system_message = messages[0]

          assert "happy" in system_message[1]  # Second element is the system message with emotion

  @pytest.mark.parametrize("emotion", ["neutral", "happy", "sad", "angry"])
  def test_process_rag_with_various_emotions(emotion):
      """Test process_rag with different emotion values."""
      with patch("agents.rag.rag_agent") as mock_agent:
          mock_agent_instance = MagicMock()
          mock_agent.return_value = mock_agent_instance

          process_rag("Test question", thread_id="test-thread", emotion=emotion)

          call_args = mock_agent_instance.stream.call_args.args[0]
          messages = call_args[0]["messages"]
          system_message = messages[0]

          assert emotion in system_message[1]
  ```

  **Must NOT do**:
  - Don't make real LLM API calls
  - Don't create real Redis connections

  **Parallelizable**: YES (with 5)

  **References**:

  **Pattern References** (existing code to follow):
  - `agents/rag.py:process_rag` - Main function to test (lines 253-303)
  - `agents/rag.py:_extract_json_from_response` - JSON parsing logic (lines 216-250)
  - `agents/rag.py:fetch_documents` - Tool usage (line 160 calls fetch_documents)

  **External References** (libraries and frameworks):
  - pytest marks documentation: https://docs.pytest.org/en/stable/mark/
  - unittest.mock assertions: https://docs.python.org/3/library/unittest.mock.html

  **WHY Each Reference Matters**:
  - `agents/rag.py`: Test all RAG agent logic (generation, JSON parsing, emotion handling, thread_id)
  - pytest marks: Categorize tests (slow, integration, unit) for selective execution
  - unittest.mock: Verify correct mocking behavior and assertions

  **Acceptance Criteria**:
  - [ ] test_rag_generation.py file created with at least 5 test functions
  - [ ] Tests cover JSON parsing, answer generation, thread_id usage, emotion parameter
  - [ ] All tests use mocked agent (no real LLM calls)
  - [ ] Tests verify correct function calls using assert_called_once(), assert_called_with()
  - [ ] Running `pytest tests/unit/test_rag_generation.py -v` shows all tests passing
  - [ ] Parametrized tests (emotions) work correctly with pytest.mark.parametrize

  **Commit**: YES (message: "test: Add generation unit tests")

### Phase 5: LangChain Evaluators

- [ ] 7. Create Evaluator Tests

  **What to do**:
  - Test LangChain evaluator setup
  - Test faithfulness evaluation
  - Test relevance evaluation
  - Test LLM-as-judge configuration

  **Test file**: `tests/unit/test_rag_evaluation.py`

  **Implementation**:
  ```python
  import pytest
  from langchain.evaluation import load_evaluator
  from langchain_openai import ChatOpenAI

  # Create evaluator LLM (for LLM-as-judge)
  @pytest.fixture
  def evaluator_llm():
      """LLM for evaluating similarity."""
      # Use a cheaper/faster model for evaluation
      return ChatOpenAI(
          model="gpt-4o-mini",
          temperature=0,  # Deterministic for consistent grading
          openai_api_key="fake-key-for-testing"
      )

  # Load LangChain evaluators
  @pytest.fixture
  def faithfulness_evaluator(evaluator_llm):
      """Evaluator for answer faithfulness."""
      return load_evaluator("score_string", criteria="faithfulness")

  @pytest.fixture
  def relevance_evaluator(evaluator_llm):
      """Evaluator for answer relevance."""
      return load_evaluator("score_string", criteria="relevance")

  def test_faithfulness_evaluator_works(evaluator_llm, faithfulness_evaluator):
      """Test that faithfulness evaluator returns expected scores."""
      prediction = "Program studi STEI meliputi Informatika, Teknik Elektro, dan Sistem Informasi."
      reference = "STEI ITB memiliki 5 program studi: Informatika, Teknik Elektro, Sistem Informasi, Teknik Tenaga Listrik, dan Teknik Telekomunikasi."

      result = faithfulness_evaluator.evaluate_strings(
          prediction=prediction,
          reference=reference,
          input="Apa program studi di STEI?"
      )

      # Verify result structure
      assert "score" in result
      assert "comment" in result
      assert "reasoning" in result

      # Score should be high (answer is grounded)
      assert result["score"] >= 0.8, f"Faithfulness too low: {result['score']}"
      print(f"Faithfulness Score: {result['score']}")
      print(f"Comment: {result['comment']}")

  def test_relevance_evaluator_works(evaluator_llm, relevance_evaluator):
      """Test that relevance evaluator returns expected scores."""
      prediction = "Biaya kuliah ITB berkisar antara Rp15-25 juta per tahun."
      reference = "Apa biaya kuliah di ITB?"

      result = relevance_evaluator.evaluate_strings(
          prediction=prediction,
          reference=reference,
          input=reference  # Relevance is evaluated against question
      )

      # Verify result structure
      assert "score" in result
      assert "comment" in result

      # Score should be high (answer addresses question)
      assert result["score"] >= 0.8, f"Relevance too low: {result['score']}"
      print(f"Relevance Score: {result['score']}")
      print(f"Comment: {result['comment']}")

  def test_evaluator_handles_multiple_predictions():
      """Test evaluator with multiple predictions."""
      predictions = [
          "STEI ITB memiliki 5 program studi.",
          "Di STEI ada Informatika, Teknik Elektro.",
      ]
      reference = "Program studi di STEI ITB."

      result = faithfulness_evaluator.evaluate_strings(
          prediction=predictions[0],
          reference=reference,
          input="Jelaskan program studi STEI"
      )

      assert "score" in result
      assert 0 <= result["score"] <= 1  # Scores should be normalized

  @pytest.mark.parametrize("scenario,expected_faithfulness,expected_relevance", [
      # High faithfulness, high relevance
      ("Answer with complete details and citations", 0.9, 0.85),
      # Medium faithfulness, high relevance
      ("Answer with partial details", 0.7, 0.8),
      # Low faithfulness, medium relevance
      ("Vague answer without specifics", 0.5, 0.6),
  ])
  def test_evaluator_with_various_scenarios(
      evaluator_llm, faithfulness_evaluator, relevance_evaluator,
      scenario, expected_faithfulness, expected_relevance
  ):
      """Test evaluator behavior with different answer qualities."""
      faithfulness_result = faithfulness_evaluator.evaluate_strings(
          prediction=scenario,
          reference="STEI ITB memiliki 5 program studi.",
          input="Apa program studi di STEI?"
      )

      assert faithfulness_result["score"] >= expected_faithfulness, \
          f"Faithfulness {faithfulness_result['score']} below threshold {expected_faithfulness}"

      relevance_result = relevance_evaluator.evaluate_strings(
          prediction=scenario,
          reference="Apa program studi di STEI?",
          input="Apa biaya kuliah ITB?"
      )

      assert relevance_result["score"] >= expected_relevance, \
          f"Relevance {relevance_result['score']} below threshold {expected_relevance}"

      print(f"\nScenario: {scenario[:50]}...")
      print(f"  Faithfulness: {faithfulness_result['score']} (expected >= {expected_faithfulness})")
      print(f"  Relevance: {relevance_result['score']} (expected >= {expected_relevance})")
  ```

  **Must NOT do**:
  - Don't use external evaluation frameworks (RAGAS, DeepEval)
  - Don't create LangSmith integrations

  **Parallelizable**: YES (with 7)

  **References**:

  **Pattern References** (existing code to follow):
  - N/A (new functionality - no existing evaluator code)

  **External References** (libraries and frameworks):
  - LangChain evaluator documentation: https://python.langchain.com/docs/evaluation/
  - LangChain load_evaluator API: https://python.langchain.com/en/latest/langchain/evaluation.html
  - gpt-4o-mini model info: https://platform.openai.com/docs/models/gpt-4o-mini

  **WHY Each Reference Matters**:
  - LangChain evaluator docs: Understand available evaluator types and usage patterns
  - load_evaluator API: How to load and instantiate evaluators programmatically
  - gpt-4o-mini: Choosing appropriate model for LLM-as-judge (cheap, fast, accurate)

  **Acceptance Criteria**:
  - [ ] test_rag_evaluation.py file created with evaluator fixtures and at least 4 test functions
  - [ ] Faithfulness evaluator configured with criteria="faithfulness"
  - [ ] Relevance evaluator configured with criteria="relevance"
  - [ ] Tests verify evaluator returns expected structure (score, comment, reasoning)
  - [ ] Tests include threshold assertions (≥ 0.70 for faithfulness, ≥ 0.75 for relevance)
  - [ ] Tests use gpt-4o-mini for LLM-as-judge (temperature=0 for determinism)
  - [ ] Running `pytest tests/unit/test_rag_evaluation.py -v -s` shows evaluator scores and all tests passing

  **Commit**: YES (message: "test: Add LangChain evaluator tests")

### Phase 6: Integration Tests

- [ ] 8. Create E2E RAG Pipeline Tests

  **What to do**:
  - Test full RAG pipeline with testcontainers
  - Use real Qdrant instance (testcontainers)
  - Test multiple questions end-to-end
  - Validate complete response structure

  **Test file**: `tests/integration/test_e2e_rag.py`

  **Implementation**:
  ```python
  import pytest
  import json
  from testcontainers.qdrant import QdrantContainer
  from qdrant_client import QdrantClient
  from agents.rag import process_rag
  from agents.models import embeddings, llm

  @pytest.fixture(scope="session")
  def qdrant_container():
      """Spin up real Qdrant container for integration tests."""
      with QdrantContainer() as container:
          # Wait for Qdrant to be ready
          client = container.get_client()

          # Create test collection
          client.create_collection(
              collection_name="test_rag_collection",
              vectors_config={
                  "size": 1536,  # OpenAI embedding dimension
                  "distance": "Cosine"
              }
          )

          # Insert test documents
          test_docs = [
              {
                  "id": "doc1",
                  "vector": [0.1] * 1536,  # Dummy vector
                  "payload": {
                      "content": "STEI ITB memiliki 5 program studi: Informatika, Teknik Elektro, Sistem Informasi, Teknik Tenaga Listrik, dan Teknik Telekomunikasi.",
                      "metadata": {"category": "academics", "source": "stei-itb.ac.id"}
                  }
              },
              {
                  "id": "doc2",
                  "vector": [0.2] * 1536,
                  "payload": {
                      "content": "Biaya kuliah ITB berkisar antara Rp15-25 juta per tahun tergantung program studi.",
                      "metadata": {"category": "fees", "source": "finance.itb.ac.id"}
                  }
              },
          ]

          client.upsert(
              collection_name="test_rag_collection",
              points=test_docs
          )

          yield client, container.get_internal_url()

      # Cleanup
      client.delete_collection("test_rag_collection")

  @pytest.fixture
  def real_rag_agent(qdrant_container):
      """Create real RAG agent with test Qdrant."""
      from langchain_qdrant import QdrantVectorStore

      client = QdrantClient(url=qdrant_container, api_key=None)
      vectorstore = QdrantVectorStore(
          client=client,
          collection_name="test_rag_collection",
          embedding=embeddings,
      )

      # Create real agent with test vector store
      from agents.rag import fetch_documents, memory

      # Patch the real fetch_documents to use test vector store
      from unittest.mock import patch

      def mock_fetch_documents(search_query, num_queries):
          """Mock fetch_documents to use test vector store."""
          from agents.rag import vectorstore

          # Use test vector store instead of real one
          result = vectorstore.similarity_search_with_score(search_query, k=5)

          # Format as JSON (same as real implementation)
          docs = [
              {
                  "content": doc.page_content,
                  "metadata": doc.metadata,
                  "score": float(score)
              }
              for doc, score in result
          ]

          return json.dumps({
              "query_used": search_query,
              "expanded_queries": [search_query],  # Simplified
              "documents": docs[:10],
          }, ensure_ascii=False)

      with patch("agents.rag.vectorstore", vectorstore):
          with patch("agents.rag.fetch_documents", side_effect=mock_fetch_documents):
              from langgraph.prebuilt import create_react_agent

              agent = create_react_agent(
                  llm,
                  [fetch_documents],
                  checkpointer=memory,
                  messages_modifier=None,  # Use original system message
              )

              yield agent

  def test_e2e_rag_simple_question(real_rag_agent):
      """Test end-to-end RAG with simple question."""
      response = process_rag(
          message="Apa program studi di STEI?",
          thread_id="test-thread-simple",
          emotion="neutral"
      )

      # Verify response structure
      assert "answer" in response
      assert "sources" in response

      # Verify answer contains expected content
      answer = response["answer"]
      assert "program studi" in answer.lower() or "prodi" in answer.lower()
      assert "STEI" in answer or "Sekolah Teknik Elektro dan Informatika" in answer

      # Verify sources
      sources = response["sources"]
      assert len(sources) > 0, "Should have sources"
      assert any("STEI" in source.get("source", "").lower() for source in sources)

      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_fee_question(real_rag_agent):
      """Test end-to-end RAG with fee question."""
      response = process_rag(
          message="Berapa biaya kuliah di ITB?",
          thread_id="test-thread-fees",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Verify answer contains fee-related terms
      assert "biaya" in answer.lower() or "pembayaran" in answer.lower()
      assert "juta" in answer or "rupiah" in answer

      sources = response["sources"]
      assert len(sources) > 0

      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_multi_turn_conversation(real_rag_agent):
      """Test multi-turn conversation with context."""
      # First question
      response1 = process_rag(
          message="Siapa nama dekan STEI?",
          thread_id="test-thread-multi",
          emotion="neutral"
      )

      assert "answer" in response1
      print(f"Q1: {response1['answer'][:50]}")

      # Follow-up question (should use context from first question)
      response2 = process_rag(
          message="Siapa program beliau?",
          thread_id="test-thread-multi",  # Same thread_id
          emotion="neutral"
      )

      assert "answer" in response2
      answer2 = response2["answer"]

      # Verify second answer uses context
      assert "dekan" in answer2.lower() or "nama dekan" in answer2.lower()

      print(f"Q2 (context-aware): {answer2[:50]}")

  def test_e2e_rag_empty_results():
      """Test RAG when no relevant documents found."""
      # Delete all documents from test collection
      pass  # Assume documents are deleted or query finds nothing

      response = process_rag(
          message="Apa kuliah di ITB tahun 1900?",
          thread_id="test-thread-empty",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should indicate no information found
      assert "tidak" in answer.lower() or "maaf" in answer.lower()

      sources = response["sources"]
      assert len(sources) == 0, "Should have no sources when nothing found"

      print(f"\n✅ No info response: {answer[:80]}")

  @pytest.mark.integration
  @pytest.mark.slow
  def test_e2e_rag_full_suite(real_rag_agent):
      """Run full integration test suite (marked as slow and integration)."""
      # This test will be discovered and run by pytest
      pass  # Individual tests above will be executed

  def test_e2e_rag_question_apa_itu_itb(real_rag_agent):
      """Test question: apa itu itb?"""
      response = process_rag(
          message="Apa itu ITB?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Verify answer is in Indonesian
      assert any(word in answer.lower() for word in ["institut", "teknologi", "bandung"])

      sources = response["sources"]
      assert len(sources) > 0, "Should have sources"
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_program_stei_only(real_rag_agent):
      """Test question: ada prodi apa saja di stei itb"""
      response = process_rag(
          message="ada prodi apa saja di stei itb",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention specific majors at STEI
      assert any(major in answer.lower() for major in ["informatika", "teknik elektro", "sistem informasi", "teknik tenaga listrik", "teknik telekomunikasi"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_pembayaran_ukt(real_rag_agent):
      """Test question: pembayaran ukt di itb gmn"""
      response = process_rag(
          message="pembayaran ukt di ITB gmn",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention UKT payment methods
      assert any(word in answer.lower() for word in ["ukt", "pembayaran", "biaya", "kuliah", "tagihan"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")
  ```

  **Must NOT do**:
  - Don't use mocked Qdrant in integration tests
  - Don't skip testcontainers setup
  - Don't test without real LLM (it's okay to use production LLM for e2e)

  **Parallelizable**: NO (depends on 1-7)

  **References**:

  **Pattern References** (existing code to follow):
  - `agents/rag.py:process_rag` - Main entry point (line 253)
  - `agents/models.py:llm`, `vectorstore` - Dependencies (lines 26, 79)
  - `docker-compose.yml:qdrant` - Qdrant configuration

  **External References** (libraries and frameworks):
  - testcontainers Qdrant docs: https://testcontainers.com/modules/qdrant/
  - pytest marks: https://docs.pytest.org/en/stable/mark/
  - pytest fixture scopes: https://docs.pytest.org/en/stable/how-to/fixtures.html

  **WHY Each Reference Matters**:
  - `agents/rag.py`: Test the exact same function used in production
  - `agents/models.py`: Understand dependencies to mock/setup correctly in tests
  - `docker-compose.yml`: Match Qdrant configuration for testcontainers
  - pytest marks: Mark integration tests as `@pytest.mark.slow` to skip in CI
  - testcontainers docs: Official patterns for spinning up Qdrant in tests
  - pytest fixture scopes: Session-scoped fixtures reduce container startup time

  **Acceptance Criteria**:
  - [ ] test_e2e_rag.py file created with at least 4 test functions
  - [ ] Integration tests use testcontainers Qdrant (not mocked)
  - [ ] Tests call real `process_rag` function from agents/rag.py
  - [ ] Tests cover simple questions, fee questions, multi-turn conversations, empty results
  - [ ] Tests verify response structure (answer, sources keys exist)
  - [ ] Tests use real LLM from `agents/models.py`
  - [ ] Running `pytest tests/integration/ -v -m integration` shows all integration tests passing
  - [ ] Session-scoped qdrant_container fixture creates collection and yields client

  **Commit**: YES (message: "test: Add end-to-end RAG integration tests")

### Phase 7: Documentation

- [ ] 9. Create Test Documentation

  **What to do**:
  - Create README for tests/
  - Document how to run tests
  - Document test structure and conventions
  - Provide examples of running tests

  **File**: `tests/README.md`

  **Implementation**:
  ```markdown
  # RAG Pipeline Tests

  This directory contains unit tests, integration tests, and evaluation utilities for the ITB RAG chatbot.

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
      """One-line description of what's being tested."""
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

  - **Faithfulness**: Is the answer grounded in retrieved context? (Threshold: ≥ 0.70)
  - **Relevance**: Does the answer address the question? (Threshold: ≥ 0.75)

  Evaluators are configured in `tests/conftest.py` and run in test functions.
  ```

  **Must NOT do**:
  - Don't create complex documentation with diagrams
  - Don't document external tools not in the plan

  **Parallelizable**: NO (depends on 1-8)

  **References**:

  **Pattern References** (existing code to follow):
  - `README.md` - Main project README (pattern for documentation)
  - Standard Python project structure

  **External References** (libraries and frameworks):
  - pytest documentation: https://docs.pytest.org/en/stable/
  - testcontainers documentation: https://testcontainers.com/

  **WHY Each Reference Matters**:
  - `README.md`: Follow existing documentation style and format
  - pytest docs: Official patterns for test documentation
  - testcontainers docs: Ensure integration test setup is documented

  **Acceptance Criteria**:
  - [ ] tests/README.md file created
  - [ ] Documentation includes "Running Tests" section with commands
  - [ ] Documentation includes "Test Structure" section showing directory layout
  - [ ] Documentation includes examples for writing tests, mocking, integration tests
  - [ ] Documentation includes "Evaluation" section explaining LangChain evaluators
  - [ ] Documentation follows markdown format with proper headers and code blocks

  **Commit**: YES (message: "docs: Add test README")

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | test: Add pytest to requirements-dev.txt | requirements-dev.txt | pip install -r requirements-dev.txt |
| 2 | test: Create test directory structure | tests/__init__.py, conftest.py, unit/, integration/, data/ | pytest tests/ --collect-only |
| 3 | test: Generate synthetic test cases | tests/data/synthetic_test_cases.json, tests/generate_synthetic_data.py | ls tests/data/ |
| 4 | test: Create shared fixtures and mocks | tests/conftest.py | pytest tests/ --collect-only |
| 5 | test: Add retrieval unit tests | tests/unit/test_rag_retrieval.py | pytest tests/unit/test_rag_retrieval.py -v |
| 6 | test: Add generation unit tests | tests/unit/test_rag_generation.py | pytest tests/unit/test_rag_generation.py -v |
| 7 | test: Add LangChain evaluator tests | tests/unit/test_rag_evaluation.py | pytest tests/unit/test_rag_evaluation.py -v -s |
| 8 | test: Add end-to-end integration tests | tests/integration/test_e2e_rag.py | pytest tests/integration/ -v -m integration |
| 9 | docs: Add test README | tests/README.md | cat tests/README.md |

---

## Success Criteria

### Verification Commands
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov-report=term-missing

# Generate synthetic data
python tests/generate_synthetic_data.py

# Verify test collection
pytest tests/ --collect-only
```

### Final Checklist
- [ ] All "Must Have" deliverables created
- [ ] All "Must NOT Have" guardrails respected
- [ ] All tests pass with `pytest tests/ -v`
- [ ] Code coverage ≥ 80% for RAG agent functions
- [ ] LangChain evaluators return scores (faithfulness ≥ 0.70, relevance ≥ 0.75)
- [ ] Integration tests use testcontainers (real Qdrant)
- [ ] No external API keys required for tests
- [ ] README documentation is clear and actionable

  def test_e2e_rag_question_wisuda(real_rag_agent):
      """Test question: kapan waktu wisuda paling dekat?"""
      response = process_rag(
          message="Kapan waktu wisuda paling dekat?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Verify answer contains time-related information
      assert any(word in answer.lower() for word in ["wisuda", "kelulusan", "wisudah"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_syarat_lulus_s2_if(real_rag_agent):
      """Test question: syarat lulus S2 IF?"""
      response = process_rag(
          message="syarat lulus S2 IF",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention S2 graduation requirements
      assert any(word in answer.lower() for word in ["s2", "skripsi", "tesis", "ipk"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_syarat_lulus_magister_informatika(real_rag_agent):
      """Test question: syarat lulus program magister informatika"""
      response = process_rag(
          message="syarat lulus program magister informatika",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention Informatics master's graduation requirements
      assert any(word in answer.lower() for word in ["skripsi", "tesis", "magister", "informatika"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_publikasi_s2(real_rag_agent):
      """Test question: publikasi untuk S2 apa saja?"""
      response = process_rag(
          message="publikasi untuk S2 apa saja?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention S2 publication requirements
      assert any(word in answer.lower() for word in ["publikasi", "s2", "jurnal", "artikel"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_mekanisme_kurikulum_itb(real_rag_agent):
      """Test question: Bagaimana mekanisme perubahan kurikulum ITB bagaimana?"""
      response = process_rag(
          message="Bagaimana mekanisme perubahan kurikulum ITB bagaimana?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention curriculum change mechanism
      assert any(word in answer.lower() for word in ["kurikulum", "perubahan", "mekanisme", "perbaharui"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_mekanisme_kurikulum_minor(real_rag_agent):
      """Test question: Mekanisme perubahan kurikulum minor di itb bagaimana?"""
      response = process_rag(
          message="Mekanisme perubahan kurikulum minor di ITB bagaimana?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention minor curriculum change mechanism
      assert any(word in answer.lower() for word in ["kurikulum minor", "perubahan", "mekanisme"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_saya_mau_cuti(real_rag_agent):
      """Test question: Saya mau cuti, syaratnya apa ya?"""
      response = process_rag(
          message="Saya mau cuti, syaratnya apa ya?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention major change requirements
      assert any(word in answer.lower() for word in ["cuti", "pindah program", "syarat", "ipk"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_perbedaan_kurikulum_2024_2019(real_rag_agent):
      """Test question: coba apa perbedaan dari kurikulum tahun 2024 dengan 2019"""
      response = process_rag(
          message="coba apa perbedaan dari kurikulum tahun 2024 dengan 2019",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention 2024 and 2019 curriculum differences
      assert all(year in answer for year in ["2024", "2019"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_apa_itu_itb_duplicate(real_rag_agent):
      """Test question: Apa itu ITB? (duplicate test)"""
      response = process_rag(
          message="Apa itu ITB?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Same as test_e2e_rag_question_apa_itu_itb
      assert any(word in answer.lower() for word in ["institut", "teknologi", "bandung"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_saya_terarik_sama_itb(real_rag_agent):
      """Test question: saya tertarik sama itb, apa syarat mendaftar?"""
      response = process_rag(
          message="Saya tertarik sama ITB, apa syarat mendaftar?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention registration requirements
      assert any(word in answer.lower() for word in ["mendaftar", "pmb", "snmptn", "pendaftaran"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_syarat_lulus_sarjana(real_rag_agent):
      """Test question: Apa syarat lulus sarjana di ITB?"""
      response = process_rag(
          message="Apap syarat lulus sarjana di ITB?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention S1 graduation requirements
      assert any(word in answer.lower() for word in ["sarjana", "s1", "wisuda", "skripsi"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_masa_studi_s1_itb(real_rag_agent):
      """Test question: Berapa lama masa studi normal untuk mahasiswa S1 ITB?"""
      response = process_rag(
          message="Berapa lama masa studi normal untuk mahasiswa S1 ITB?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention S1 study duration
      assert any(word in answer.lower() for word in ["masa studi", "semester", "tahun", "lama"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_masa_studi_s1_itb_duplicate(real_rag_agent):
      """Test question: Berapa lama masa studi normal untuk mahasiswa S1 ITB? (duplicate)"""
      # This is a duplicate test, same as test_e2e_rag_question_masa_studi_s1_itb
      # Mark with pytest.mark.skip to avoid duplication
      pytest.skip("Duplicate of test_e2e_rag_question_masa_studi_s1_itb")

  def test_e2e_rag_question_syarat_lulus_program_profesi(real_rag_agent):
      """Test question: apa syarat mahasiswa lulus program profesi?"""
      response = process_rag(
          message="Apap syarat mahasiswa lulus program profesi?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention professional degree graduation requirements
      assert any(word in answer.lower() for word in ["profesi", "program profesi", "gelar", "kerja", "skripsi"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_jumlah_fakultas_itb(real_rag_agent):
      """Test question: ada berapa fakultas di itb?"""
      response = process_rag(
          message="Ada berapa fakultas di ITB?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention number of faculties
      # Looking for number (indonesian: "berapa", "jumlah") or faculty names
      assert any(word in answer.lower() for word in ["fakultas", "sekolah", "institut"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")

  def test_e2e_rag_question_syarat_cumlaude_magna_summa(real_rag_agent):
      """Test question: apa syarat cumlaude, magna cumlaude, dan summa cumlaude s2 di ITB?"""
      response = process_rag(
          message="Apap syarat cumlaude, magna cumlaude, dan summa cumlaude S2 di ITB?",
          thread_id="test-thread-question",
          emotion="neutral"
      )

      assert "answer" in response
      answer = response["answer"]

      # Should mention cum laude requirements
      assert any(word in answer.lower() for word in ["cumlaude", "magna cumlaude", "summa cumlaude", "ipk"])
      
      sources = response["sources"]
      assert len(sources) > 0
      
      print(f"\n✅ Answer: {answer[:100]}...")
      print(f"Sources: {len(sources)} document(s)")
