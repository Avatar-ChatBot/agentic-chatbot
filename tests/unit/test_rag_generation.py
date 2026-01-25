"""
Unit tests for RAG generation functionality.

Tests LLM generation, JSON parsing, emotion handling, and thread_id usage.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agents.rag import process_rag, _extract_json_from_response, get_rag_agent
from langchain_core.messages import AIMessage


def test_extract_json_standard_json():
    """Test JSON extraction from standard JSON format."""
    result = _extract_json_from_response('{"answer": "test", "sources": []}')
    assert result["answer"] == "test"
    assert result["sources"] == []


def test_extract_json_markdown_json():
    """Test JSON extraction from markdown code blocks."""
    result = _extract_json_from_response('```json\n{"answer": "test"}\n```')
    assert result["answer"] == "test"


def test_extract_json_with_thinking_tags():
    """Test JSON extraction with thinking tags removed."""
    response = 'think: I should answer\n{"answer": "test"}'
    result = _extract_json_from_response(response)
    assert "think" not in result
    assert result["answer"] == "test"


def test_extract_json_malformed():
    """Test that malformed JSON returns empty dict."""
    result = _extract_json_from_response("not valid json")
    assert result == {}


def test_extract_json_partial_json():
    """Test extraction when response contains JSON + extra text."""
    response = 'Here is the answer: {"answer": "Paris", "sources": []}'
    result = _extract_json_from_response(response)
    assert result["answer"] == "Paris"


@patch("agents.rag.get_rag_agent")
def test_process_rag_generates_answer(mock_get_agent):
    """Test that process_rag generates answer with mocked agent."""
    mock_agent_instance = MagicMock()
    mock_get_agent.return_value = mock_agent_instance

    # Mock the stream to return a final message
    mock_msg = AIMessage(
        content='{"answer": "Di STEI ITB terdapat program studi Informatika...", "sources": []}'
    )
    mock_agent_instance.stream.return_value = [{"messages": [mock_msg]}]

    result = process_rag("Apa program studi di STEI?", thread_id="test-thread")

    assert "answer" in result
    assert "STEI" in result["answer"]
    assert "sources" in result


@patch("agents.rag.get_rag_agent")
def test_process_rag_uses_thread_id(mock_get_agent):
    """Test that process_rag uses thread_id for conversation memory."""
    mock_agent_instance = MagicMock()
    mock_get_agent.return_value = mock_agent_instance
    mock_agent_instance.stream.return_value = []

    process_rag("Test question", thread_id="test-thread-123")

    # Verify stream was called
    mock_agent_instance.stream.assert_called_once()

    call_kwargs = mock_agent_instance.stream.call_args.kwargs
    assert "config" in call_kwargs
    assert call_kwargs["config"]["configurable"]["thread_id"] == "test-thread-123"


@patch("agents.rag.get_rag_agent")
def test_process_rag_passes_emotion(mock_agent):
    """Test that process_rag passes emotion to system message."""
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    mock_agent_instance.stream.return_value = []

    process_rag("Test question", thread_id="test-thread", emotion="happy")

    call_args = mock_agent_instance.stream.call_args.args[0]
    messages = call_args["messages"]

    # System message should include emotion
    assert len(messages) == 2
    assert messages[0][0] == "system"
    assert "happy" in messages[0][1]


@pytest.mark.parametrize("emotion", ["neutral", "happy", "sad", "angry"])
@patch("agents.rag.get_rag_agent")
def test_process_rag_with_various_emotions(mock_agent, emotion):
    """Test process_rag with different emotion values."""
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    mock_agent_instance.stream.return_value = []

    process_rag("Test question", thread_id="test-thread", emotion=emotion)

    call_args = mock_agent_instance.stream.call_args.args[0]
    messages = call_args["messages"]
    system_message = messages[0]

    assert emotion in system_message[1]


@patch("agents.rag.get_rag_agent")
def test_process_rag_fallback_for_non_json(mock_agent):
    """Test that process_rag provides fallback for non-JSON responses."""
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance

    # Return a plain text response (no JSON)
    mock_msg = AIMessage(content="Here is the answer to your question.")
    mock_agent_instance.stream.return_value = [{"messages": [mock_msg]}]

    result = process_rag("Test question", thread_id="test-thread")

    # Should return fallback answer
    assert "answer" in result
    assert result["sources"] == []
    assert "answer" in result["answer"]


@patch("agents.rag.get_rag_agent")
def test_process_rag_handles_thinking_tags_in_response(mock_agent):
    """Test that thinking tags are removed from final answer."""
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance

    # Response with thinking tags
    response_with_think = (
        'think: need to check database\n{"answer": "Paris", "sources": []}'
    )
    mock_msg = AIMessage(content=response_with_think)
    mock_agent_instance.stream.return_value = [{"messages": [mock_msg]}]

    result = process_rag("Test question", thread_id="test-thread")

    # Thinking tags should be removed from final answer
    assert "think" not in result["answer"].lower()
    assert "Paris" in result["answer"]
