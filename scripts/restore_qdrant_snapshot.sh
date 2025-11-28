#!/bin/bash
# Script to restore Qdrant collection from snapshot on first startup
# This script is designed to run inside the Qdrant Docker container

set -e

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
QDRANT_API_KEY="${QDRANT_API_KEY:-}"
COLLECTION_NAME="${QDRANT_COLLECTION_NAME:-informasi-umum-itb}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-/qdrant/snapshots}"
SNAPSHOT_FILE="${SNAPSHOT_FILE:-${COLLECTION_NAME}_latest.snapshot}"

echo "=========================================="
echo "Qdrant Snapshot Restore Script"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Qdrant URL: $QDRANT_URL"
echo "  Collection: $COLLECTION_NAME"
echo "  Snapshot Directory: $SNAPSHOT_DIR"
echo "  Snapshot File: $SNAPSHOT_FILE"
echo ""

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f -s "${QDRANT_URL}/health" > /dev/null 2>&1; then
        echo "✓ Qdrant is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "✗ Qdrant did not become ready in time"
    exit 1
fi

# Check if collection already exists
echo ""
echo "Checking if collection '$COLLECTION_NAME' exists..."
if curl -f -s "${QDRANT_URL}/collections/${COLLECTION_NAME}" > /dev/null 2>&1; then
    echo "✓ Collection '$COLLECTION_NAME' already exists"
    echo "  Skipping snapshot restore"
    exit 0
fi

echo "  Collection does not exist"
echo ""

# Check if snapshot file exists
SNAPSHOT_PATH="${SNAPSHOT_DIR}/${SNAPSHOT_FILE}"
if [ ! -f "$SNAPSHOT_PATH" ]; then
    echo "⚠ Snapshot file not found: $SNAPSHOT_PATH"
    echo "  Available files in $SNAPSHOT_DIR:"
    ls -lh "$SNAPSHOT_DIR" 2>/dev/null || echo "    (directory not found or empty)"
    echo ""
    echo "  Skipping snapshot restore"
    echo "  Collection will be created when data is inserted"
    exit 0
fi

echo "✓ Snapshot file found: $SNAPSHOT_PATH"
SNAPSHOT_SIZE=$(du -h "$SNAPSHOT_PATH" | cut -f1)
echo "  Size: $SNAPSHOT_SIZE"
echo ""

# Upload and restore snapshot
echo "Uploading snapshot to Qdrant..."
UPLOAD_URL="${QDRANT_URL}/collections/${COLLECTION_NAME}/snapshots/upload"

if [ -n "$QDRANT_API_KEY" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        -H "api-key: ${QDRANT_API_KEY}" \
        -F "snapshot=@${SNAPSHOT_PATH}" \
        "${UPLOAD_URL}")
else
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        -F "snapshot=@${SNAPSHOT_PATH}" \
        "${UPLOAD_URL}")
fi

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo "✓ Snapshot uploaded successfully"
    echo ""
    
    # Wait a moment for Qdrant to process
    echo "Waiting for snapshot to be processed..."
    sleep 3
    
    # Verify collection exists
    if curl -f -s "${QDRANT_URL}/collections/${COLLECTION_NAME}" > /dev/null 2>&1; then
        echo "✓ Collection '$COLLECTION_NAME' restored successfully"
        
        # Get collection info
        COLLECTION_INFO=$(curl -s "${QDRANT_URL}/collections/${COLLECTION_NAME}")
        POINT_COUNT=$(echo "$COLLECTION_INFO" | grep -o '"points_count":[0-9]*' | cut -d':' -f2 || echo "unknown")
        echo "  Points restored: $POINT_COUNT"
    else
        echo "⚠ Collection not found after restore (may still be processing)"
    fi
else
    echo "✗ Failed to upload snapshot"
    echo "  HTTP Code: $HTTP_CODE"
    echo "  Response: $BODY"
    exit 1
fi

echo ""
echo "=========================================="
echo "Snapshot restore completed"
echo "=========================================="

