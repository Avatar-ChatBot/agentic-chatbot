#!/usr/bin/env python3
"""
Script to create a Qdrant snapshot for backup and deployment.

This script:
1. Connects to Qdrant
2. Creates a snapshot of the specified collection
3. Downloads the snapshot file to the local filesystem
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    from qdrant_client import QdrantClient
    import requests
except ImportError:
    print("Error: qdrant-client and requests packages are required")
    print("Run: pip install qdrant-client requests")
    sys.exit(1)


def create_snapshot(
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    output_dir: str = "qdrant_snapshots",
) -> str:
    """
    Create a snapshot of a Qdrant collection and download it.

    Args:
        qdrant_url: Qdrant server URL
        qdrant_api_key: Qdrant API key (optional)
        collection_name: Name of the collection to snapshot
        output_dir: Directory to save the snapshot file

    Returns:
        Path to the downloaded snapshot file
    """
    print("=" * 60)
    print("Creating Qdrant Snapshot")
    print("=" * 60)
    print()

    # Initialize Qdrant client
    print(f"Connecting to Qdrant at {qdrant_url}...")
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)

    # Check connection
    try:
        collections = client.get_collections()
        print(f"✓ Connected to Qdrant")
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        sys.exit(1)

    # Check if collection exists
    collection_names = [col.name for col in collections.collections]
    if collection_name not in collection_names:
        print(f"✗ Collection '{collection_name}' does not exist")
        print(f"  Available collections: {collection_names}")
        sys.exit(1)

    print(f"✓ Collection '{collection_name}' found")
    print()

    # Get collection info
    try:
        collection_info = client.get_collection(collection_name)
        point_count = collection_info.points_count
        print(f"Collection info:")
        print(f"  Points: {point_count}")
        print(f"  Vector size: {collection_info.config.params.vectors.size}")
        print(f"  Distance: {collection_info.config.params.vectors.distance}")
        print()
    except Exception as e:
        print(f"⚠ Warning: Could not get collection info: {e}")
        print()

    # Create snapshot
    print(f"Creating snapshot for collection '{collection_name}'...")
    try:
        snapshot_info = client.create_snapshot(collection_name=collection_name)
        print(f"✓ Snapshot created successfully")
        print(f"  Snapshot name: {snapshot_info.name}")
        print(f"  Snapshot size: {snapshot_info.size} bytes")
        print()
    except Exception as e:
        print(f"✗ Failed to create snapshot: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Download snapshot using REST API
    print("Downloading snapshot...")
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"{collection_name}_{timestamp}.snapshot"
        snapshot_path = os.path.join(output_dir, snapshot_filename)

        # Download snapshot using REST API
        # Qdrant REST API: GET /collections/{collection_name}/snapshots/{snapshot_name}
        download_url = f"{qdrant_url}/collections/{collection_name}/snapshots/{snapshot_info.name}"
        
        headers = {}
        if qdrant_api_key:
            headers["api-key"] = qdrant_api_key
        
        print(f"  Downloading from: {download_url}")
        print(f"  Snapshot name: {snapshot_info.name}")
        
        response = requests.get(download_url, headers=headers, stream=True, timeout=300)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download snapshot: {response.status_code} - {response.text}")

        # Save to file
        with open(snapshot_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(snapshot_path) / (1024 * 1024)  # Size in MB
        print(f"✓ Snapshot downloaded successfully")
        print(f"  File: {snapshot_path}")
        print(f"  Size: {file_size:.2f} MB")
        print()

        # Also create a symlink to latest snapshot
        latest_path = os.path.join(output_dir, f"{collection_name}_latest.snapshot")
        if os.path.exists(latest_path):
            os.remove(latest_path)
        os.symlink(snapshot_filename, latest_path)
        print(f"✓ Created symlink: {latest_path} -> {snapshot_filename}")
        print()

        print("=" * 60)
        print("Snapshot creation completed successfully!")
        print("=" * 60)
        print()
        print(f"Snapshot saved to: {snapshot_path}")
        print(f"Latest snapshot: {latest_path}")
        print()
        print("Next steps:")
        print("1. Add snapshot to your repository (or store securely)")
        print("2. Update docker-compose.yml to restore from snapshot on startup")

        return snapshot_path

    except Exception as e:
        print(f"✗ Failed to download snapshot: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Create a Qdrant snapshot")
    parser.add_argument(
        "--collection",
        type=str,
        default=os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb"),
        help="Collection name to snapshot (default: from QDRANT_COLLECTION_NAME env var)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="qdrant_snapshots",
        help="Directory to save snapshot (default: qdrant_snapshots)",
    )

    args = parser.parse_args()

    # Get configuration from environment
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    print("Snapshot Configuration:")
    print(f"  Qdrant URL: {qdrant_url}")
    print(f"  Collection: {args.collection}")
    print(f"  Output Directory: {args.output_dir}")
    print()

    snapshot_path = create_snapshot(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=args.collection,
        output_dir=args.output_dir,
    )

    sys.exit(0)


if __name__ == "__main__":
    main()

