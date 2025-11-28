# Qdrant Migration Plan: From Pinecone to Self-Hosted Qdrant

## Executive Summary

This document outlines the research findings and implementation plan for migrating the agentic chatbot from Pinecone (cloud-hosted) to Qdrant (self-hosted in Docker). The migration includes data extraction from Pinecone collection `informasi-umum-itb`, data insertion into Qdrant, codebase updates to use Qdrant client, and Docker configuration to host Qdrant.

### Key Changes Overview

**Core Application:**
- Remove `langchain-pinecone==0.2.0` dependency
- Add `qdrant-client` and `langchain-qdrant` dependencies
- Replace `PineconeVectorStore` with `Qdrant` vector store
- Update vector store initialization to use Qdrant client
- Add `QDRANT_URL` and `QDRANT_API_KEY` environment variables

**Data Migration:**
- Create migration script to extract all vectors from Pinecone collection `informasi-umum-itb`
- Insert extracted vectors into Qdrant collection
- Preserve vector IDs, embeddings, and metadata

**Deployment Configuration:**
- Add Qdrant service to `docker-compose.yml`
- Configure Qdrant with API key authentication
- Set up persistent storage for Qdrant data
- Update `config.py` validation to require `QDRANT_URL` and `QDRANT_API_KEY`
- Update `validate.py` to check for Qdrant configuration
- Update `DEPLOYMENT_GUIDE.md` environment variables section

**Files Modified:** 8 files (3 core + 5 deployment config)
**Files Created:** 2 files (migration script + migration plan)
**Files Unchanged:** 6 files (no changes needed)

---

## 1. Current State Analysis

### 1.1 Current Dependencies (from `requirements.txt`)

```
langchain==0.3.7
langchain-community==0.3.5
langchain-core==0.3.60
langchain-openai==0.3.17
langchain-pinecone==0.2.0  # ⚠️ TO BE REMOVED
langgraph==0.2.48
```

### 1.2 Current Vector Store Configuration

**File: `agents/models.py`**
- **Current Provider:** Pinecone (cloud-hosted)
- **Current Collection:** `informasi-umum-itb`
- **Current Implementation:**
  ```python
  from langchain_pinecone import PineconeVectorStore
  vectorstore = PineconeVectorStore(embedding=embeddings, index_name="informasi-umum-itb")
  ```

### 1.3 Current Usage Points

1. **`agents/models.py`** - Vector store initialization (line 39)
2. **`agents/rag.py`** - RAG agent uses `vectorstore` from `agents.models` (line 7, 23)
3. **`config.py`** - Contains `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` configuration (lines 24-25)

---

## 2. Research Findings

### 2.1 Qdrant Compatibility with LangChain

**Key Finding:** Qdrant provides excellent LangChain integration:
- ✅ **Compatible with `langchain-qdrant`** - Official LangChain integration package
- ✅ **Works with LangChain 0.3.x** - Fully compatible with current versions
- ✅ **Self-hosted option** - Can be deployed in Docker with API key authentication
- ✅ **Seamless integration** - Similar API to Pinecone, minimal code changes required

### 2.2 Qdrant Client Libraries

**Latest Versions (as of 2024-2025):**
- `qdrant-client>=1.7.0` - Official Qdrant Python client
- `langchain-qdrant>=0.1.0` - LangChain integration for Qdrant

**Installation:**
```bash
pip install qdrant-client langchain-qdrant
```

### 2.3 Qdrant Docker Deployment

**Official Docker Image:** `qdrant/qdrant:latest`

**Key Features:**
- REST API on port 6333
- gRPC API on port 6334
- Web UI on port 6333 (dashboard)
- API key authentication support
- Persistent storage via volumes

**Docker Compose Configuration:**
```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"  # REST API
    - "6334:6334"  # gRPC API
  volumes:
    - qdrant_data:/qdrant/storage
  environment:
    QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}
```

### 2.4 Data Migration Approach

**Option 1: Qdrant Migration Tool (Recommended)**
- Official Docker-based migration tool
- Supports Pinecone to Qdrant migration
- Handles batch processing and resumable migrations
- **Limitation:** Requires Pinecone serverless index (not pod-based)

**Option 2: Custom Python Script (Fallback)**
- Direct Pinecone API calls to fetch all vectors
- Direct Qdrant API calls to insert vectors
- More control over the migration process
- Works with any Pinecone index type

**Recommendation:** Use Option 2 (custom script) for maximum compatibility and control.

### 2.5 API Key Authentication

Qdrant supports API key authentication for secure access:
- Set via environment variable: `QDRANT__SERVICE__API_KEY`
- Required in client initialization: `QdrantClient(url=..., api_key=...)`
- Can be used for internal users and services

---

## 3. Compatibility Matrix

| Component | Current Version | Qdrant Compatible | Notes |
|-----------|----------------|-------------------|-------|
| `langchain` | 0.3.7 | ✅ Yes | No change needed |
| `langchain-openai` | 0.3.17 | ✅ Yes | No change needed |
| `langchain-core` | 0.3.60 | ✅ Yes | No change needed |
| `langchain-community` | 0.3.5 | ✅ Yes | No change needed |
| `langchain-pinecone` | 0.2.0 | ❌ Remove | Replace with langchain-qdrant |
| `langchain-qdrant` | - | ✅ Add | New dependency |

**Conclusion:** All current LangChain versions are compatible with Qdrant. Need to replace `langchain-pinecone` with `langchain-qdrant`.

---

## 4. Implementation Plan

### Phase 1: Environment Configuration

#### 4.1.1 Update `config.py`

**File:** `config.py`

**Changes:**
1. Add `QDRANT_URL` and `QDRANT_API_KEY` configuration
2. Add `QDRANT_COLLECTION_NAME` configuration
3. Keep `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` for migration period (optional - can be removed after migration)
4. Update validation method

**Code Changes:**

```python
# In Config class, update Vector Database section:
# Vector Database
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")  # Keep for migration
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "informasi-umum-itb")  # Keep for migration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")  # NEW
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # NEW
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb")  # NEW

# Update validate() method:
required = [
    ("API_KEY", cls.API_KEY),
    ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
    ("OPENROUTER_API_KEY", cls.OPENROUTER_API_KEY),
    ("QDRANT_URL", cls.QDRANT_URL),  # NEW
    ("QDRANT_API_KEY", cls.QDRANT_API_KEY),  # NEW - replace PINECONE_API_KEY
]
```

**Location:** Lines 23-25, 67-72

---

### Phase 2: Update Dependencies

#### 4.2.1 Update `requirements.txt`

**File:** `requirements.txt`

**Changes:**
1. Remove `langchain-pinecone==0.2.0`
2. Add `qdrant-client>=1.7.0`
3. Add `langchain-qdrant>=0.1.0`
4. Keep all other dependencies unchanged

**Code Changes:**

```diff
langchain==0.3.7
langchain-community==0.3.5
langchain-core==0.3.60
langchain-openai==0.3.17
- langchain-pinecone==0.2.0
+ qdrant-client>=1.7.0
+ langchain-qdrant>=0.1.0
langgraph==0.2.48
```

**Location:** Line 10

---

### Phase 3: Update Vector Store Initialization

#### 4.3.1 Update `agents/models.py`

**File:** `agents/models.py`

**Changes:**
1. Remove `from langchain_pinecone import PineconeVectorStore`
2. Add `from langchain_qdrant import Qdrant`
3. Add `from qdrant_client import QdrantClient`
4. Replace `PineconeVectorStore` initialization with `Qdrant` initialization
5. Update to use Qdrant client with API key

**Code Changes:**

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import Qdrant  # CHANGED from langchain_pinecone
from qdrant_client import QdrantClient  # NEW
import os

load_dotenv()

# ... existing LLM code ...

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# NEW: Qdrant vector store initialization
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

vectorstore = Qdrant(
    client=qdrant_client,
    collection_name=os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb"),
    embedding=embeddings,
)

# REMOVED: PineconeVectorStore initialization
# vectorstore = PineconeVectorStore(embedding=embeddings, index_name="informasi-umum-itb")
```

**Location:** Lines 1-4, 38-39

---

### Phase 4: Verify No Breaking Changes

#### 4.4.1 Check Usage in `agents/rag.py`

**File:** `agents/rag.py`

**Status:** ✅ **No changes needed**
- Already imports `vectorstore` from `agents.models`
- Uses `vectorstore.similarity_search_with_score()` which is compatible with Qdrant
- Will automatically use new Qdrant vector store

**Location:** Line 7, 23

---

### Phase 5: Environment Variables

#### 5.1 Required Environment Variables

**Add to `.env` file:**

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION_NAME=informasi-umum-itb

# Pinecone (keep for migration, can remove after)
PINECONE_API_KEY=your_pinecone_api_key_here  # For migration only
PINECONE_INDEX_NAME=informasi-umum-itb  # For migration only
```

**Note:** `PINECONE_API_KEY` is only needed during migration. Can be removed after successful migration.

#### 5.2 Update Documentation

**Files to update:**
- `DEPLOYMENT_GUIDE.md` (if exists)
- `README.md` (if exists)
- Any environment variable documentation

**Changes:**
- Replace `PINECONE_API_KEY` references with `QDRANT_URL` and `QDRANT_API_KEY`
- Update vector database provider information
- Update deployment instructions

---

### Phase 6: Update Deployment Configuration

#### 6.1 Update `docker-compose.yml`

**File:** `docker-compose.yml`

**Changes:**
1. Add Qdrant service
2. Configure Qdrant with API key
3. Set up persistent storage
4. Expose Qdrant ports
5. Add health check for Qdrant
6. Update app service to depend on Qdrant

**Code Changes:**

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - QDRANT_URL=http://qdrant:6333  # NEW
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
      qdrant:  # NEW
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - QDRANT_URL=http://qdrant:6333  # NEW
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
      app:
        condition: service_healthy
      qdrant:  # NEW
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  qdrant:  # NEW SERVICE
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"  # REST API
      - "6334:6334"  # gRPC API
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 10s

volumes:
  redis_data:
  qdrant_data:  # NEW
```

**Location:** After redis service, before volumes section

---

#### 6.2 Update `DEPLOYMENT_GUIDE.md`

**File:** `DEPLOYMENT_GUIDE.md`

**Changes:**
1. Update environment variables section to replace `PINECONE_API_KEY` with `QDRANT_URL` and `QDRANT_API_KEY`
2. Update vector database provider description
3. Add Qdrant setup instructions

**Code Changes:**

```markdown
### Environment Variables

All configuration is managed through environment variables in `.env`:

**Required:**
- `API_KEY` - API authentication key
- `OPENAI_API_KEY` - OpenAI API key (embeddings)
- `OPENROUTER_API_KEY` - OpenRouter API key (LLM)
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)  # CHANGED from PINECONE_API_KEY
- `QDRANT_API_KEY` - Qdrant API key for authentication  # NEW
- `QDRANT_COLLECTION_NAME` - Qdrant collection name (default: informasi-umum-itb)  # NEW
```

**Location:** Line 188

**Additional Updates:**
- Update any mentions of "Pinecone" to "Qdrant"
- Update vector database setup instructions
- Add Qdrant deployment information

---

#### 6.3 Update `validate.py`

**File:** `validate.py`

**Changes:**
1. Update validation to check for `QDRANT_URL` and `QDRANT_API_KEY` instead of `PINECONE_API_KEY`
2. Update required environment variables list

**Code Changes:**

```python
# In validate_config() function, update required list:
required = [
    ("API_KEY", Config.API_KEY),
    ("OPENAI_API_KEY", Config.OPENAI_API_KEY),
    ("OPENROUTER_API_KEY", Config.OPENROUTER_API_KEY),
    ("QDRANT_URL", Config.QDRANT_URL),  # CHANGED from PINECONE_API_KEY
    ("QDRANT_API_KEY", Config.QDRANT_API_KEY),  # NEW
]
```

**Location:** Lines 46-51

---

#### 6.4 Update `Dockerfile`

**File:** `Dockerfile`

**Status:** ✅ **No changes needed**
- No environment variable references
- No provider-specific code
- Qdrant runs as separate service

---

## 5. Data Migration Script

### 5.1 Migration Script Overview

**File:** `migrate_pinecone_to_qdrant.py` (NEW)

**Purpose:**
- **Step 1:** Extract all vectors from Pinecone collection `informasi-umum-itb` and save to pickle file
- **Step 2:** Load vectors from pickle file and insert into Qdrant collection
- Preserve vector IDs, embeddings, and metadata
- Provide progress tracking and error handling

**Key Features:**
- Two-step process for safety and verification
- Data saved to pickle file for backup and verification
- Batch processing for efficient migration
- Progress reporting
- Error handling and retry logic
- Validation of migrated data
- Support for resuming interrupted migrations

**Usage:**

**Step 1: Extract from Pinecone**
```bash
python migrate_pinecone_to_qdrant.py --step extract --output pinecone_data.pkl
```

**Step 2: Upload to Qdrant**
```bash
python migrate_pinecone_to_qdrant.py --step upload --input pinecone_data.pkl
```

**Optional: Provide vector IDs file for extraction**
```bash
python migrate_pinecone_to_qdrant.py --step extract --output pinecone_data.pkl --vector-ids-file vector_ids.txt
```

**Prerequisites:**
- Pinecone API key configured in environment (for extract step)
- Qdrant instance running and accessible (for upload step)
- Qdrant API key configured in environment (for upload step)
- Required Python packages installed:
  - `pinecone-client` (for migration only, can be removed after)
  - `qdrant-client`
  - `python-dotenv`

**Note:** The migration script requires `pinecone-client` package. This is only needed during migration and can be removed from requirements after successful migration.

**Data File Format:**
The extracted data is saved as a pickle file containing:
- `metadata`: Extraction date, Pinecone index name, vector count, vector dimension
- `vectors`: List of vectors with IDs, values, and metadata

**LangChain Format Conversion:**
During upload, the script automatically converts Pinecone metadata to LangChain's expected format:
- `page_content`: Extracted from the `text` field (or `content`/`page_content` if available)
- `metadata`: All other fields from the original metadata

The payload structure in Qdrant will be:
```python
{
    "page_content": "Main text content here...",
    "metadata": {
        "source": "...",
        "title": "...",
        "chunk_index": 1,
        # ... all other fields
    }
}
```

This allows you to:
1. Verify the extracted data before uploading
2. Re-run the upload step if needed
3. Keep a backup of your Pinecone data
4. Ensure compatibility with LangChain's Qdrant integration

---

## 6. Code Changes Summary

### Files to Modify

#### Core Application Files

1. ✅ **`requirements.txt`**
   - Remove `langchain-pinecone==0.2.0`
   - Add `qdrant-client>=1.7.0`
   - Add `langchain-qdrant>=0.1.0`

2. ✅ **`config.py`**
   - Add `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME` to Config class
   - Update `validate()` method to require `QDRANT_URL` and `QDRANT_API_KEY` instead of `PINECONE_API_KEY`

3. ✅ **`agents/models.py`**
   - Remove `from langchain_pinecone import PineconeVectorStore`
   - Add `from langchain_qdrant import Qdrant`
   - Add `from qdrant_client import QdrantClient`
   - Replace `PineconeVectorStore` initialization with `Qdrant` initialization

#### Deployment Configuration Files

4. ✅ **`docker-compose.yml`**
   - Add Qdrant service with API key configuration
   - Add Qdrant volume for persistent storage
   - Update app and streamlit services to depend on Qdrant
   - Add Qdrant health check

5. ✅ **`validate.py`**
   - Update `validate_config()` function
   - Replace `PINECONE_API_KEY` with `QDRANT_URL` and `QDRANT_API_KEY` in required variables list

6. ✅ **`DEPLOYMENT_GUIDE.md`**
   - Update environment variables section
   - Replace `PINECONE_API_KEY` with `QDRANT_URL` and `QDRANT_API_KEY`
   - Update vector database provider description
   - Add Qdrant setup instructions

#### Migration Scripts

7. ✅ **`migrate_pinecone_to_qdrant.py`** (NEW)
   - Extract vectors from Pinecone
   - Insert vectors into Qdrant
   - Progress tracking and error handling

### Files That Don't Need Changes

- ✅ `agents/rag.py` - Uses `vectorstore` from `agents.models` (automatic)
- ✅ `app.py` - No direct vector store usage
- ✅ `Dockerfile` - No environment variable references
- ✅ `test_deployment.sh` - No provider-specific references
- ✅ All other files - No vector store dependencies

---

## 7. Testing Checklist

### 7.1 Pre-Implementation Verification

- [ ] Verify Qdrant Docker image is available
- [ ] Test Qdrant Docker container startup
- [ ] Verify Qdrant API key authentication works
- [ ] Test Qdrant collection creation
- [ ] Verify Pinecone API key has access to `informasi-umum-itb` collection

### 7.2 Data Migration Testing

**Step 1: Extract from Pinecone**
- [ ] Run: `python migrate_pinecone_to_qdrant.py --step extract --output pinecone_data.pkl`
- [ ] Verify pickle file was created successfully
- [ ] Check file size is reasonable
- [ ] Verify all vectors are extracted correctly
- [ ] Inspect pickle file metadata (extraction date, vector count, etc.)

**Step 2: Upload to Qdrant**
- [ ] Run: `python migrate_pinecone_to_qdrant.py --step upload --input pinecone_data.pkl`
- [ ] Verify all vectors are inserted correctly
- [ ] Compare vector counts between Pinecone and Qdrant
- [ ] Test vector search functionality in Qdrant
- [ ] Verify metadata is preserved correctly
- [ ] Test with sample queries to ensure search results match

### 7.3 Post-Implementation Testing

- [ ] Test RAG agent with new Qdrant vector store (`/v1/chat` endpoint)
- [ ] Test audio processing with new Qdrant vector store (`/v1/audio` endpoint)
- [ ] Verify search results match previous Pinecone results
- [ ] Check error handling for invalid API key
- [ ] Verify Qdrant connection handling
- [ ] Test with various conversation threads
- [ ] Monitor Qdrant performance and resource usage

### 7.4 Rollback Plan

If issues occur:
1. Revert `agents/models.py` to use `PineconeVectorStore`
2. Re-add `langchain-pinecone==0.2.0` to `requirements.txt`
3. Restore `PINECONE_API_KEY` in environment
4. Remove Qdrant service from `docker-compose.yml`
5. Restore original configuration files

---

## 8. Implementation Steps (Sequential)

### Step 1: Research & Verification
- [x] Research latest Qdrant client and LangChain integration
- [x] Research Qdrant Docker setup and API key authentication
- [x] Research Pinecone to Qdrant migration approaches
- [ ] Verify Qdrant Docker image availability
- [ ] Test Qdrant container startup locally

### Step 2: Create Migration Script
- [ ] Create `migrate_pinecone_to_qdrant.py` script
- [ ] Implement Pinecone data extraction
- [ ] Implement Qdrant data insertion
- [ ] Add progress tracking and error handling
- [ ] Test migration script with sample data

### Step 3: Update Dependencies
- [ ] Remove `langchain-pinecone==0.2.0` from `requirements.txt`
- [ ] Add `qdrant-client>=1.7.0` to `requirements.txt`
- [ ] Add `langchain-qdrant>=0.1.0` to `requirements.txt`
- [ ] Run `pip install -r requirements.txt` to update environment

### Step 4: Update Configuration
- [ ] Add `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME` to `config.py`
- [ ] Update `validate()` method in `config.py`
- [ ] Add Qdrant environment variables to `.env` file
- [ ] Generate Qdrant API key for authentication

### Step 5: Update Vector Store Initialization
- [ ] Remove `PineconeVectorStore` import from `agents/models.py`
- [ ] Add `Qdrant` and `QdrantClient` imports to `agents/models.py`
- [ ] Replace vector store initialization with Qdrant configuration
- [ ] Test vector store initialization

### Step 6: Update Docker Configuration
- [ ] Add Qdrant service to `docker-compose.yml`
- [ ] Configure Qdrant with API key and persistent storage
- [ ] Update app and streamlit services to depend on Qdrant
- [ ] Add Qdrant health check
- [ ] Test Docker Compose configuration

### Step 7: Run Data Migration
- [ ] Start Qdrant service: `docker-compose up -d qdrant`
- [ ] Verify Qdrant is accessible
- [ ] **Step 7a: Extract from Pinecone**
  - [ ] Run: `python migrate_pinecone_to_qdrant.py --step extract --output pinecone_data.pkl`
  - [ ] Verify the pickle file was created and contains data
  - [ ] Check file size and vector count
- [ ] **Step 7b: Upload to Qdrant**
  - [ ] Run: `python migrate_pinecone_to_qdrant.py --step upload --input pinecone_data.pkl`
  - [ ] Verify all vectors are migrated
  - [ ] Test vector search in Qdrant

### Step 8: Testing
- [ ] Run `python validate.py` to verify configuration
- [ ] Test `/v1/chat` endpoint with Qdrant
- [ ] Test `/v1/audio` endpoint with Qdrant
- [ ] Verify search results match previous results
- [ ] Test deployment with `docker-compose up`

### Step 9: Update Deployment Configuration
- [ ] Update `validate.py` to check for `QDRANT_URL` and `QDRANT_API_KEY`
- [ ] Update `DEPLOYMENT_GUIDE.md` environment variables section
- [ ] Update any other documentation references

### Step 10: Cleanup (Optional)
- [ ] Remove `PINECONE_API_KEY` from `config.py` (after successful migration)
- [ ] Remove `PINECONE_API_KEY` from `.env` file
- [ ] Remove any remaining Pinecone references from documentation

---

## 9. Risk Assessment

### Low Risk ✅
- Qdrant has excellent LangChain integration
- Similar API to Pinecone, minimal code changes
- Self-hosted option provides more control
- Easy rollback path

### Medium Risk ⚠️
- Data migration complexity (large datasets)
- Qdrant collection configuration (dimensions, distance metric)
- API key management for internal users
- Performance differences between Pinecone and Qdrant

### High Risk ⚠️
- Data loss during migration (mitigate with backups)
- Service downtime during migration (mitigate with parallel setup)

### Mitigation
- Test migration script with sample data first
- Keep Pinecone configuration as backup during transition
- Monitor Qdrant performance and resource usage
- Implement proper error handling and retry logic
- Create backups before migration

---

## 10. Additional Considerations

### 10.1 Collection Configuration

**Qdrant Collection Settings:**
- **Vector Size:** 3072 (for `text-embedding-3-large`)
- **Distance Metric:** Cosine (matching Pinecone default)
- **Collection Name:** `informasi-umum-itb` (matching Pinecone index name)

**Collection Creation:**
The migration script should create the collection with proper configuration if it doesn't exist.

### 10.2 Performance Considerations

- **Batch Size:** Use appropriate batch size for vector insertion (recommended: 64-128)
- **Concurrency:** Qdrant supports concurrent requests, can optimize migration speed
- **Resource Usage:** Monitor Qdrant memory and CPU usage during migration

### 10.3 API Key Security

- **Generation:** Generate strong API keys for Qdrant
- **Storage:** Store API keys securely in environment variables
- **Rotation:** Plan for API key rotation if needed
- **Internal Access:** API keys can be used for internal service authentication

### 10.4 Data Persistence

- **Volume Mounting:** Ensure Qdrant data is persisted via Docker volumes
- **Backups:** Implement regular backups of Qdrant data
- **Recovery:** Test data recovery procedures

---

## 11. References

- Qdrant Documentation: https://qdrant.tech/documentation/
- Qdrant Python Client: https://github.com/qdrant/qdrant-client
- LangChain Qdrant Integration: https://python.langchain.com/docs/integrations/vectorstores/qdrant
- Qdrant Docker Guide: https://qdrant.tech/documentation/guides/installation/
- Qdrant Migration Guide: https://qdrant.tech/documentation/database-tutorials/migration/
- Pinecone Python Client: https://github.com/pinecone-io/pinecone-python-client

---

## 12. Notes

### Migration Tool Options

**Option 1: Official Qdrant Migration Tool**
- Docker-based tool: `registry.cloud.qdrant.io/library/qdrant-migration`
- Supports Pinecone to Qdrant migration
- **Limitation:** Requires Pinecone serverless index

**Option 2: Custom Python Script (Recommended)**
- More control over migration process
- Works with any Pinecone index type
- Better error handling and progress tracking
- Can be customized for specific needs

**Recommendation:** Use custom Python script for maximum compatibility and control.

### Vector ID Format

**Important:** Qdrant supports both UUID and integer IDs, while Pinecone uses string IDs. The migration script should handle ID conversion appropriately.

---

## 13. Estimated Implementation Time

- **Research & Verification:** 1 hour
- **Migration Script Development:** 2-3 hours
- **Core Code Changes:** 1 hour
- **Docker Configuration:** 30 minutes
- **Data Migration:** 1-4 hours (depends on data size)
- **Testing:** 2-3 hours
- **Documentation:** 1 hour
- **Total:** ~8-12 hours

---

**Document Created:** Research Phase Complete
**Next Step:** Create migration script and proceed with implementation

