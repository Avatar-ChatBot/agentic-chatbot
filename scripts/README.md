# Scripts Directory

This directory contains utility scripts for managing the Qdrant migration and snapshots.

## Scripts

### Migration Scripts

- **`migrate_pinecone_to_qdrant.py`** - Two-step migration from Pinecone to Qdrant
  - Step 1: Extract data from Pinecone and save to pickle file
  - Step 2: Upload data from pickle file to Qdrant
  
  Usage:
  ```bash
  # Step 1: Extract from Pinecone
  python scripts/migrate_pinecone_to_qdrant.py --step extract --output pinecone_data.pkl
  
  # Step 2: Upload to Qdrant
  python scripts/migrate_pinecone_to_qdrant.py --step upload --input pinecone_data.pkl
  ```

### Snapshot Scripts

- **`create_qdrant_snapshot.py`** - Create a snapshot of a Qdrant collection
  
  Usage:
  ```bash
  python scripts/create_qdrant_snapshot.py
  ```

- **`restore_qdrant_snapshot.py`** - Restore a Qdrant collection from snapshot
  - Used automatically by Docker Compose on startup
  - Can also be run manually if needed
  
  Usage:
  ```bash
  python scripts/restore_qdrant_snapshot.py
  ```

## Environment Variables

All scripts use environment variables from `.env` file:

- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
- `QDRANT_API_KEY` - Qdrant API key (optional for local)
- `QDRANT_COLLECTION_NAME` - Collection name (default: informasi-umum-itb)
- `PINECONE_API_KEY` - Pinecone API key (for migration only)
- `PINECONE_INDEX_NAME` - Pinecone index name (default: informasi-umum-itb)

## Dependencies

All scripts require:
- `qdrant-client` - Qdrant Python client
- `requests` - HTTP library (for REST API calls)
- `python-dotenv` - Environment variable management

Install with:
```bash
pip install qdrant-client requests python-dotenv
```

## Notes

- Scripts are designed to be run from the project root directory
- They will automatically load environment variables from `.env` file
- All scripts include error handling and progress reporting

