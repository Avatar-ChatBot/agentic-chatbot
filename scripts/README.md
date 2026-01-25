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

- **`reembed_snapshot.py`** - Re-embed Qdrant snapshot with new embedding model
  - Restores snapshot to temporary collection
  - Re-embeds all points using OpenRouter's qwen3-embedding-8b
  - Creates new collection and snapshot with updated embeddings
  - Useful for migrating to a different embedding model

  Usage:
  ```bash
  # Basic usage
  python scripts/reembed_snapshot.py \
      --snapshot-path ./qdrant_snapshots/informasi-umum-itb.snapshot \
      --output-dir ./qdrant_snapshots

  # With custom batch size and output collection
  python scripts/reembed_snapshot.py \
      --snapshot-path ./qdrant_snapshots/my_collection.snapshot \
      --collection-name my_collection \
      --batch-size 100 \
      --output-collection my_collection_new

  # Keep temp collection for debugging
  python scripts/reembed_snapshot.py \
      --snapshot-path ./snapshots/my_collection.snapshot \
      --keep-temp
  ```

### Parser Scripts

- **`parse_peraturan_pdf.py`** - Parse Indonesian legal documents (Peraturan Perundang-undangan)
  - Extracts structured `Pasal` objects from PDF or text files
  - Supports the standard Indonesian legal document format (BAB, Pasal, Ayat)
  - Outputs JSON, Markdown, or RAG-compatible format
  - Can embed and upload directly to Qdrant

  Usage:
  ```bash
  # Basic parsing - output to console
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf

  # Output to JSON file
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output json

  # Output to Markdown file
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output markdown --output-file ./output.md

  # Export for RAG pipeline
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --output rag --output-file ./rag_data.json

  # Custom source name
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/doc.pdf --source-name "UU No 1 Tahun 2024"

  # Parse and upload to Qdrant (end-to-end)
  python scripts/parse_peraturan_pdf.py --pdf-path ./docs/uu_12_2011.pdf --upload-to-qdrant

  # Upload from existing JSON file to Qdrant
  python scripts/parse_peraturan_pdf.py --json-input ./rag_data.json --upload-to-qdrant
  ```

  Output Schema:
  ```json
  {
    "content": "(1) Ayat pertama... (2) Ayat kedua...",
    "pasal": 1,
    "pasal_title": "Ruang Lingkup",
    "bab": "I",
    "bab_title": "KETENTUAN UMUM",
    "source": "UU No 12 Tahun 2011"
  }
  ```

  Qdrant Upload Options:
  - `--upload-to-qdrant` - Enable embedding and upload to Qdrant
  - `--json-input <path>` - Load from pre-parsed JSON instead of PDF
  - `--batch-size <n>` - Batch size for uploads (default: 50)

  Environment Variables for Qdrant Upload:
  - `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
  - `QDRANT_API_KEY` - Qdrant API key (optional for local)
  - `QDRANT_COLLECTION_NAME` - Collection name (default: informasi-umum-itb)
  - `EMBEDDING_PROVIDER` - "openrouter" or "openai" (default: openai)
  - `EMBEDDING_MODEL` - Model name for OpenRouter (default: qwen/qwen3-embedding-8b)
  - `OPENROUTER_API_KEY` - Required if using OpenRouter embeddings

## Environment Variables

All scripts use environment variables from `.env` file:

- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
- `QDRANT_API_KEY` - Qdrant API key (optional for local)
- `QDRANT_COLLECTION_NAME` - Collection name (default: informasi-umum-itb)
- `PINECONE_API_KEY` - Pinecone API key (for migration only)
- `PINECONE_INDEX_NAME` - Pinecone index name (default: informasi-umum-itb)
- `OPENROUTER_API_KEY` - OpenRouter API key (required for reembed_snapshot.py and parse_peraturan_pdf.py --upload-to-qdrant)
- `REEMBED_BATCH_SIZE` - Embedding batch size for reembed_snapshot.py (default: 50)
- `EMBEDDING_PROVIDER` - Embedding provider: "openrouter" or "openai" (default: openai)
- `EMBEDDING_MODEL` - OpenRouter embedding model name (default: qwen/qwen3-embedding-8b)

## Dependencies

Common dependencies for all scripts:
- `qdrant-client` - Qdrant Python client
- `requests` - HTTP library (for REST API calls)
- `python-dotenv` - Environment variable management

Additional dependencies for parser scripts:
- `pdfplumber` - PDF text extraction (for parse_peraturan_pdf.py)

Additional dependencies for Qdrant upload functionality:
- `langchain-openai` - Embeddings support
- `langchain-qdrant` - Qdrant vector store integration
- `langchain-core` - Document format

Install with:
```bash
pip install qdrant-client requests python-dotenv pdfplumber langchain-openai langchain-qdrant langchain-core
```

## Notes

- Scripts are designed to be run from the project root directory
- They will automatically load environment variables from `.env` file
- All scripts include error handling and progress reporting







