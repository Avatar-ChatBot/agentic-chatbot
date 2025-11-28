# Qdrant Snapshot Guide

This guide explains how to create and use Qdrant snapshots for backup and deployment.

## Overview

Snapshots allow you to:
- **Backup** your Qdrant collection data
- **Restore** data quickly on new deployments
- **Version** your vector database state

## Step 1: Create a Snapshot

After you've migrated data to Qdrant and verified it's working:

```bash
# Make sure Qdrant is running and has your data
docker-compose up -d qdrant

# Create a snapshot
python create_qdrant_snapshot.py
```

The script will:
1. Connect to your Qdrant instance
2. Create a snapshot of the `informasi-umum-itb` collection
3. Download and save it to `qdrant_snapshots/` directory
4. Create a symlink `informasi-umum-itb_latest.snapshot` for easy access

**Output:**
```
✓ Snapshot created successfully
  Snapshot name: informasi-umum-itb-1234567890.snapshot
  Snapshot size: 12345678 bytes

✓ Snapshot downloaded successfully
  File: qdrant_snapshots/informasi-umum-itb_20250101_120000.snapshot
  Size: 11.78 MB
```

## Step 2: Verify Snapshot

Check that the snapshot file was created:

```bash
ls -lh qdrant_snapshots/
```

You should see:
- A timestamped snapshot file
- A `_latest.snapshot` symlink

## Step 3: Automatic Restoration on Docker Startup

The Docker Compose setup is configured to automatically restore from snapshot:

1. **On first startup** (when collection doesn't exist):
   - The `qdrant-restore` service waits for Qdrant to be ready
   - Checks if collection exists
   - If not, restores from `qdrant_snapshots/informasi-umum-itb_latest.snapshot`
   - Collection is ready with all your data

2. **On subsequent startups** (when collection exists):
   - Skips restoration (data persists in Docker volume)
   - Uses existing collection

## Docker Configuration

The `docker-compose.yml` includes:

```yaml
qdrant:
  volumes:
    - qdrant_data:/qdrant/storage
    - ./qdrant_snapshots:/qdrant/snapshots:ro  # Snapshots directory

qdrant-restore:
  depends_on:
    qdrant:
      condition: service_healthy
  volumes:
    - ./qdrant_snapshots:/snapshots:ro
  # Automatically restores on startup
```

## Best Practices

### 1. Regular Snapshots
Create snapshots after:
- Initial data migration
- Major data updates
- Before deployments
- After successful migrations

### 2. Snapshot Storage
- **Local**: Keep in `qdrant_snapshots/` for development
- **Production**: Store in cloud storage (S3, GCS, etc.)
- **Version Control**: Consider a separate repository for snapshots

### 3. Testing Restoration
Periodically test restoration:
```bash
# Start fresh (remove volumes)
docker-compose down -v
docker-compose up -d

# Check logs
docker-compose logs qdrant-restore
```

### 4. Snapshot Size
Snapshots are compressed but can be large:
- Monitor disk space
- Consider cleanup of old snapshots
- Keep only the latest few versions

## Manual Operations

### Create Snapshot with Custom Options
```bash
python create_qdrant_snapshot.py \
  --collection informasi-umum-itb \
  --output-dir qdrant_snapshots
```

### Manual Restoration
If you need to restore manually:

```bash
# Using Python script
python restore_qdrant_snapshot.py

# Or using Qdrant client
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
with open("qdrant_snapshots/informasi-umum-itb_latest.snapshot", "rb") as f:
    client.upload_snapshot(
        collection_name="informasi-umum-itb",
        snapshot=f.read(),
        priority="snapshot"
    )
```

## Troubleshooting

### Snapshot Creation Fails
- **Check Qdrant is running**: `docker-compose ps qdrant`
- **Verify collection exists**: Check Qdrant dashboard
- **Check API key**: Ensure `QDRANT_API_KEY` is set if required

### Restoration Fails
- **Check snapshot file exists**: `ls qdrant_snapshots/`
- **Check file permissions**: Ensure readable
- **Check Qdrant logs**: `docker-compose logs qdrant`
- **Check restore logs**: `docker-compose logs qdrant-restore`

### Collection Not Restored
- **Check if collection exists**: May already exist from previous run
- **Check restore service logs**: `docker-compose logs qdrant-restore`
- **Verify snapshot file**: Ensure `_latest.snapshot` symlink is valid

## Environment Variables

Configure via `.env` file or environment:

```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key_here
QDRANT_COLLECTION_NAME=informasi-umum-itb
```

## Files Created

- `create_qdrant_snapshot.py` - Script to create snapshots
- `restore_qdrant_snapshot.py` - Script to restore snapshots
- `restore_qdrant_snapshot.sh` - Shell script alternative (not used by default)
- `qdrant_snapshots/` - Directory for snapshot files
- Updated `docker-compose.yml` - Includes restore service

## Next Steps

1. ✅ Create snapshot after data migration
2. ✅ Test restoration in a fresh environment
3. ✅ Set up regular snapshot schedule (cron job, CI/CD, etc.)
4. ✅ Store snapshots in secure backup location
5. ✅ Document snapshot versioning strategy

