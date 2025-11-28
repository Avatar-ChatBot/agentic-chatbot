# Qdrant Snapshots

This directory stores Qdrant collection snapshots for backup and deployment.

## Creating a Snapshot

After migrating data to Qdrant, create a snapshot:

```bash
python scripts/create_qdrant_snapshot.py
```

This will:
1. Connect to your Qdrant instance
2. Create a snapshot of the `informasi-umum-itb` collection
3. Download and save it to this directory with a timestamp
4. Create a symlink `informasi-umum-itb_latest.snapshot` pointing to the latest snapshot

## Snapshot Files

- `informasi-umum-itb_YYYYMMDD_HHMMSS.snapshot` - Timestamped snapshot files
- `informasi-umum-itb_latest.snapshot` - Symlink to the latest snapshot

## Automatic Restoration

When you start Docker Compose, the `qdrant-restore` service will:
1. Wait for Qdrant to be ready
2. Check if the collection exists
3. If the collection doesn't exist and a snapshot is available, restore from the snapshot
4. If the collection already exists, skip restoration

## Best Practices

1. **Create snapshots regularly** - Especially after major data updates
2. **Store snapshots securely** - These files contain your vector data
3. **Version control** - Consider storing snapshots in a separate repository or cloud storage
4. **Test restoration** - Periodically test that snapshots can be restored successfully

## Manual Restoration

If you need to manually restore a snapshot:

```bash
# Using the Python script
python scripts/restore_qdrant_snapshot.py

# Or using curl
curl -X POST "http://localhost:6333/collections/informasi-umum-itb/snapshots/upload" \
     -H "api-key: YOUR_API_KEY" \
     -F "snapshot=@qdrant_snapshots/informasi-umum-itb_latest.snapshot"
```

## Environment Variables

- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
- `QDRANT_API_KEY` - Qdrant API key (optional for local)
- `QDRANT_COLLECTION_NAME` - Collection name (default: informasi-umum-itb)

