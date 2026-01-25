#!/usr/bin/env python3
"""
Script to re-embed Qdrant collection data using a new embedding model.

This script:
1. Reads all points from an existing Qdrant collection (without old vectors)
2. Re-embeds using OpenRouter's embedding model
3. Creates a new collection with new embeddings
4. Optionally creates and downloads a new snapshot

Usage:
    # Read from existing collection and re-embed
    python scripts/reembed_snapshot.py --source-collection informasi-umum-itb

    # With custom embedding model and batch size
    python scripts/reembed_snapshot.py --source-collection informasi-umum-itb --embedding-model openai/text-embedding-3-small --batch-size 100

    # Create snapshot after re-embedding
    python scripts/reembed_snapshot.py --source-collection informasi-umum-itb --create-snapshot
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
    import requests
except ImportError:
    print("Error: Required packages are missing")
    print("Run: pip install qdrant-client requests python-dotenv")
    sys.exit(1)


class QdrantCollectionReembedder:
    """Re-embed Qdrant collection points with a new embedding model."""

    # Known embedding dimensions (use None for native dimension)
    # Qwen3-Embedding series native dimensions:
    # - 0.6B: 1024
    # - 4B: 2560
    # - 8B: 4096
    EMBEDDING_DIMENSIONS = {
        "openai/text-embedding-3-small": 1536,
        "openai/text-embedding-3-large": 3072,
        "openai/text-embedding-ada-002": 1536,
        "qwen/qwen2-7b-instruct": 1536,
        "qwen/qwen3-embedding-0.6b": 1024,
        "qwen/qwen3-embedding-4b": 2560,
        "qwen/qwen3-embedding-8b": None,  # Use native dimension (4096)
    }

    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: Optional[str],
        api_key: str,
        embedding_model: str = "openai/text-embedding-3-small",
        provider: str = "openai",  # "openai" or "openrouter"
    ):
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.provider = provider

        # Initialize Qdrant client
        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.client = QdrantClient(url=qdrant_url)

        self.output_collection_name: Optional[str] = None

    def connect_to_qdrant(self) -> bool:
        """Verify connection to Qdrant."""
        try:
            collections = self.client.get_collections()
            print(f"  Connected to Qdrant at {self.qdrant_url}")
            print(f"  Available collections: {[col.name for col in collections.collections]}")
            return True
        except Exception as e:
            print(f"  Failed to connect to Qdrant: {e}")
            return False

    def read_all_points(self, collection_name: str) -> List[Dict]:
        """Read all points from collection using scroll API."""
        all_points = []
        offset = None
        limit = 100

        print(f"  Reading points from '{collection_name}'...")

        # First verify collection exists
        try:
            collections = self.client.get_collections()
            if collection_name not in [col.name for col in collections.collections]:
                print(f"  Error: Collection '{collection_name}' not found")
                return []
        except Exception as e:
            print(f"  Error checking collections: {e}")
            return []

        while True:
            records, offset = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            all_points.extend(records)

            if offset is None:
                break

            if len(all_points) % 500 == 0:
                print(f"    Read {len(all_points)} points...")

        print(f"  Read {len(all_points)} total points")

        # Analyze payload structure
        if all_points:
            self._analyze_payloads(all_points)

        return all_points

    def _analyze_payloads(self, points: List) -> None:
        """Analyze payload structure to understand data format."""
        if not points:
            return

        sample = points[0].payload
        print(f"  Sample payload keys: {list(sample.keys())}")

        # Check for common text fields
        text_fields = []
        for key in sample.keys():
            if isinstance(sample[key], str) and len(sample[key]) > 50:
                text_fields.append(key)

        if text_fields:
            print(f"  Potential text fields for embedding: {text_fields}")

        # Calculate text statistics
        if "page_content" in sample:
            total_length = sum(len(str(record.payload.get("page_content", ""))) for record in points)
            avg_length = total_length / len(points)
            max_length = max(len(str(record.payload.get("page_content", ""))) for record in points)
            print(f"  page_content stats: avg={avg_length:.0f} chars, max={max_length} chars")

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the current model."""
        # Check known dimensions first
        for model_key, dim in self.EMBEDDING_DIMENSIONS.items():
            if model_key in self.embedding_model:
                if dim is None:
                    # Use native dimension - need to test with actual API call
                    print(f"  Using native dimension for {self.embedding_model} (testing...)")
                    test_embedding = self._embed_batch(["test"])
                    if test_embedding:
                        dimension = len(test_embedding[0])
                        print(f"  Measured embedding dimension: {dimension}")
                        return dimension
                    else:
                        raise Exception("Failed to get embedding dimension")
                else:
                    print(f"  Using known dimension for {self.embedding_model}: {dim}")
                    return dim

        # Otherwise test with actual API call
        print(f"  Testing embedding dimension for {self.embedding_model}...")
        test_embedding = self._embed_batch(["test"])
        if test_embedding:
            dimension = len(test_embedding[0])
            print(f"  Measured embedding dimension: {dimension}")
            return dimension
        else:
            raise Exception("Failed to get embedding dimension")

    def _embed_batch_openai(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed using OpenAI API directly."""
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "input": texts,
            "model": self.embedding_model,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings

        except Exception as e:
            print(f"  OpenAI API error: {e}")
            return None

    def _embed_batch_openrouter(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed using OpenRouter API directly."""
        url = "https://openrouter.ai/api/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
        }

        # Build request data - only specify dimensions if model requires it
        # For Qwen3-8B, use native dimension (4096) by not specifying dimensions
        data = {
            "input": texts,
            "model": self.embedding_model,
        }

        # Only add dimensions parameter for models that need explicit specification
        # Qwen3-8B uses native dimension (None in dict means don't specify)
        for model_key, dim in self.EMBEDDING_DIMENSIONS.items():
            if model_key in self.embedding_model and dim is not None:
                data["dimensions"] = dim
                break

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings

        except Exception as e:
            print(f"  OpenRouter API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"  Response: {e.response.text}")
            return None

    def _embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed a batch of texts using the configured provider."""
        if self.provider == "openai":
            return self._embed_batch_openai(texts)
        elif self.provider == "openrouter":
            return self._embed_batch_openrouter(texts)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def reembed_points(
        self,
        points: List,
        batch_size: int,
        text_field: str = "page_content",
        max_retries: int = 3,
    ) -> List[Dict]:
        """Re-embed points using the configured embedding API."""
        reembedded = []

        total = len(points)
        print(f"  Re-embedding {total} points with {self.embedding_model}...")
        print(f"  Using text field: '{text_field}'")
        print(f"  Provider: {self.provider}")

        for i in range(0, total, batch_size):
            batch = points[i:i + batch_size]

            # Extract texts from specified field
            texts = []
            valid_points = []

            for point in batch:
                text = point.payload.get(text_field, "")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
                    valid_points.append(point)
                else:
                    print(f"  Warning: Point {point.id} has empty or missing '{text_field}' field")

            if not texts:
                print(f"  Warning: No valid texts in batch {i//batch_size}")
                continue

            # Embed batch with retries
            new_vectors = None
            for attempt in range(max_retries):
                try:
                    new_vectors = self._embed_batch(texts)
                    if new_vectors:
                        break
                except Exception as e:
                    print(f"  Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)

            if new_vectors is None:
                print(f"  Error: Failed to embed batch {i//batch_size} after {max_retries} attempts")
                continue

            # Store with original data
            for point, vector in zip(valid_points, new_vectors):
                reembedded.append({
                    "id": point.id,
                    "vector": vector,
                    "payload": point.payload,
                })

            progress = min(i + batch_size, total)
            pct = progress / total * 100
            print(f"    Progress: {progress}/{total} ({pct:.1f}%)")

        return reembedded

    def create_new_collection(self, dimension: int, output_name: str) -> bool:
        """Create new collection for re-embedded points."""
        print(f"  Creating new collection: '{output_name}'")

        # Check if collection exists
        try:
            collections = self.client.get_collections()
            existing = [col.name for col in collections.collections]

            if output_name in existing:
                print(f"  Warning: Collection '{output_name}' already exists")
                response = input(f"  Delete and recreate? (y/N): ")
                if response.lower() == "y":
                    self.client.delete_collection(output_name)
                    print(f"  Deleted existing collection")
                else:
                    print(f"  Aborting...")
                    return False
        except Exception as e:
            print(f"  Warning: Could not check existing collections: {e}")

        # Create collection
        try:
            self.client.create_collection(
                collection_name=output_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            print(f"  Collection created with dimension {dimension}")
            self.output_collection_name = output_name
            return True
        except Exception as e:
            print(f"  Failed to create collection: {e}")
            return False

    def insert_points(self, reembedded: List[Dict], batch_size: int = 100) -> bool:
        """Insert re-embedded points into new collection."""
        total = len(reembedded)
        output_name = self.output_collection_name
        print(f"  Inserting {total} points into '{output_name}'...")

        for i in range(0, total, batch_size):
            batch = reembedded[i:i + batch_size]

            points = [
                PointStruct(
                    id=item["id"],
                    vector=item["vector"],
                    payload=item["payload"],
                )
                for item in batch
            ]

            try:
                self.client.upsert(
                    collection_name=output_name,
                    points=points,
                )
            except Exception as e:
                print(f"  Error inserting batch starting at {i}: {e}")
                continue

            progress = min(i + batch_size, total)
            pct = progress / total * 100
            print(f"    Progress: {progress}/{total} ({pct:.1f}%)")

        # Verify insertion
        try:
            info = self.client.get_collection(output_name)
            print(f"  Verification: Collection has {info.points_count} points")
        except Exception as e:
            print(f"  Warning: Could not verify collection: {e}")

        return True

    def create_snapshot(self, output_dir: str) -> Optional[str]:
        """Create and download snapshot from output collection."""
        output_name = self.output_collection_name

        print(f"  Creating snapshot for '{output_name}'...")

        try:
            snapshot_info = self.client.create_snapshot(collection_name=output_name)
            print(f"  Snapshot created: {snapshot_info.name}")
        except Exception as e:
            print(f"  Failed to create snapshot: {e}")
            return None

        # Download snapshot
        os.makedirs(output_dir, exist_ok=True)

        snapshot_name = self.generate_snapshot_name(self.embedding_model, self.provider)
        snapshot_path = os.path.join(output_dir, f"{snapshot_name}.snapshot")

        download_url = f"{self.qdrant_url}/collections/{output_name}/snapshots/{snapshot_info.name}"

        headers = {}
        if self.qdrant_api_key:
            headers["api-key"] = self.qdrant_api_key

        print(f"  Downloading snapshot...")

        try:
            response = requests.get(download_url, headers=headers, stream=True, timeout=600)

            if response.status_code != 200:
                raise Exception(f"Download failed: {response.status_code} - {response.text}")

            with open(snapshot_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(snapshot_path) / (1024 * 1024)
            print(f"  Downloaded to: {snapshot_path}")
            print(f"  File size: {file_size:.2f} MB")

            return snapshot_path

        except Exception as e:
            print(f"  Failed to download snapshot: {e}")
            return None

    def generate_snapshot_name(self, model_name: str, provider: str) -> str:
        """Generate snapshot name with model, provider, date, and time."""
        now = datetime.now()
        date_str = now.strftime("%d%b").lower()
        time_str = now.strftime("%H%M")

        safe_model = model_name.replace("/", "-").replace("_", "-")

        return f"snapshot-{provider}-{safe_model}-{date_str}-{time_str}"


def print_header():
    """Print script header."""
    print("=" * 60)
    print("Qdrant Collection Re-embedding Tool")
    print("=" * 60)
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Re-embed Qdrant collection with a new embedding model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Re-embed with OpenAI (requires OPENAI_API_KEY)
  python scripts/reembed_snapshot.py --source-collection informasi-umum-itb --provider openai

  # Re-embed with OpenRouter
  python scripts/reembed_snapshot.py --source-collection informasi-umum-itb --provider openrouter --embedding-model qwen/qwen3-embedding-8b

  # With custom batch size and output collection
  python scripts/reembed_snapshot.py --source-collection informasi-umum-itb --provider openai --batch-size 100 --output-collection itb-v2
        """,
    )
    parser.add_argument(
        "--source-collection",
        type=str,
        default=os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb"),
        help="Source Qdrant collection name (default: from QDRANT_COLLECTION_NAME env var)",
    )
    parser.add_argument(
        "--output-collection",
        type=str,
        default=None,
        help="Output collection name (default: {source_collection}_reembedded)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "openrouter"],
        default="openai",
        help="Embedding API provider (default: openai)",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Embedding model name (default: text-embedding-3-small for openai, qwen/qwen3-embedding-8b for openrouter)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Embedding batch size (default: 100)",
    )
    parser.add_argument(
        "--text-field",
        type=str,
        default="page_content",
        help="Payload field containing text to embed (default: page_content)",
    )
    parser.add_argument(
        "--create-snapshot",
        action="store_true",
        help="Create and download a snapshot after re-embedding",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=str,
        default="qdrant_snapshots",
        help="Directory for snapshot output (default: qdrant_snapshots)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read points and analyze without re-embedding or creating collection",
    )

    args = parser.parse_args()

    # Set default embedding model based on provider
    if args.embedding_model is None:
        if args.provider == "openai":
            args.embedding_model = "text-embedding-3-small"
        else:
            args.embedding_model = "qwen/qwen3-embedding-8b"

    # Get configuration from environment
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    # Get API key based on provider
    if args.provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is required for provider 'openai'")
            sys.exit(1)
    else:  # openrouter
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("Error: OPENROUTER_API_KEY environment variable is required for provider 'openrouter'")
            sys.exit(1)

    # Set default output collection name
    if args.output_collection is None:
        args.output_collection = f"{args.source_collection}_reembedded"

    print_header()

    print("Configuration:")
    print(f"  Qdrant URL: {qdrant_url}")
    print(f"  Source Collection: {args.source_collection}")
    print(f"  Output Collection: {args.output_collection}")
    print(f"  Provider: {args.provider}")
    print(f"  Embedding Model: {args.embedding_model}")
    print(f"  Batch Size: {args.batch_size}")
    print(f"  Text Field: {args.text_field}")
    if args.create_snapshot:
        print(f"  Create Snapshot: Yes (to {args.snapshot_dir})")
    if args.dry_run:
        print(f"  Dry Run: Yes (no re-embedding)")
    print()

    # Initialize reembedder
    reembedder = QdrantCollectionReembedder(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        api_key=api_key,
        embedding_model=args.embedding_model,
        provider=args.provider,
    )

    # STEP 1: Connect to Qdrant
    print("STEP 1: Connecting to Qdrant...")
    if not reembedder.connect_to_qdrant():
        sys.exit(1)
    print()

    # STEP 2: Read all points from source collection
    print("STEP 2: Reading points from source collection...")
    points = reembedder.read_all_points(args.source_collection)

    if not points:
        print("  No points found in collection")
        sys.exit(1)
    print()

    # Dry run - just analyze and exit
    if args.dry_run:
        print("=" * 60)
        print("Dry Run Complete")
        print("=" * 60)
        print(f"  Read {len(points)} points from '{args.source_collection}'")
        print(f"  Would re-embed with {args.embedding_model}")
        print()
        return

    # STEP 3: Get embedding dimension
    print("STEP 3: Determining embedding dimension...")
    dimension = reembedder.get_embedding_dimension()
    print()

    # STEP 4: Re-embed points
    print(f"STEP 4: Re-embedding points...")
    reembedded = reembedder.reembed_points(points, args.batch_size, args.text_field)

    if not reembedded:
        print("  No points were re-embedded")
        sys.exit(1)

    print(f"  Re-embedded {len(reembedded)} points")
    print()

    # STEP 5: Create new collection
    print("STEP 5: Creating new collection...")
    if not reembedder.create_new_collection(dimension, args.output_collection):
        sys.exit(1)
    print()

    # STEP 6: Insert points
    print("STEP 6: Inserting re-embedded points...")
    reembedder.insert_points(reembedded)
    print()

    # STEP 7: Create snapshot (optional)
    snapshot_path = None
    if args.create_snapshot:
        print("STEP 7: Creating snapshot...")
        snapshot_path = reembedder.create_snapshot(args.snapshot_dir)
        if not snapshot_path:
            print("  Failed to create snapshot")
        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Input: {len(points)} points from '{args.source_collection}'")
    print(f"  Re-embedded: {len(reembedded)} points")
    print(f"  Output Collection: '{reembedder.output_collection_name}'")
    print(f"  Embedding Model: {args.embedding_model}")
    print(f"  Vector Dimension: {dimension}")
    if snapshot_path:
        print(f"  Snapshot: {snapshot_path}")
    print()
    print("Next steps:")
    print(f"1. Test the new collection: '{reembedder.output_collection_name}'")
    print("2. Update your application to use the new embedding model")
    print(f"3. Update QDRANT_COLLECTION_NAME to '{reembedder.output_collection_name}'")
    print()


if __name__ == "__main__":
    main()
