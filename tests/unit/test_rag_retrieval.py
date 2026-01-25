"""
Unit tests for RAG document retrieval functionality.

Tests query expansion, Qdrant search, and document deduplication.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

# Patch agents.rag module functions directly to avoid LSP issues with @tool decorator
import sys

sys.path.insert(0, "..")
import agents.rag as rag_module

# Import functions directly to test internal logic without @tool decorator
fetch_documents = rag_module.fetch_documents
_generate_expanded_queries = rag_module._generate_expanded_queries
_expand_with_synonyms = rag_module._expand_with_synonyms
_deduplicate_docs = rag_module._deduplicate_docs
_is_complex_query = rag_module._is_complex_query
_decompose_query = rag_module._decompose_query
QUERY_EXPANSION_DICT = rag_module.QUERY_EXPANSION_DICT


def test_expand_with_synonyms_for_program_studi():
    result = _expand_with_synonyms("program studi")
    assert "prodi" in result or "jurusan" in result
    assert "program studi" in result  # Original query should be included


def test_expand_with_synonyms_for_biaya():
    result = _expand_with_synonyms("biaya")
    assert any(term in result for term in ["ukt", "spp", "pendidikan"])


def test_expand_with_synonyms_no_match():
    result = _expand_with_synonyms("random term not in dict")
    assert len(result) == 1
    assert result[0] == "random term not in dict"


def test_is_complex_query_with_conjunctions():
    assert _is_complex_query("Apa biaya dan syarat pendaftaran?")
    assert _is_complex_query("Program studi ATAU jurusan")


def test_is_complex_query_simple():
    assert not _is_complex_query("Apa biaya kuliah?")
    assert not _is_complex_query("Program studi STEI")


def test_decompose_query_with_dan():
    result = _decompose_query("Apa program studi DAN jurusan?")
    result_stripped = [r.strip() for r in result]
    assert "apa program studi" in result_stripped
    assert "jurusan?" in result_stripped


def test_decompose_query_with_atau():
    result = _decompose_query("Informatika ATAU Teknik Elektro")
    result_lower = [r.lower().strip() for r in result]
    assert "informatika" in result_lower or "informatika" in result_lower
    assert "teknik elektro" in result_lower or "teknik elektro" in result_lower


def test_generate_expanded_queries_simple():
    result = _generate_expanded_queries("program studi", num_queries=3)
    assert "program studi" in result
    assert len(result) <= 3


def test_generate_expanded_queries_complex():
    result = _generate_expanded_queries("biaya dan syarat", num_queries=5)
    assert len(result) > 1
    assert "biaya" in " ".join(result).lower()


def test_deduplicate_docs_removes_duplicates():
    doc1 = MagicMock(page_content="STEI ITB has 5 programs")
    doc2 = MagicMock(page_content="STEI ITB has 5 programs")

    docs = [(doc1, 0.90), (doc2, 0.85)]
    result = _deduplicate_docs(docs)

    assert len(result) == 1


def test_deduplicate_docs_preserves_order():
    doc1 = MagicMock(page_content="STEI ITB has 5 programs")
    doc2 = MagicMock(page_content="Tuition is Rp15-25M")

    docs = [(doc1, 0.90), (doc2, 0.92)]
    result = _deduplicate_docs(docs)

    assert len(result) == 2
    assert result[0][1] == 0.92  # Higher score first
    assert result[1][1] == 0.90


@patch("agents.rag._generate_expanded_queries")
def test_fetch_documents_generates_queries(mock_generate):
    mock_generate.return_value = ["program studi STEI", "prodi STEI"]

    with patch("agents.rag.vectorstore.similarity_search_with_score") as mock_search:
        mock_search.return_value = []
        # Use invoke() for StructuredTool
        result = fetch_documents.invoke(
            {"search_query": "program studi STEI", "num_queries": 3}
        )

        mock_generate.assert_called_once_with("program studi STEI", 3)


@patch("agents.rag._generate_expanded_queries")
@patch("agents.rag._deduplicate_docs")
def test_fetch_documents_calls_vectorstore(mock_dedup, mock_generate):
    mock_generate.return_value = ["test query"]
    mock_dedup.side_effect = lambda docs: docs

    # Create a proper mock Document with metadata that can be serialized
    from langchain_core.documents import Document

    mock_doc = Document(page_content="Test content", metadata={"source": "test"})

    with patch("agents.rag.vectorstore.similarity_search_with_score") as mock_search:
        mock_search.return_value = [(mock_doc, 0.95)]
        # Use invoke() for StructuredTool
        result = fetch_documents.invoke(
            {"search_query": "test query", "num_queries": 1}
        )

        data = json.loads(result)
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert data["documents"][0]["content"] == "Test content"


@patch("agents.rag._generate_expanded_queries")
@patch("agents.rag._deduplicate_docs")
def test_fetch_documents_deduplicates_results(mock_dedup, mock_generate):
    mock_generate.return_value = ["query1", "query2"]
    mock_dedup.side_effect = lambda docs: docs

    # Create a proper mock Document with metadata that can be serialized
    from langchain_core.documents import Document

    doc1 = Document(page_content="STEI ITB...", metadata={"source": "test1"})
    doc2 = Document(page_content="STEI ITB...", metadata={"source": "test2"})

    with patch("agents.rag.vectorstore.similarity_search_with_score") as mock_search:
        mock_search.return_value = [(doc1, 0.90), (doc2, 0.85)]
        # Use invoke() for StructuredTool
        fetch_documents.invoke({"search_query": "test", "num_queries": 2})

        mock_dedup.assert_called_once()


def test_fetch_documents_returns_valid_json():
    with patch("agents.rag.vectorstore.similarity_search_with_score") as mock_search:
        with patch("agents.rag._generate_expanded_queries") as mock_generate:
            with patch("agents.rag._deduplicate_docs") as mock_dedup:
                mock_generate.return_value = ["test"]
                mock_dedup.return_value = []
                mock_search.return_value = []

                # Use invoke() for StructuredTool
                result = fetch_documents.invoke(
                    {"search_query": "test", "num_queries": 1}
                )

                data = json.loads(result)
                assert "query_used" in data
                assert "expanded_queries" in data
                assert "documents" in data
                assert isinstance(data["documents"], list)
