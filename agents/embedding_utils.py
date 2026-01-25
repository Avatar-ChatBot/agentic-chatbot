"""
Embedding utilities for instruction-aware models like Qwen3-Embedding.

Qwen3-Embedding models support instruction-aware embeddings which can improve
retrieval performance by 1-5% according to official documentation.

Reference: https://github.com/QwenLM/Qwen3-Embedding

NOTE: The langchain-openai OpenAIEmbeddings class has a bug where it tokenizes
input client-side before sending to non-OpenAI providers, breaking embeddings.
This module provides a custom embedding class that calls OpenRouter directly.
"""

import os
from typing import List, Optional
import requests
import numpy as np
from langchain_core.embeddings import Embeddings
from dotenv import load_dotenv

load_dotenv()


# Default task instruction for RAG/search scenarios
DEFAULT_RAG_INSTRUCTION = "Given a web search query, retrieve relevant passages that answer the query"

# Models that support instruction-aware embeddings
INSTRUCTION_AWARE_MODELS = [
    "qwen3-embedding",
    "qwen/qwen3-embedding",
]


def get_detailed_instruct(task_description: str, query: str) -> str:
    """Format query with instruction for Qwen3-Embedding.

    This follows the official format from Qwen3-Embedding documentation.

    Args:
        task_description: Task description (e.g., "Given a web search query...")
        query: The actual search query

    Returns:
        Formatted string with instruction prefix

    Example:
        >>> get_detailed_instruct("Search for relevant passages", "What is ITB?")
        'Instruct: Search for relevant passages\\nQuery:What is ITB?'
    """
    return f'Instruct: {task_description}\nQuery:{query}'


def format_query_for_embedding(
    query: str,
    instruction: Optional[str] = None,
    model_name: str = "qwen/qwen3-embedding-8b"
) -> str:
    """Format a query string with instruction if the model supports it.

    Args:
        query: The search query
        instruction: Optional custom instruction (uses default if None and model is instruction-aware)
        model_name: The embedding model name

    Returns:
        Formatted query string (with instruction for instruction-aware models, or plain query otherwise)

    Example:
        >>> format_query_for_embedding("biaya kuliah ITB")
        'Instruct: Given a web search query, retrieve relevant passages that answer the query\\nQuery:biaya kuliah ITB'
    """
    if should_use_instructions(model_name):
        task_instruction = instruction or DEFAULT_RAG_INSTRUCTION
        return get_detailed_instruct(task_instruction, query)
    return query


def should_use_instructions(model_name: str) -> bool:
    """Check if a model supports and should use instructions.

    Args:
        model_name: The embedding model name

    Returns:
        True if model is instruction-aware (Qwen3-Embedding series)
    """
    model_name_lower = model_name.lower()
    return any(model in model_name_lower for model in INSTRUCTION_AWARE_MODELS)


class OpenRouterEmbeddings(Embeddings):
    """Custom Embeddings class that calls OpenRouter API directly.

    This bypasses the langchain-openai OpenAIEmbeddings bug where it tokenizes
    input client-side before sending to non-OpenAI providers.

    Usage:
        embeddings = OpenRouterEmbeddings(model="qwen/qwen3-embedding-8b")
        vector = embeddings.embed_query("search text")
    """

    def __init__(
        self,
        model: str = "qwen/qwen3-embedding-8b",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """Initialize OpenRouter embeddings.

        Args:
            model: The model name (e.g., "qwen/qwen3-embedding-8b")
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: Base URL for the API
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key must be provided or set in OPENROUTER_API_KEY environment variable")
        self.base_url = base_url

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts by calling OpenRouter API directly."""
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "ITB Chatbot",
        }

        data = {
            "input": texts,
            "model": self.model,
        }

        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        return [item["embedding"] for item in result["data"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents.

        Args:
            texts: List of document texts

        Returns:
            List of embedding vectors
        """
        return self._embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a query text.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        return self._embed_texts([text])[0]
