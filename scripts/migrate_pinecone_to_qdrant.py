#!/usr/bin/env python3
"""
Migration script to transfer vectors from Pinecone to Qdrant.

This script has two separate steps:
1. STEP 1: Extract data from Pinecone and save to a pickle file
2. STEP 2: Load data from pickle file and upload to Qdrant

Usage:
    # Step 1: Extract from Pinecone
    python migrate_pinecone_to_qdrant.py --step extract --output pinecone_data.pkl

    # Step 2: Upload to Qdrant
    python migrate_pinecone_to_qdrant.py --step upload --input pinecone_data.pkl
"""

import os
import sys
import time
import pickle
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from pinecone import Pinecone
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
    )
except ImportError as e:
    print(f"Error: Missing required package. Please install: {e.name}")
    print("Run: pip install pinecone-client qdrant-client")
    sys.exit(1)


class PineconeExtractor:
    """Extracts vectors from Pinecone and saves to file"""

    def __init__(
        self,
        pinecone_api_key: str,
        pinecone_index_name: str,
    ):
        """
        Initialize the extractor.

        Args:
            pinecone_api_key: Pinecone API key
            pinecone_index_name: Name of Pinecone index to extract from
        """
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_index_name = pinecone_index_name

        # Initialize Pinecone client
        print("Initializing Pinecone client...")
        self.pinecone_client = Pinecone(api_key=pinecone_api_key)
        self.pinecone_index = self.pinecone_client.Index(pinecone_index_name)

        # Get vector dimension from index stats
        print(f"Fetching Pinecone index stats for '{pinecone_index_name}'...")
        try:
            stats = self.pinecone_index.describe_index_stats()
            # Default dimension for text-embedding-3-large
            self.vector_dimension = 3072
            print(f"Using vector dimension: {self.vector_dimension}")
        except Exception as e:
            print(f"Warning: Could not determine vector dimension: {e}")
            print("Using default dimension: 3072 (text-embedding-3-large)")
            self.vector_dimension = 3072

    def check_pinecone_connection(self) -> bool:
        """Check if Pinecone index is accessible"""
        try:
            stats = self.pinecone_index.describe_index_stats()
            total_vectors = stats.get("total_vector_count", 0)
            print(f"✓ Pinecone connection successful")
            print(f"  Index: {self.pinecone_index_name}")
            print(f"  Total vectors: {total_vectors}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Pinecone: {e}")
            return False

    def fetch_all_pinecone_vectors(
        self, vector_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all vectors from Pinecone index.

        Args:
            vector_ids: Optional list of vector IDs to fetch. If provided, uses fetch().
                       If None, attempts to query all vectors (may not get all).

        Returns:
            List of vectors with their IDs, values, and metadata
        """
        print("\nFetching vectors from Pinecone...")
        all_vectors = []

        try:
            # Get index stats first
            stats = self.pinecone_index.describe_index_stats()
            total_vectors = stats.get("total_vector_count", 0)

            if total_vectors == 0:
                print("No vectors found in Pinecone index")
                return []

            print(f"Total vectors in index: {total_vectors}")

            # Strategy 1: If vector IDs are provided, use fetch()
            if vector_ids:
                print(f"Using provided list of {len(vector_ids)} vector IDs...")
                return self._fetch_vectors_by_ids(vector_ids)

            # Strategy 2: Try to use list_paginated if available (Pinecone serverless)
            try:
                print("Attempting to list all vector IDs using list_paginated...")
                all_ids = []
                pagination_token = None

                # Try to get all IDs using pagination
                while True:
                    if pagination_token:
                        result = self.pinecone_index.list(
                            pagination_token=pagination_token, limit=100
                        )
                    else:
                        result = self.pinecone_index.list(limit=100)

                    if hasattr(result, "vectors"):
                        all_ids.extend([v.id for v in result.vectors])
                    elif hasattr(result, "ids"):
                        all_ids.extend(result.ids)
                    else:
                        break

                    # Check if there's more to fetch
                    if hasattr(result, "pagination") and result.pagination:
                        pagination_token = result.pagination.next
                    elif hasattr(result, "next"):
                        pagination_token = result.next
                    else:
                        break

                    if not pagination_token:
                        break

                if all_ids:
                    print(f"Found {len(all_ids)} vector IDs, fetching vectors...")
                    return self._fetch_vectors_by_ids(all_ids)
            except Exception as e:
                print(f"list_paginated not available: {e}")
                print("Falling back to query-based approach...")

            # Strategy 3: Query-based approach (limited, may not get all vectors)
            print("Using query-based approach (may not fetch all vectors)...")
            print(
                "⚠ Note: This method has limitations. Consider providing a list of vector IDs."
            )

            # Create a zero vector for querying
            zero_vector = [0.0] * self.vector_dimension

            # Query with high top_k (Pinecone limit is usually 10000)
            top_k = min(10000, total_vectors)

            print(f"Querying Pinecone with top_k={top_k}...")
            results = self.pinecone_index.query(
                vector=zero_vector,
                top_k=top_k,
                include_metadata=True,
                include_values=True,
            )

            for match in results.matches:
                vector_data = {
                    "id": match.id,
                    "vector": match.values,
                    "metadata": match.metadata or {},
                    "score": match.score,
                }
                all_vectors.append(vector_data)

            print(f"Fetched {len(all_vectors)} vectors from Pinecone")

            # If we didn't get all vectors, warn the user
            if len(all_vectors) < total_vectors:
                print(
                    f"⚠ Warning: Only fetched {len(all_vectors)} of {total_vectors} vectors"
                )
                print("To fetch all vectors, consider:")
                print("1. Providing a list of vector IDs via --vector-ids-file")
                print("2. Using the official Qdrant migration tool")
                print("3. Exporting IDs from your application if available")

        except Exception as e:
            print(f"✗ Error fetching vectors from Pinecone: {e}")
            import traceback

            traceback.print_exc()
            raise

        return all_vectors

    def _fetch_vectors_by_ids(self, vector_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch vectors by their IDs using Pinecone's fetch() method.

        Args:
            vector_ids: List of vector IDs to fetch

        Returns:
            List of vectors with their IDs, values, and metadata
        """
        all_vectors = []
        batch_size = 1000  # Pinecone fetch limit per request

        print(f"Fetching {len(vector_ids)} vectors in batches of {batch_size}...")

        for i in range(0, len(vector_ids), batch_size):
            batch_ids = vector_ids[i : i + batch_size]

            try:
                fetch_response = self.pinecone_index.fetch(ids=batch_ids)

                # Process fetched vectors
                if hasattr(fetch_response, "vectors"):
                    for vec_id, vec_data in fetch_response.vectors.items():
                        vector_info = {
                            "id": vec_id,
                            "vector": vec_data.values
                            if hasattr(vec_data, "values")
                            else None,
                            "metadata": vec_data.metadata
                            if hasattr(vec_data, "metadata")
                            else {},
                        }
                        all_vectors.append(vector_info)
                elif isinstance(fetch_response, dict):
                    for vec_id, vec_data in fetch_response.items():
                        vector_info = {
                            "id": vec_id,
                            "vector": vec_data.get("values")
                            if isinstance(vec_data, dict)
                            else None,
                            "metadata": vec_data.get("metadata", {})
                            if isinstance(vec_data, dict)
                            else {},
                        }
                        all_vectors.append(vector_info)

                progress = min(i + batch_size, len(vector_ids))
                print(f"  Progress: {progress}/{len(vector_ids)} vectors fetched")

            except Exception as e:
                print(f"  ⚠ Error fetching batch {i//batch_size + 1}: {e}")
                continue

        print(f"Successfully fetched {len(all_vectors)} vectors")
        return all_vectors

    def extract_and_save(self, output_file: str, vector_ids: Optional[List[str]] = None) -> bool:
        """
        Extract vectors from Pinecone and save to pickle file.

        Args:
            output_file: Path to output pickle file
            vector_ids: Optional list of vector IDs to extract

        Returns:
            True if successful, False otherwise
        """
        print("=" * 60)
        print("STEP 1: Extract Data from Pinecone")
        print("=" * 60)
        print()

        # Check connection
        print("Checking Pinecone connection...")
        if not self.check_pinecone_connection():
            return False
        print()

        # Fetch vectors
        print("Fetching vectors from Pinecone...")
        try:
            vectors = self.fetch_all_pinecone_vectors(vector_ids=vector_ids)
            if not vectors:
                print("No vectors to extract")
                return False
        except Exception as e:
            print(f"✗ Failed to fetch vectors: {e}")
            return False
        print()

        # Save to pickle file
        print(f"Saving {len(vectors)} vectors to {output_file}...")
        try:
            # Create metadata
            metadata = {
                "extraction_date": datetime.now().isoformat(),
                "pinecone_index": self.pinecone_index_name,
                "vector_count": len(vectors),
                "vector_dimension": self.vector_dimension,
                "sample_ids": [v["id"] for v in vectors[:5]] if vectors else [],
            }

            # Save data
            data = {
                "metadata": metadata,
                "vectors": vectors,
            }

            with open(output_file, "wb") as f:
                pickle.dump(data, f)

            file_size = os.path.getsize(output_file) / (1024 * 1024)  # Size in MB
            print(f"✓ Successfully saved {len(vectors)} vectors to {output_file}")
            print(f"  File size: {file_size:.2f} MB")
            print(f"  Extraction date: {metadata['extraction_date']}")
            
            # Show sample metadata structure
            if vectors:
                sample_metadata = vectors[0].get("metadata", {})
                print(f"\n  Sample metadata fields: {list(sample_metadata.keys())[:10]}")
                if "text" in sample_metadata:
                    text_preview = sample_metadata["text"][:100] + "..." if len(sample_metadata["text"]) > 100 else sample_metadata["text"]
                    print(f"  Text field found: {text_preview}")
                print()

            print("=" * 60)
            print("Extraction completed successfully!")
            print("=" * 60)
            print()
            print("Next step: Run with --step upload --input", output_file)
            return True

        except Exception as e:
            print(f"✗ Error saving to file: {e}")
            import traceback

            traceback.print_exc()
            return False


class QdrantUploader:
    """Loads vectors from file and uploads to Qdrant"""

    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: Optional[str],
        qdrant_collection_name: str,
        batch_size: int = 100,
    ):
        """
        Initialize the uploader.

        Args:
            qdrant_url: Qdrant server URL
            qdrant_api_key: Qdrant API key (optional)
            qdrant_collection_name: Name of Qdrant collection to create/use
            batch_size: Number of vectors to process in each batch
        """
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key
        self.qdrant_collection_name = qdrant_collection_name
        self.batch_size = batch_size

        # Initialize Qdrant client
        print("Initializing Qdrant client...")
        if qdrant_api_key:
            self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.qdrant_client = QdrantClient(url=qdrant_url)

    def check_qdrant_connection(self) -> bool:
        """Check if Qdrant is accessible"""
        try:
            collections = self.qdrant_client.get_collections()
            print(f"✓ Qdrant connection successful at {self.qdrant_url}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Qdrant: {e}")
            return False

    def drop_collection_if_exists(self) -> bool:
        """Drop Qdrant collection if it exists"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.qdrant_collection_name in collection_names:
                print(f"Dropping existing collection '{self.qdrant_collection_name}'...")
                self.qdrant_client.delete_collection(self.qdrant_collection_name)
                print(f"✓ Collection '{self.qdrant_collection_name}' dropped successfully")
                return True
            else:
                print(f"Collection '{self.qdrant_collection_name}' does not exist (nothing to drop)")
                return True
        except Exception as e:
            print(f"✗ Failed to drop collection: {e}")
            return False

    def create_qdrant_collection(self, vector_dimension: int, drop_existing: bool = True) -> bool:
        """
        Create Qdrant collection. Optionally drops existing collection first.
        
        Args:
            vector_dimension: Dimension of the vectors
            drop_existing: If True, drop existing collection before creating new one
        """
        try:
            # Drop existing collection if requested
            if drop_existing:
                if not self.drop_collection_if_exists():
                    return False
                print()

            # Check if collection still exists (shouldn't if we just dropped it)
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.qdrant_collection_name in collection_names:
                print(
                    f"Collection '{self.qdrant_collection_name}' already exists"
                )
                # Verify collection configuration
                collection_info = self.qdrant_client.get_collection(
                    self.qdrant_collection_name
                )
                print(
                    f"  Vector size: {collection_info.config.params.vectors.size}"
                )
                print(
                    f"  Distance: {collection_info.config.params.vectors.distance}"
                )
                return True

            # Create collection
            print(f"Creating Qdrant collection '{self.qdrant_collection_name}'...")
            self.qdrant_client.create_collection(
                collection_name=self.qdrant_collection_name,
                vectors_config=VectorParams(
                    size=vector_dimension,
                    distance=Distance.COSINE,
                ),
            )
            print(
                f"✓ Collection '{self.qdrant_collection_name}' created successfully"
            )
            return True
        except Exception as e:
            print(f"✗ Failed to create collection: {e}")
            return False

    def load_from_file(self, input_file: str) -> Dict[str, Any]:
        """
        Load vectors from pickle file.

        Args:
            input_file: Path to input pickle file

        Returns:
            Dictionary with metadata and vectors
        """
        print(f"Loading data from {input_file}...")
        try:
            with open(input_file, "rb") as f:
                data = pickle.load(f)

            if "metadata" not in data or "vectors" not in data:
                raise ValueError(
                    "Invalid file format: missing 'metadata' or 'vectors' keys"
                )

            metadata = data["metadata"]
            vectors = data["vectors"]

            print(f"✓ Loaded {len(vectors)} vectors from file")
            print(f"  Extraction date: {metadata.get('extraction_date', 'unknown')}")
            print(f"  Pinecone index: {metadata.get('pinecone_index', 'unknown')}")
            print(f"  Vector dimension: {metadata.get('vector_dimension', 'unknown')}")
            print()

            return data

        except Exception as e:
            print(f"✗ Error loading file: {e}")
            import traceback

            traceback.print_exc()
            raise

    def _convert_to_langchain_format(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Pinecone metadata to LangChain Qdrant format.
        
        LangChain Qdrant expects:
        - page_content: The main text content
        - metadata: Dictionary with all other fields
        
        Args:
            metadata: Original metadata from Pinecone
            
        Returns:
            Dictionary with page_content and metadata keys
        """
        # Identify the text field (common field names: text, content, page_content)
        text_field = None
        for field in ["text", "content", "page_content"]:
            if field in metadata:
                text_field = field
                break
        
        if not text_field:
            # If no text field found, try to use the first string value or empty string
            print("⚠ Warning: No 'text', 'content', or 'page_content' field found in metadata")
            print(f"  Available fields: {list(metadata.keys())[:5]}")
            # Use empty string as fallback, or try to find any string field
            page_content = ""
            for key, value in metadata.items():
                if isinstance(value, str) and len(value) > len(page_content):
                    page_content = value
                    text_field = key
            if not page_content:
                page_content = ""  # Fallback to empty string
        else:
            page_content = metadata[text_field]
        
        # Create metadata dict without the text field
        langchain_metadata = {k: v for k, v in metadata.items() if k != text_field}
        
        # Return in LangChain format
        return {
            "page_content": page_content,
            "metadata": langchain_metadata
        }

    def insert_vectors_to_qdrant(
        self, vectors: List[Dict[str, Any]]
    ) -> bool:
        """
        Insert vectors into Qdrant collection in LangChain-compatible format.

        Args:
            vectors: List of vectors with IDs, values, and metadata

        Returns:
            True if successful, False otherwise
        """
        if not vectors:
            print("No vectors to insert")
            return True

        print(f"\nInserting {len(vectors)} vectors into Qdrant...")
        print("Converting to LangChain format (page_content + metadata)...")
        
        # Show sample conversion
        if vectors:
            sample_vec = vectors[0]
            sample_langchain = self._convert_to_langchain_format(sample_vec["metadata"])
            print(f"  Sample conversion:")
            print(f"    page_content length: {len(sample_langchain['page_content'])} chars")
            print(f"    metadata keys: {list(sample_langchain['metadata'].keys())[:5]}")
        print()

        try:
            # Process vectors in batches
            total_batches = (len(vectors) + self.batch_size - 1) // self.batch_size
            inserted_count = 0

            for batch_num in range(total_batches):
                start_idx = batch_num * self.batch_size
                end_idx = min(start_idx + self.batch_size, len(vectors))
                batch = vectors[start_idx:end_idx]

                # Convert to Qdrant PointStruct format with LangChain structure
                points = []
                for vec in batch:
                    # Qdrant requires integer or UUID IDs
                    # Convert string IDs to integers if possible, otherwise use hash
                    point_id = self._convert_id(vec["id"])

                    # Convert metadata to LangChain format
                    langchain_data = self._convert_to_langchain_format(vec["metadata"])
                    
                    # Create payload with page_content and metadata as LangChain expects
                    payload = {
                        "page_content": langchain_data["page_content"],
                        "metadata": langchain_data["metadata"]
                    }

                    point = PointStruct(
                        id=point_id,
                        vector=vec["vector"],
                        payload=payload,
                    )
                    points.append(point)

                # Insert batch into Qdrant
                self.qdrant_client.upsert(
                    collection_name=self.qdrant_collection_name, points=points
                )

                inserted_count += len(batch)
                progress = (inserted_count / len(vectors)) * 100
                print(
                    f"  Progress: {inserted_count}/{len(vectors)} vectors ({progress:.1f}%)"
                )

                # Small delay to avoid overwhelming the server
                time.sleep(0.1)

            print(f"✓ Successfully inserted {inserted_count} vectors into Qdrant")
            return True

        except Exception as e:
            print(f"✗ Error inserting vectors into Qdrant: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _convert_id(self, id_str: str) -> int:
        """
        Convert string ID to integer for Qdrant.

        Qdrant supports both integer and UUID IDs. This function converts
        string IDs to integers using a hash function to ensure consistency.

        Args:
            id_str: String ID from Pinecone

        Returns:
            Integer ID for Qdrant
        """
        # Use hash to convert string to integer
        # This ensures consistent mapping
        return abs(hash(id_str)) % (2**63)  # Keep within int64 range

    def verify_migration(self, expected_count: int) -> bool:
        """Verify that all vectors were migrated successfully"""
        print("\nVerifying migration...")
        try:
            collection_info = self.qdrant_client.get_collection(
                self.qdrant_collection_name
            )
            actual_count = collection_info.points_count

            print(f"Expected vectors: {expected_count}")
            print(f"Actual vectors in Qdrant: {actual_count}")

            if actual_count == expected_count:
                print("✓ Migration verification successful")
                return True
            else:
                print(
                    f"⚠ Warning: Vector count mismatch (expected {expected_count}, got {actual_count})"
                )
                return False

        except Exception as e:
            print(f"✗ Error verifying migration: {e}")
            return False

    def upload_from_file(self, input_file: str, drop_existing: bool = True) -> bool:
        """
        Load vectors from file and upload to Qdrant.

        Args:
            input_file: Path to input pickle file

        Returns:
            True if successful, False otherwise
        """
        print("=" * 60)
        print("STEP 2: Upload Data to Qdrant")
        print("=" * 60)
        print()

        # Check connection
        print("Checking Qdrant connection...")
        if not self.check_qdrant_connection():
            return False
        print()

        # Load data from file
        try:
            data = self.load_from_file(input_file)
            vectors = data["vectors"]
            metadata = data["metadata"]
            vector_dimension = metadata.get("vector_dimension", 3072)
        except Exception as e:
            print(f"✗ Failed to load data: {e}")
            return False

        # Create collection (will drop existing if requested)
        print("Setting up Qdrant collection...")
        if drop_existing:
            print("Note: Existing collection will be dropped and recreated")
        if not self.create_qdrant_collection(vector_dimension, drop_existing=drop_existing):
            return False
        print()

        # Insert vectors
        print("Inserting vectors into Qdrant...")
        if not self.insert_vectors_to_qdrant(vectors):
            return False
        print()

        # Verify migration
        print("Verifying migration...")
        self.verify_migration(len(vectors))
        print()

        print("=" * 60)
        print("Upload completed successfully!")
        print("=" * 60)
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate vectors from Pinecone to Qdrant (two-step process)"
    )
    parser.add_argument(
        "--step",
        choices=["extract", "upload"],
        required=True,
        help="Step to execute: 'extract' to pull from Pinecone, 'upload' to push to Qdrant",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for extract step (default: pinecone_data.pkl)",
        default="pinecone_data.pkl",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input file path for upload step (default: pinecone_data.pkl)",
        default="pinecone_data.pkl",
    )
    parser.add_argument(
        "--vector-ids-file",
        type=str,
        help="Optional file containing vector IDs (one per line) for extract step",
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        help="Don't drop existing collection before uploading (default: drops existing collection)",
    )

    args = parser.parse_args()

    if args.step == "extract":
        # Step 1: Extract from Pinecone
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "informasi-umum-itb")

        if not pinecone_api_key:
            print("Error: PINECONE_API_KEY environment variable is required")
            sys.exit(1)

        print("Extraction Configuration:")
        print(f"  Pinecone Index: {pinecone_index_name}")
        print(f"  Output File: {args.output}")
        print()

        # Load vector IDs if provided
        vector_ids = None
        if args.vector_ids_file and os.path.exists(args.vector_ids_file):
            print(f"Reading vector IDs from {args.vector_ids_file}...")
            with open(args.vector_ids_file, "r") as f:
                vector_ids = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(vector_ids)} vector IDs from file")
            print()

        extractor = PineconeExtractor(
            pinecone_api_key=pinecone_api_key,
            pinecone_index_name=pinecone_index_name,
        )

        success = extractor.extract_and_save(args.output, vector_ids=vector_ids)

        if success:
            print("\n✓ Extraction completed successfully!")
            print(f"\nData saved to: {args.output}")
            print("\nNext step: Run with --step upload --input", args.output)
            sys.exit(0)
        else:
            print("\n✗ Extraction failed. Please check the errors above.")
            sys.exit(1)

    elif args.step == "upload":
        # Step 2: Upload to Qdrant
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        qdrant_collection_name = os.getenv(
            "QDRANT_COLLECTION_NAME", "informasi-umum-itb"
        )
        batch_size = int(os.getenv("MIGRATION_BATCH_SIZE", "100"))

        if not qdrant_url:
            print("Error: QDRANT_URL environment variable is required")
            sys.exit(1)

        if not os.path.exists(args.input):
            print(f"Error: Input file '{args.input}' does not exist")
            print("Please run the extract step first:")
            print(f"  python {sys.argv[0]} --step extract --output {args.input}")
            sys.exit(1)

        print("Upload Configuration:")
        print(f"  Qdrant URL: {qdrant_url}")
        print(f"  Qdrant Collection: {qdrant_collection_name}")
        print(f"  Input File: {args.input}")
        print(f"  Batch Size: {batch_size}")
        print()

        uploader = QdrantUploader(
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
            qdrant_collection_name=qdrant_collection_name,
            batch_size=batch_size,
        )

        # Drop existing collection by default (unless --no-drop flag is set)
        drop_existing = not args.no_drop
        success = uploader.upload_from_file(args.input, drop_existing=drop_existing)

        if success:
            print("\n✓ Upload completed successfully!")
            print("\nNext steps:")
            print("1. Update your code to use Qdrant instead of Pinecone")
            print("2. Test your application with the new Qdrant vector store")
            print("3. Once verified, you can remove Pinecone configuration")
            sys.exit(0)
        else:
            print("\n✗ Upload failed. Please check the errors above.")
            sys.exit(1)


if __name__ == "__main__":
    main()
