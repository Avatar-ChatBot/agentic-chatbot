#!/usr/bin/env python3
"""
CLI tool to parse Indonesian legal documents (Peraturan Perundang-undangan).

This script extracts Pasal (articles) from PDF or text files of Indonesian
legislation and outputs structured data for use in RAG systems.

Supported formats: PDF, TXT, JSON (pre-parsed)
Output formats: JSON, Markdown, Console (pretty-printed), Qdrant upload

Usage:
    python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf
    python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output json
    python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output markdown --output-file ./output.md
    python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --upload-to-qdrant
    python scripts/parse_peraturan_pdf.py --json-input ./parsed.json --upload-to-qdrant
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add project root and scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def print_header():
    """Print script header."""
    print("=" * 60)
    print("Peraturan Perundang-undangan Parser")
    print("=" * 60)
    print()


def print_summary(parser) -> None:
    """Print parsing summary."""
    summary = parser.get_summary()

    print("\nSummary:")
    print("-" * 40)
    print(f"  Source:          {summary['source']}")
    print(f"  Total BAB:       {summary['total_babs']}")
    print(f"  Total Pasal:     {summary['total_pasals']}")
    print(f"  BAB Range:       {summary['bab_range']}")
    print(f"  Pasal Range:     {summary['pasal_range']}")


def pretty_print_pasals(pasals, limit: Optional[int] = None) -> None:
    """Pretty print parsed Pasal objects to console."""
    print("\nParsed Pasal:")
    print("-" * 40)

    for i, pasal in enumerate(pasals):
        if limit and i >= limit:
            print(f"\n... and {len(pasals) - limit} more pasals")
            break

        print(f"\n[Pasal {pasal.pasal}]")
        if pasal.pasal_title:
            print(f"  Title: {pasal.pasal_title}")
        print(f"  BAB:  {pasal.bab} - {pasal.bab_title}")
        print(f"  Content: {pasal.content[:200]}{'...' if len(pasal.content) > 200 else ''}")


def load_rag_documents_from_json(json_path: str) -> List[Dict[str, Any]]:
    """Load RAG documents from a JSON file."""
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both formats: direct list or dict with "documents" key
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "documents" in data:
        return data["documents"]
    else:
        raise ValueError("JSON must be a list or a dict with 'documents' key")


def upload_to_qdrant(
    documents: List[Dict[str, Any]],
    batch_size: int = 50,
    embedding_provider: str = "openai",
) -> bool:
    """
    Embed and upload documents to Qdrant.

    Args:
        documents: List of documents to embed and upload
        batch_size: Batch size for upload
        embedding_provider: Either "openai" or "qwen"

    Uses the same configuration as agents/models.py:
    - OpenAI: text-embedding-3-large, collection "informasi-umum-itb"
    - Qwen: qwen/qwen3-embedding-8b, collection "informasi-umum-itb-qwen3"
    """
    # Load environment variables
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
        collection_name = "informasi-umum-itb"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        print(f"  Using OpenAI embedding: text-embedding-3-large")

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
    langchain_docs = []
    for doc in documents:
        if isinstance(doc, dict):
            langchain_docs.append(Document(
                page_content=doc.get("page_content", doc.get("content", "")),
                metadata=doc.get("metadata", {}),
            ))
        else:
            # Already a Document object
            langchain_docs.append(doc)

    print(f"  Uploading {len(langchain_docs)} documents in batches of {batch_size}...")

    # Upload in batches
    total = len(langchain_docs)
    try:
        for i in range(0, total, batch_size):
            batch = langchain_docs[i:i + batch_size]
            vectorstore.add_documents(batch)

            progress = min(i + batch_size, total)
            pct = progress / total * 100
            print(f"    Progress: {progress}/{total} ({pct:.1f}%)")

        # Verify upload
        collection_info = qdrant_client.get_collection(collection_name)
        print(f"  Upload complete!")
        print(f"  Collection now has {collection_info.points_count} points")

        return True

    except Exception as e:
        print(f"  Error uploading documents: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse Indonesian legal documents (Peraturan Perundang-undangan)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic parsing - output to console
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf

  # Output to JSON file
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output json

  # Output to Markdown file
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output markdown --output-file ./output.md

  # Custom source name
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/doc.pdf --source-name "UU No 1 Tahun 2024"

  # Export for RAG pipeline (JSON with specific format)
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output rag --output-file ./rag_data.json

  # Parse and upload to Qdrant (end-to-end)
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --upload-to-qdrant

  # Upload from existing JSON file to Qdrant
  python scripts/parse_peraturan_pdf.py --json-input ./rag_data.json --upload-to-qdrant
        """,
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--pdf-path",
        type=str,
        default=None,
        help="Path to PDF or text file to parse",
    )
    input_group.add_argument(
        "--json-input",
        type=str,
        default=None,
        help="Path to pre-parsed JSON file (skips parsing, used for --upload-to-qdrant)",
    )

    parser.add_argument(
        "--source-name",
        type=str,
        default=None,
        help="Custom source name (default: filename)",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["console", "json", "markdown", "rag"],
        default="console",
        help="Output format (default: console)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Output file path (default: auto-generated)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of pasals to display (console output only)",
    )
    parser.add_argument(
        "--include-raw-text",
        action="store_true",
        help="Include raw extracted text in JSON output",
    )
    parser.add_argument(
        "--upload-to-qdrant",
        action="store_true",
        help="Embed and upload documents to Qdrant collection",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for Qdrant upload (default: 50)",
    )
    parser.add_argument(
        "--embedding-provider",
        type=str,
        choices=["openai", "qwen"],
        default="openai",
        help="Embedding provider: openai (text-embedding-3-large, informasi-umum-itb) or qwen (qwen3-embedding-8b, informasi-umum-itb-qwen3) (default: openai)",
    )

    args = parser.parse_args()

    print_header()

    # Variables to hold RAG documents for upload
    rag_documents: List[Dict[str, Any]] = []
    parser_instance = None
    input_path = None

    # Path 1: Load from JSON (skip parsing)
    if args.json_input:
        input_path = Path(args.json_input)
        if not input_path.exists():
            print(f"Error: JSON file not found: {args.json_input}")
            sys.exit(1)

        print(f"Loading from JSON: {args.json_input}")
        try:
            rag_documents = load_rag_documents_from_json(args.json_input)
            print(f"Loaded {len(rag_documents)} documents from JSON")
        except Exception as e:
            print(f"Error loading JSON: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Path 2: Parse from PDF/TXT
    elif args.pdf_path:
        input_path = Path(args.pdf_path)
        if not input_path.exists():
            print(f"Error: File not found: {args.pdf_path}")
            sys.exit(1)

        # Import parser - try relative first, then absolute
        try:
            # Try relative import (when run as module from scripts/)
            from parsers.peraturan_parser import PeraturanParser
        except ImportError:
            try:
                # Try absolute import (when run from project root with python scripts/)
                from scripts.parsers.peraturan_parser import PeraturanParser
            except ImportError as e:
                print(f"Error: Could not import parser: {e}")
                print(f"Project root: {PROJECT_ROOT}")
                print(f"Script dir: {SCRIPT_DIR}")
                print(f"sys.path: {sys.path[:3]}...")
                sys.exit(1)

        # Initialize parser
        source_name = args.source_name or input_path.stem
        print(f"Input file:  {args.pdf_path}")
        print(f"Source name: {source_name}")
        print()

        parser_instance = PeraturanParser(args.pdf_path, source_name)

        # Parse document
        print("Parsing document...")
        try:
            pasals = parser_instance.parse()
        except Exception as e:
            print(f"Error parsing document: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        if not pasals:
            print("Warning: No Pasal found in document")
            sys.exit(0)

        print(f"Found {len(pasals)} Pasal")

        # Convert to RAG format
        rag_documents = parser_instance.to_rag_documents()

        # Output based on format (skip if only uploading)
        if args.output == "console":
            pretty_print_pasals(pasals, args.limit)
            print_summary(parser_instance)

        elif args.output == "json":
            output_file = args.output_file or f"{input_path.stem}_parsed.json"
            output_path = parser_instance.export_json(output_file)

            print(f"\nJSON output written to: {output_path}")
            print_summary(parser_instance)

        elif args.output == "markdown":
            output_file = args.output_file or f"{input_path.stem}_parsed.md"
            output_path = parser_instance.export_markdown(output_file)

            print(f"\nMarkdown output written to: {output_path}")
            print_summary(parser_instance)

        elif args.output == "rag":
            # Export in format compatible with RAG pipeline
            output_file = args.output_file or f"{input_path.stem}_rag.json"
            output_path = Path(output_file)

            rag_data = {
                "metadata": parser_instance.get_summary(),
                "documents": rag_documents,
            }

            if args.include_raw_text:
                rag_data["raw_text"] = parser_instance.raw_text

            output_path.write_text(
                json.dumps(rag_data, ensure_ascii=False, indent=2)
            )

            print(f"\nRAG format output written to: {output_path}")
            print_summary(parser_instance)

    # Upload to Qdrant if requested
    if args.upload_to_qdrant:
        print()
        print("=" * 60)
        print("Uploading to Qdrant")
        print("=" * 60)

        success = upload_to_qdrant(rag_documents, args.batch_size, args.embedding_provider)

        if not success:
            print("\nError: Failed to upload to Qdrant")
            sys.exit(1)

        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Documents processed: {len(rag_documents)}")
        collection_name = "informasi-umum-itb-qwen3" if args.embedding_provider == "qwen" else "informasi-umum-itb"
        print(f"  Uploaded to: {collection_name}")
        print()

    print()


if __name__ == "__main__":
    main()
