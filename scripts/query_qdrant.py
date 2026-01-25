#!/usr/bin/env python3
"""Simple script to query Qdrant directly for debugging purposes.

Usage:
    python scripts/query_qdrant.py "your search query"
    python scripts/query_qdrant.py "biaya kuliah" --top 10
    python scripts/query_qdrant.py "beasiswa" --collection informasi-umum-itb
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import warnings

load_dotenv()

# Add parent directory to path for importing agents module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.embedding_utils import format_query_for_embedding, OpenRouterEmbeddings

# Suppress warnings
warnings.filterwarnings("ignore", message=".*Api key is used with an insecure connection.*")


def get_embeddings(embedding_provider: str = "openai"):
    """Get embeddings instance based on provider.

    Args:
        embedding_provider: Either "openai" or "qwen"

    NOTE: Uses custom OpenRouterEmbeddings for qwen to bypass langchain-openai bug
    where it tokenizes input client-side, breaking embeddings.
    """
    embedding_provider = embedding_provider.lower()

    if embedding_provider == "qwen":
        embedding_model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for qwen embeddings")
        # Use custom OpenRouterEmbeddings class to avoid OpenAI library tokenization bug
        return OpenRouterEmbeddings(
            model=embedding_model,
            api_key=openrouter_api_key,
        )
    return OpenAIEmbeddings(model="text-embedding-3-large")
       

def get_vectorstore(collection_name: str, embedding_provider: str = "openai"):
    """Get Qdrant vectorstore instance.

    Args:
        collection_name: Name of the Qdrant collection
        embedding_provider: Either "openai" or "qwen"
    """
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if qdrant_api_key:
        qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        qdrant_client = QdrantClient(url=qdrant_url)

    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=get_embeddings(embedding_provider),
    ), qdrant_client


def main():
    parser = argparse.ArgumentParser(description="Query Qdrant vector database")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top", "-k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--collection", "-c", default=None,
                        help="Collection name (default: informasi-umum-itb for openai, informasi-umum-itb-qwen for qwen)")
    parser.add_argument("--embedding-provider", "-e", choices=["openai", "qwen"], default="openai",
                        help="Embedding provider (default: openai)")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON")
    parser.add_argument("--info", action="store_true", help="Show collection info only")

    args = parser.parse_args()

    # Set default collection based on embedding provider
    if args.collection is None:
        args.collection = "informasi-umum-itb-qwen3" if args.embedding_provider == "qwen" else "informasi-umum-itb"

    vectorstore, qdrant_client = get_vectorstore(args.collection, args.embedding_provider)

    # Show collection info
    if args.info:
        info = qdrant_client.get_collection(args.collection)
        print(f"Collection: {args.collection}")
        print(f"Vectors count: {info.points_count}")
        print(f"Vector size: {info.config.params.vectors.size}")
        print(f"Distance: {info.config.params.vectors.distance}")
        return

    # Perform search
    print(f"\n{'='*60}")
    print(f"Query: {args.query}")
    print(f"Collection: {args.collection}")
    print(f"Embedding: {args.embedding_provider}")
    print(f"{'='*60}\n")

    # Format query with instruction if using Qwen3-Embedding
    search_query = args.query
    if args.embedding_provider == "qwen":
        embedding_model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        search_query = format_query_for_embedding(args.query, model_name=embedding_model)
        print(f"[DEBUG] Formatted query for Qwen3:\n  {search_query[:150]}{'...' if len(search_query) > 150 else ''}\n")

    results = vectorstore.similarity_search_with_score(search_query, k=args.top)

    if args.raw:
        output = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in results
        ]
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # Pretty print results
    for i, (doc, score) in enumerate(results, 1):
        print(f"[{i}] Score: {score:.4f}")
        print(f"Content: {doc.page_content[:200]}{'...' if len(doc.page_content) > 200 else ''}")
        print(f"Metadata: {json.dumps(doc.metadata, ensure_ascii=False)}")
        print(f"{'-'*60}\n")


if __name__ == "__main__":
    main()
