#!/usr/bin/env python3
"""
Script to restore Qdrant collection from snapshot on first startup.
This script is designed to run in a Docker container after Qdrant is ready.
"""

import os
import sys
import time
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    import requests
except ImportError:
    print("Error: qdrant-client and requests packages are required")
    print("Run: pip install qdrant-client requests")
    sys.exit(1)


def wait_for_qdrant(url: str, max_attempts: int = 30) -> bool:
    """Wait for Qdrant to be ready"""
    import urllib.request
    import urllib.error

    print("Waiting for Qdrant to be ready...")
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(f"{url}/health")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print("✓ Qdrant is ready")
                    return True
        except Exception:
            pass

        print(f"  Attempt {attempt}/{max_attempts}...")
        time.sleep(2)

    print("✗ Qdrant did not become ready in time")
    return False


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    """Check if collection exists"""
    try:
        collections = client.get_collections()
        return collection_name in [col.name for col in collections.collections]
    except Exception:
        return False


def restore_snapshot(
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    snapshot_path: str,
) -> bool:
    """Restore collection from snapshot"""
    print("=" * 60)
    print("Qdrant Snapshot Restore")
    print("=" * 60)
    print()

    # Wait for Qdrant
    if not wait_for_qdrant(qdrant_url):
        return False

    print()

    # Initialize client
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)

    # Check if collection exists (fast check - avoids unnecessary restore)
    print(f"Checking if collection '{collection_name}' exists...")
    if collection_exists(client, collection_name):
        collection_info = client.get_collection(collection_name)
        point_count = collection_info.points_count
        print(f"✓ Collection '{collection_name}' already exists")
        print(f"  Points: {point_count}")
        print("  Data persists from previous session - skipping snapshot restore")
        print("  (This is expected when using persistent Docker volumes)")
        return True

    print("  Collection does not exist")
    print()

    # Check if snapshot exists
    snapshot_file = Path(snapshot_path)
    if not snapshot_file.exists():
        print(f"⚠ Snapshot file not found: {snapshot_path}")
        print("  Skipping snapshot restore")
        print("  Collection will be created when data is inserted")
        return True

    print(f"✓ Snapshot file found: {snapshot_path}")
    file_size = snapshot_file.stat().st_size / (1024 * 1024)  # Size in MB
    print(f"  Size: {file_size:.2f} MB")
    print()

    # Upload and restore snapshot
    print("Uploading snapshot to Qdrant...")
    try:
        # Use REST API to upload snapshot (more reliable than client method)
        upload_url = f"{qdrant_url}/collections/{collection_name}/snapshots/upload?priority=snapshot"
        
        headers = {}
        if qdrant_api_key:
            headers["api-key"] = qdrant_api_key
        
        with open(snapshot_path, "rb") as f:
            files = {"snapshot": (os.path.basename(snapshot_path), f, "application/octet-stream")}
            response = requests.post(upload_url, headers=headers, files=files, timeout=300)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")

        print("✓ Snapshot uploaded successfully")
        print()

        # Wait for processing
        print("Waiting for snapshot to be processed...")
        time.sleep(3)

        # Verify collection exists
        max_verify_attempts = 10
        for attempt in range(1, max_verify_attempts + 1):
            if collection_exists(client, collection_name):
                collection_info = client.get_collection(collection_name)
                point_count = collection_info.points_count
                print(f"✓ Collection '{collection_name}' restored successfully")
                print(f"  Points restored: {point_count}")
                return True
            print(f"  Verification attempt {attempt}/{max_verify_attempts}...")
            time.sleep(2)

        print("⚠ Collection not found after restore (may still be processing)")
        return True

    except Exception as e:
        print(f"✗ Failed to restore snapshot: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb")
    snapshot_dir = os.getenv("SNAPSHOT_DIR", "/snapshots")
    snapshot_file = os.getenv(
        "SNAPSHOT_FILE", f"{collection_name}_latest.snapshot"
    )
    snapshot_path = os.path.join(snapshot_dir, snapshot_file)

    print("=" * 60)
    print("Qdrant Snapshot Restore Service")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Qdrant URL: {qdrant_url}")
    print(f"  Collection: {collection_name}")
    print(f"  Snapshot Path: {snapshot_path}")
    print()
    print("Note: This service only restores if collection doesn't exist.")
    print("      If collection exists (from persistent volume), restore is skipped.")
    print()

    success = restore_snapshot(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=collection_name,
        snapshot_path=snapshot_path,
    )

    if success:
        print()
        print("=" * 60)
        print("Snapshot restore completed")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("Snapshot restore failed")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

