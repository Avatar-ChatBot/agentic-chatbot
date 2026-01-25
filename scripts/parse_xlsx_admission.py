#!/usr/bin/env python3
"""
CLI tool to parse ITB information Excel files and upload to Qdrant.

This script parses ITB admission information from Excel files using
Gemini 2.0 Flash for natural language conversion, then uploads to Qdrant.

Usage:
    python scripts/parse_xlsx_admission.py --upload-to-qdrant
    python scripts/parse_xlsx_admission.py --from-cache --upload-to-qdrant
    python scripts/parse_xlsx_admission.py --list-cache
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add project root and scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def upload_to_qdrant(
    documents: list[dict],
    batch_size: int = 50,
    embedding_provider: str = "openai",
    collection_name: str | None = None,
) -> bool:
    """
    Embed and upload documents to Qdrant.

    Args:
        documents: List of documents to embed and upload
        batch_size: Batch size for upload
        embedding_provider: Either "openai" or "qwen"
        collection_name: Custom collection name (auto-selected if not provided)

    Uses the same configuration as agents/models.py:
    - OpenAI: text-embedding-3-large, collection "informasi-umum-itb"
    - Qwen: qwen/qwen3-embedding-8b, collection "informasi-umum-itb-qwen3"
    """
    from dotenv import load_dotenv

    load_dotenv()

    # Import Qdrant and embeddings
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient
        from langchain_core.documents import Document
    except ImportError as e:
        print(f"Error: Required packages are missing: {e}")
        print("Run: pip install langchain-openai langchain-qdrant qdrant-client python-dotenv")
        return False

    # Get configuration from environment
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    # Normalize embedding provider
    embedding_provider = embedding_provider.lower()

    # Set collection name and embedding based on provider
    if embedding_provider == "qwen":
        # Use custom collection if provided, otherwise use default
        if collection_name is None:
            collection_name = "informasi-umum-itb-qwen3"
        embedding_model = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        if not openrouter_api_key:
            print("Error: OPENROUTER_API_KEY environment variable is required for Qwen embeddings")
            return False

        embeddings = OpenAIEmbeddings(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            model=embedding_model,
            dimensions=1024,  # Explicitly set dimension for qwen3-embedding-8b
        )
        print(f"  Using Qwen embedding: {embedding_model}")
    else:  # openai (default)
        # Use custom collection if provided, otherwise use default
        if collection_name is None:
            collection_name = "informasi-umum-itb"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        print("  Using OpenAI embedding: text-embedding-3-large")

    # Initialize Qdrant client
    if qdrant_api_key:
        qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        qdrant_client = QdrantClient(url=qdrant_url)

    print(f"  Qdrant URL: {qdrant_url}")
    print(f"  Collection: {collection_name}")

    # Check if collection exists
    try:
        collections = qdrant_client.get_collections()
        existing_collections = [col.name for col in collections.collections]

        if collection_name not in existing_collections:
            print(f"  Warning: Collection '{collection_name}' does not exist")
            print(f"  Creating collection '{collection_name}'...")

            # Get embedding dimension
            test_embedding = embeddings.embed_query("test")
            dimension = len(test_embedding)

            from qdrant_client.models import Distance, VectorParams
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            print(f"  Created collection with dimension {dimension}")
        else:
            collection_info = qdrant_client.get_collection(collection_name)
            print(f"  Existing collection points: {collection_info.points_count}")
    except Exception as e:
        print(f"  Error checking/creating collection: {e}")
        return False

    # Initialize vector store
    vectorstore = QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embeddings,
    )

    # Convert documents to LangChain Document format
    langchain_docs: list[Document] = []
    for doc in documents:
        if isinstance(doc, dict):
            langchain_docs.append(
                Document(
                    page_content=doc.get("page_content", doc.get("content", "")),
                    metadata=doc.get("metadata", {}),
                )
            )
        else:
            # Already a Document object
            langchain_docs.append(doc)

    print(f"  Uploading {len(langchain_docs)} documents in batches of {batch_size}...")

    # Upload in batches
    total = len(langchain_docs)
    try:
        for i in range(0, total, batch_size):
            batch = langchain_docs[i : i + batch_size]
            vectorstore.add_documents(batch)

            progress = min(i + batch_size, total)
            pct = progress / total * 100
            print(f"    Progress: {progress}/{total} ({pct:.1f}%)")

        # Verify upload
        collection_info = qdrant_client.get_collection(collection_name)
        print("  Upload complete!")
        print(f"  Collection now has {collection_info.points_count} points")

        return True

    except Exception as e:
        print(f"  Error uploading documents: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> None:
    """Main entry point."""
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Parse ITB information Excel file to Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse all sheets with caching (first run - calls LLM)
  uv run scripts/parse_xlsx_admission.py --upload-to-qdrant

  # Re-run using cache (no LLM calls)
  uv run scripts/parse_xlsx_admission.py --upload-to-qdrant

  # Force refresh (ignore cache, re-call LLM)
  uv run scripts/parse_xlsx_admission.py --force-refresh --upload-to-qdrant

  # Re-embed from cache (load cached .pkl files, upload to Qdrant)
  uv run scripts/parse_xlsx_admission.py --from-cache --upload-to-qdrant

  # Parse specific sheets only
  uv run scripts/parse_xlsx_admission.py \\
    --sheets "Program Studi S1" "Jadwal Pendaftaran Magister S2" \\
    --upload-to-qdrant

  # Clear cache for a specific sheet
  uv run scripts/parse_xlsx_admission.py --clear-cache "Program Studi S1"

  # Clear all cache
  uv run scripts/parse_xlsx_admission.py --clear-cache-all

  # List cached sheets
  uv run scripts/parse_xlsx_admission.py --list-cache
        """,
    )

    # Input options
    parser.add_argument(
        "--xlsx-path",
        default="scripts/Informasi Umum ITB - Tabel.xlsx",
        help="Path to Excel file",
    )
    parser.add_argument("--sheets", nargs="+", help="Specific sheets to parse")
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Load documents from cache .pkl files instead of parsing XLSX",
    )

    # Cache options
    parser.add_argument(
        "--cache-dir", default="cache", help="Directory to store cache .pkl files"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable caching (always call LLM)"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore existing cache and re-parse with LLM",
    )
    parser.add_argument(
        "--clear-cache", metavar="SHEET", help="Clear cache for specific sheet"
    )
    parser.add_argument(
        "--clear-cache-all", action="store_true", help="Clear all cache"
    )
    parser.add_argument("--list-cache", action="store_true", help="List all cached sheets")

    # Output options
    parser.add_argument("--upload-to-qdrant", action="store_true")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument(
        "--collection",
        help="Qdrant collection name (default: auto-selected based on embedding provider)",
    )
    parser.add_argument(
        "--embedding-provider",
        default="openai",
        choices=["openai", "qwen"],
        help="Embedding provider (default: openai)",
    )

    args = parser.parse_args()

    # Initialize cache
    from scripts.parsers.xlsx_parser import LLMCache

    cache = LLMCache(args.cache_dir)

    # Handle cache management commands
    if args.clear_cache_all:
        print("Clearing all cache...")
        cache.clear()
        return

    if args.clear_cache:
        print(f"Clearing cache for: {args.clear_cache}")
        cache.clear(args.clear_cache)
        return

    if args.list_cache:
        cached = cache.list_cached()
        print(f"Cached sheets ({len(cached)}):")
        for sheet in cached:
            print(f"  - {sheet}")
        return

    print("=" * 60)
    print("ITB Excel to Qdrant Parser")
    print("=" * 60)

    # Load from cache or parse
    if args.from_cache:
        print("Loading from cache...")
        rag_docs = cache.load_all_cached()
        print(f"Loaded {len(rag_docs)} documents from cache")
    else:
        # Check if xlsx file exists
        xlsx_path = Path(args.xlsx_path)
        if not xlsx_path.exists():
            print(f"Error: Excel file not found: {args.xlsx_path}")
            sys.exit(1)

        # Initialize parser
        from scripts.parsers.xlsx_parser import ITBExcelParser

        xlsx_parser = ITBExcelParser(
            xlsx_path=args.xlsx_path,
            sheets=args.sheets,
            cache_dir=args.cache_dir,
            use_cache=not args.no_cache,
            force_refresh=args.force_refresh,
        )

        # Parse
        xlsx_parser.parse()
        rag_docs = xlsx_parser.to_rag_documents()

    print(f"\nTotal documents: {len(rag_docs)}")

    # Upload to Qdrant
    if args.upload_to_qdrant:
        print()
        print("=" * 60)
        print("Uploading to Qdrant")
        print("=" * 60)

        success = upload_to_qdrant(rag_docs, args.batch_size, args.embedding_provider, args.collection)

        if not success:
            print("\nError: Failed to upload to Qdrant")
            sys.exit(1)

        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Documents processed: {len(rag_docs)}")
        collection_name = (
            "informasi-umum-itb-qwen3"
            if args.embedding_provider == "qwen"
            else "informasi-umum-itb"
        )
        print(f"  Uploaded to: {collection_name}")
        print()


if __name__ == "__main__":
    main()
