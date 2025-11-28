# Qdrant Docker Volume Management Guide

This guide explains how Qdrant data persistence works in Docker and how snapshot restoration is efficiently managed.

## How Data Persistence Works

### Docker Volumes

Qdrant uses a **persistent Docker volume** (`qdrant_data`) to store all collection data:

```yaml
volumes:
  qdrant_data:
    driver: local
```

This volume:
- ✅ **Persists data** across container restarts
- ✅ **Survives** `docker-compose down` (data remains)
- ✅ **Only deleted** with `docker-compose down -v` (explicit volume removal)

### Data Location

- **Inside container**: `/qdrant/storage` (Qdrant's data directory)
- **Docker volume**: Managed by Docker (typically in `/var/lib/docker/volumes/`)
- **Data persists** automatically - no manual intervention needed

## Snapshot Restoration Strategy

### When Snapshots Are Restored

The `qdrant-restore` service **only restores** when:

1. ✅ Qdrant is healthy and ready
2. ✅ Collection **does NOT exist** (first-time setup or volume was deleted)
3. ✅ Snapshot file is available

### When Snapshots Are Skipped

Restoration is **skipped** (fast exit) when:

1. ✅ Collection **already exists** (data persists from previous session)
2. ✅ No snapshot file found (collection will be created when data is inserted)

### Efficiency Features

1. **Fast Collection Check**: First checks if collection exists before attempting restore
2. **Immediate Exit**: If collection exists, service exits immediately (no API calls)
3. **Conditional Restore**: Only uploads snapshot if collection is missing
4. **One-Time Service**: `restart: "no"` - only runs on startup, doesn't restart

## Common Scenarios

### Scenario 1: Normal Startup (Collection Exists)

```
1. Docker Compose starts
2. Qdrant starts and loads data from persistent volume
3. qdrant-restore checks: Collection exists ✓
4. Service exits immediately (no restore needed)
5. Total time: ~2 seconds
```

### Scenario 2: First-Time Setup (No Collection)

```
1. Docker Compose starts
2. Qdrant starts (empty volume)
3. qdrant-restore checks: Collection doesn't exist
4. Snapshot file found
5. Uploads and restores snapshot
6. Collection created with all data
7. Total time: ~30-60 seconds (depends on snapshot size)
```

### Scenario 3: Fresh Start (Volume Deleted)

```bash
# Remove volumes and start fresh
docker-compose down -v
docker-compose up -d

# Result: Snapshot will be restored automatically
```

## Volume Management Commands

### Check Volume Status

```bash
# List volumes
docker volume ls

# Inspect qdrant volume
docker volume inspect agentic-chatbot_qdrant_data

# Check volume size
docker system df -v
```

### Backup Volume

```bash
# Backup volume to tar file
docker run --rm \
  -v agentic-chatbot_qdrant_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant_backup.tar.gz -C /data .
```

### Restore Volume from Backup

```bash
# Stop Qdrant
docker-compose stop qdrant

# Remove existing volume
docker volume rm agentic-chatbot_qdrant_data

# Create new volume and restore
docker run --rm \
  -v agentic-chatbot_qdrant_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/qdrant_backup.tar.gz -C /data

# Start Qdrant
docker-compose start qdrant
```

## Best Practices

### 1. Use Snapshots for Deployment

- **Create snapshots** after data migration or major updates
- **Store snapshots** in version control or cloud storage
- **Restore on first deploy** - subsequent restarts use persistent volume

### 2. Preserve Volumes

- **Don't use `-v` flag** unless you want to delete data:
  ```bash
  # ❌ DON'T: This deletes all data
  docker-compose down -v
  
  # ✅ DO: This preserves data
  docker-compose down
  docker-compose up -d
  ```

### 3. Monitor Volume Size

```bash
# Check volume size
docker system df -v | grep qdrant_data
```

### 4. Regular Snapshots

Create snapshots regularly:
```bash
python scripts/create_qdrant_snapshot.py
```

## Troubleshooting

### Collection Not Persisting

**Problem**: Collection disappears after restart

**Solution**: Check volume mount:
```bash
# Verify volume is mounted
docker-compose exec qdrant ls -la /qdrant/storage

# Check volume exists
docker volume ls | grep qdrant_data
```

### Snapshot Restores Every Time

**Problem**: Snapshot restores on every startup

**Solution**: Check if collection exists:
```bash
# Check collection
curl http://localhost:6333/collections/informasi-umum-itb

# Check restore logs
docker-compose logs qdrant-restore
```

### Volume Too Large

**Problem**: Volume growing too large

**Solution**: 
1. Create fresh snapshot
2. Remove old volume: `docker-compose down -v`
3. Restore from snapshot on next startup

## Summary

- ✅ **Data persists** automatically in Docker volumes
- ✅ **Snapshot restores** only when collection doesn't exist
- ✅ **Fast startup** when collection already exists
- ✅ **No manual intervention** needed for normal operations

The system is designed to be efficient: it checks for existing data first, and only restores from snapshot when necessary.

