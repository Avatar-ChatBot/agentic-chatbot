# ITB RAG Chatbot - Deployment Analysis

**Document Version:** 1.0  
**Last Updated:** November 22, 2025  
**Status:** Production Readiness Assessment

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Environment Variables Analysis](#environment-variables-analysis)
4. [Dependency Analysis & Updates](#dependency-analysis--updates)
5. [External Service Dependencies](#external-service-dependencies)
6. [Security Analysis](#security-analysis)
7. [Performance & Scalability Analysis](#performance--scalability-analysis)
8. [Infrastructure Requirements](#infrastructure-requirements)
9. [Monitoring & Observability](#monitoring--observability)
10. [Risk Assessment](#risk-assessment)

---

## Executive Summary

The ITB RAG Chatbot is a sophisticated multi-modal AI application that combines:
- **RAG (Retrieval-Augmented Generation)** for knowledge-based Q&A
- **Speech-to-Text (STT)** for audio input processing
- **Emotion Analysis** for context-aware responses
- **Text-to-Speech (TTS)** for audio output generation
- **Conversation Memory** for contextual chat history

### Current State
- Development-ready Flask application (port 8000)
- Debug mode enabled
- No production WSGI server configured
- Missing environment variable documentation
- Outdated dependency versions (1+ year old)
- No monitoring/logging infrastructure
- No containerization setup
- CORS wide open (all origins)

### Production Readiness Score: **45/100**
- ✅ Core functionality complete
- ✅ Basic error handling present
- ⚠️ Security needs hardening
- ❌ Production server not configured
- ❌ No load testing performed
- ❌ No monitoring setup
- ❌ Dependencies outdated

---

## System Architecture Overview

### Request Flow

#### Text Chat (`/v1/chat`)
```
Client → API Key Auth → RAG Agent → Vector DB (Pinecone) → LLM (Together/OpenAI) → Response
                         ↓
                   Conversation Memory (MemorySaver)
```

#### Audio Chat (`/v1/audio`)
```
Client → API Key Auth → Audio File
                         ↓
                    STT (Prosa AI) ← Audio Processing (pydub)
                         ↓
                    Emotion Analysis ← Custom API
                         ↓
                    RAG Agent → Vector DB → LLM
                         ↓
                    TTS (Prosa AI) → Audio Response
```

### Component Breakdown

| Component | Technology | Purpose | External Dependency |
|-----------|-----------|---------|-------------------|
| Web Framework | Flask 3.0.3 | HTTP API server | No |
| LLM Provider (Primary) | Together AI | Qwen2.5-72B-Instruct | Yes |
| LLM Provider (Fallback) | OpenAI | gpt-4o-mini | Yes |
| Embeddings | OpenAI | text-embedding-3-large | Yes |
| Vector Database | Pinecone | Document storage/retrieval | Yes |
| STT | Prosa AI | Speech-to-text streaming | Yes |
| TTS | Prosa AI | Text-to-speech streaming | Yes |
| Emotion Analysis | Custom API | Audio/text emotion detection | Yes |
| Conversation Memory | LangGraph MemorySaver | Thread-based chat history | No (in-memory) |
| Audio Processing | pydub + ffmpeg | Audio format conversion | No (local) |

### Critical Dependencies Chain
```
Client Request
    ↓
Flask (app.py)
    ↓
┌──────────────┬──────────────┬──────────────┐
│   STT        │   Emotion    │     RAG      │
│ (Prosa AI)   │  (Custom)    │  (LangChain) │
└──────────────┴──────────────┴──────┬───────┘
                                     │
                        ┌────────────┼────────────┐
                        ↓            ↓            ↓
                   Pinecone    Together AI   OpenAI
                        ↓            ↓            ↓
                   Embeddings    LLM         Embeddings
                                                  ↓
                                             TTS (Prosa AI)
```

---

## Environment Variables Analysis

### Required Environment Variables

#### 1. **API_KEY** (Application Security)
- **Purpose:** Authentication for `/v1/chat` and `/v1/audio` endpoints
- **Format:** String (recommend 32+ character random token)
- **Security Level:** HIGH
- **Usage:** `app.py` lines 55, 84
- **Recommendation:** Generate with `openssl rand -hex 32`

#### 2. **OPENAI_API_KEY** (OpenAI Services)
- **Purpose:** 
  - Text embeddings (text-embedding-3-large)
  - Fallback LLM (gpt-4o-mini)
- **Format:** `sk-...` (OpenAI API key format)
- **Security Level:** CRITICAL
- **Usage:** `agents/models.py` (implicit via langchain-openai)
- **Cost Impact:** HIGH (embeddings on every query + fallback LLM)
- **Recommendation:** 
  - Set usage limits in OpenAI dashboard
  - Monitor spending daily
  - Consider rate limiting

#### 3. **TOGETHER_API_KEY** (Together AI Services)
- **Purpose:** Primary LLM (Qwen/Qwen2.5-72B-Instruct-Turbo)
- **Format:** String (Together AI API key)
- **Security Level:** CRITICAL
- **Usage:** `agents/models.py` line 19
- **Cost Impact:** HIGH (primary inference engine)
- **Recommendation:**
  - Set up billing alerts
  - Monitor token usage
  - Consider request queuing for cost control

#### 4. **PINECONE_API_KEY** (Vector Database)
- **Purpose:** Access to Pinecone vector store for document retrieval
- **Format:** String (Pinecone API key)
- **Security Level:** CRITICAL
- **Usage:** `agents/models.py` (implicit via langchain-pinecone)
- **Index Used:** `informasi-umum-itb`
- **Cost Impact:** MEDIUM (query-based pricing)
- **Recommendation:**
  - Ensure index is pre-populated
  - Monitor query volume
  - Set up index backups

#### 5. **PROSA_STT_API_KEY** (Speech-to-Text)
- **Purpose:** Convert audio input to text via Prosa AI WebSocket API
- **Format:** String (Prosa AI API key)
- **Security Level:** HIGH
- **Usage:** `utils/stt.py` lines 11, 53
- **Endpoint:** `wss://asr-api.stg.prosa.ai/v2/speech/stt/streaming`
- **Cost Impact:** MEDIUM (per audio minute)
- **Note:** Currently using STAGING endpoint
- **Recommendation:**
  - Switch to production endpoint for prod deployment
  - Update URL from `.stg.prosa.ai` to `.prosa.ai`

#### 6. **PROSA_TTS_API_KEY** (Text-to-Speech)
- **Purpose:** Convert text responses to audio via Prosa AI WebSocket API
- **Format:** String (Prosa AI API key)
- **Security Level:** HIGH
- **Usage:** `utils/tts.py` lines 10, 23, 58
- **Endpoint:** `wss://tts-api.stg.prosa.ai/v2/speech/tts/streaming`
- **Cost Impact:** MEDIUM (per character synthesized)
- **Note:** Currently using STAGING endpoint
- **Recommendation:**
  - Switch to production endpoint
  - Consider caching frequent responses

#### 7. **EMOTION_ANALYSIS_URL** (Emotion Detection)
- **Purpose:** Analyze user emotion from audio and text
- **Format:** URL (e.g., `https://emotion-api.example.com`)
- **Security Level:** MEDIUM
- **Usage:** `utils/emotion.py` line 21
- **Endpoint:** `{EMOTION_ANALYSIS_URL}/predict`
- **Cost Impact:** DEPENDS (custom service)
- **Recommendation:**
  - Ensure high availability (impacts UX)
  - Implement timeout (currently 30s)
  - Add fallback to "neutral" on failure (already implemented)

#### 8. **SUPABASE_URI** (SQL Database - Optional)
- **Purpose:** PostgreSQL database for SQL agent (currently unused)
- **Format:** PostgreSQL connection string `postgresql://user:pass@host:port/db`
- **Security Level:** CRITICAL (if enabled)
- **Usage:** `agents/models.py` line 29 (commented out), `agents/sql.py`
- **Status:** NOT CURRENTLY USED
- **Recommendation:**
  - Remove from production ENV if not needed
  - If enabled in future, ensure SSL mode and connection pooling

### Environment Variable Dependencies

```
Required for ALL deployments:
├── API_KEY (authentication)
├── OPENAI_API_KEY (embeddings + fallback LLM)
├── TOGETHER_API_KEY (primary LLM)
└── PINECONE_API_KEY (vector store)

Required for /v1/audio endpoint:
├── PROSA_STT_API_KEY (audio → text)
├── PROSA_TTS_API_KEY (text → audio)
└── EMOTION_ANALYSIS_URL (emotion detection)

Optional:
└── SUPABASE_URI (if SQL agent is activated)
```

### Missing Environment Variables

The following are used via implicit configuration in dependencies:
- **LANGCHAIN_API_KEY** (optional, for LangSmith tracing)
- **LANGCHAIN_TRACING_V2** (optional, for LangSmith observability)
- **LANGCHAIN_PROJECT** (optional, for organizing traces)

---

## Dependency Analysis & Updates

### Current Dependencies (from requirements.txt)

| Package | Current Version | Latest Version (Nov 2025) | Status | Update Priority |
|---------|----------------|---------------------------|---------|-----------------|
| Flask | 3.0.3 | 3.1.0 | Minor update available | MEDIUM |
| Flask-Cors | 5.0.0 | 5.0.0 | Up to date | N/A |
| langchain | 0.3.7 | 0.3.15+ | Outdated | HIGH |
| langchain-community | 0.3.5 | 0.3.15+ | Outdated | HIGH |
| langchain-core | 0.3.60 | 0.3.30+ | Potentially newer | HIGH |
| langchain-openai | 0.3.17 | 0.2.10+ | Check compatibility | HIGH |
| langchain-pinecone | 0.2.0 | 0.2.0 | Up to date | N/A |
| langgraph | 0.2.48 | 0.2.60+ | Minor update | HIGH |
| langgraph-checkpoint | 2.0.4 | 2.0.8+ | Minor update | MEDIUM |
| langgraph-sdk | 0.1.36 | 0.1.40+ | Minor update | LOW |
| langsmith | 0.1.145 | 0.2.0+ | Major update | MEDIUM |
| python-dotenv | 1.0.1 | 1.0.1 | Up to date | N/A |
| websockets | 13.1 | 14.0+ | Major update | MEDIUM |
| pydantic | 2.10.5 | 2.10.6+ | Patch update | LOW |
| pydantic_core | 2.27.2 | 2.27.3+ | Patch update | LOW |
| pydantic-settings | 2.6.1 | 2.7.0+ | Minor update | LOW |
| wsproto | 1.2.0 | 1.2.0 | Up to date | N/A |
| yarl | 1.17.1 | 1.18.0+ | Minor update | LOW |
| ffmpeg | N/A (binary) | N/A | System dependency | N/A |
| pydub | Not pinned | 0.25.1 | No version specified | HIGH |
| streamlit | Not pinned | 1.40.0+ | No version specified | MEDIUM |
| langchain-together | 0.3.0 | 0.3.1+ | Minor update | MEDIUM |

### Missing Critical Dependencies

The following are imported but not in requirements.txt:
- **httpx** (used in `utils/emotion.py`) - CRITICAL
- **io, json, os, asyncio** (standard library) - OK
- **requests** (used in `utils/tts.py` for polling) - NEEDS ADDING

### Dependency Update Recommendations

#### HIGH PRIORITY - Update immediately
```
# Core LangChain updates for security and features
langchain>=0.3.15
langchain-community>=0.3.15
langchain-core>=0.3.30
langchain-openai>=0.2.10
langgraph>=0.2.60

# Pin unpinned dependencies
pydub==0.25.1
httpx==0.27.0
requests==2.32.3
```

#### MEDIUM PRIORITY - Update before production
```
Flask==3.1.0
websockets==14.0
langsmith==0.2.0
langgraph-checkpoint==2.0.8
langchain-together==0.3.1
streamlit==1.40.0
```

#### LOW PRIORITY - Update during maintenance windows
```
pydantic==2.10.6
pydantic_core==2.27.3
pydantic-settings==2.7.0
yarl==1.18.0
langgraph-sdk==0.1.40
```

### System Dependencies

These must be installed at OS level:
- **Python 3.10+** (recommended 3.11 or 3.12)
- **ffmpeg** (for audio processing via pydub)

Installation:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt-get install ffmpeg

# Alpine (for Docker)
apk add ffmpeg
```

### Dependency Conflicts & Compatibility

⚠️ **Potential Issues:**
1. **LangChain version mismatch**: Core, Community, and partner packages should be aligned
2. **Pydantic v2**: All packages must support Pydantic v2 (already on v2.10.5)
3. **Python version**: Some packages may require Python 3.10+ (verify in production)

---

## External Service Dependencies

### Critical External Services

| Service | Provider | Criticality | Fallback Strategy | SLA Requirement |
|---------|----------|-------------|-------------------|-----------------|
| Together AI | Together.xyz | CRITICAL | OpenAI GPT-4o-mini | 99.9% |
| OpenAI Embeddings | OpenAI | CRITICAL | None (cache?) | 99.9% |
| Pinecone Vector DB | Pinecone | CRITICAL | None | 99.9% |
| Prosa STT | Prosa AI | HIGH | Disable audio endpoint | 99.5% |
| Prosa TTS | Prosa AI | HIGH | Text-only response | 99.5% |
| Emotion Analysis | Custom | MEDIUM | Default to "neutral" | 95% |

### Service Interdependencies

```
User Request (Audio)
    ↓
    Prosa STT (CRITICAL PATH)
    ↓
    Emotion API (DEGRADED: defaults to "neutral")
    ↓
    Together AI (CRITICAL PATH)
    ↓   ↓ (on failure)
    ↓   OpenAI (FALLBACK)
    ↓
    Pinecone (CRITICAL PATH, no fallback)
    ↓
    Prosa TTS (DEGRADED: return text only)
```

### Failure Mode Analysis

#### Scenario 1: Together AI Down
- **Impact:** LLM inference fails
- **Mitigation:** Code has `llm_4o_mini` available but NOT automatically used
- **Action Required:** Implement automatic LLM failover

#### Scenario 2: Pinecone Down
- **Impact:** Cannot retrieve documents, entire RAG fails
- **Mitigation:** NONE
- **Action Required:** 
  - Implement local fallback vector store (FAISS)
  - Or implement graceful error with helpful message

#### Scenario 3: Prosa APIs Down
- **Impact:** Audio endpoints fail
- **Mitigation:** Emotion analysis already has try/catch
- **Action Required:** 
  - Return error message guiding user to text chat
  - Consider alternative STT/TTS providers (OpenAI Whisper/TTS)

#### Scenario 4: Emotion Analysis Down
- **Impact:** Neutral emotion used (graceful degradation)
- **Mitigation:** ALREADY IMPLEMENTED (lines 112-119 in app.py)
- **Status:** ✅ GOOD

### API Rate Limits & Quotas

| Service | Likely Limit | Cost per 1000 requests | Monitoring Needed |
|---------|--------------|------------------------|-------------------|
| Together AI | Varies by plan | ~$0.50-2.00 | YES - token usage |
| OpenAI Embeddings | 3M tokens/min | ~$0.13 | YES - embeddings count |
| Pinecone | Query-based | ~$0.10-0.50 | YES - query volume |
| Prosa STT | Minutes-based | Varies | YES - audio duration |
| Prosa TTS | Character-based | Varies | YES - character count |

**Action Required:**
- Set up billing alerts for all services
- Implement rate limiting at application layer
- Add request queuing for high load

---

## Security Analysis

### Current Security Posture

#### ✅ IMPLEMENTED
1. API key authentication on all endpoints
2. Environment variables for secrets (not hardcoded)
3. Try/catch for external service failures
4. Basic input validation (file existence checks)

#### ⚠️ NEEDS IMPROVEMENT
1. **CORS is wide open** - allows ALL origins
2. **No rate limiting** - vulnerable to abuse
3. **No request size limits** - DoS risk on audio upload
4. **API key in plain comparison** - use timing-safe comparison
5. **Debug mode enabled** in production startup
6. **No HTTPS enforcement** - should run behind reverse proxy
7. **No input sanitization** on message content
8. **Conversation IDs are user-provided** - potential for session hijacking

#### ❌ MISSING
1. Request rate limiting per API key
2. Request size limits (max audio file size)
3. Input validation and sanitization
4. Security headers (HSTS, CSP, etc.)
5. Audit logging
6. Secrets rotation mechanism
7. API key management system

### Security Recommendations

#### IMMEDIATE (Before Production)

```python
# 1. Fix CORS - specify allowed origins
CORS(
    app,
    resources={r"/*": {"origins": ["https://yourdomain.com"]}},
    supports_credentials=True,
    methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Conversation-Id", "X-API-Key"],
)

# 2. Use timing-safe comparison for API key
import secrets
if not secrets.compare_digest(api_key, os.getenv("API_KEY")):
    raise APIError("Invalid API key", 401)

# 3. Add request size limit
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# 4. Disable debug in production
app.run(host="0.0.0.0", port=8000, debug=False)

# 5. Add rate limiting
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.headers.get("X-API-Key"))
@limiter.limit("100 per hour")
```

#### SHORT-TERM (Within 1 month)

1. **Implement audit logging** - log all requests with API key, conversation ID, timestamps
2. **Add input validation** - validate conversation ID format, sanitize user messages
3. **Set up API key rotation** - ability to invalidate and rotate keys
4. **Add security headers** - use Flask-Talisman
5. **Implement conversation ID validation** - use UUIDs, validate format
6. **Set up Web Application Firewall (WAF)** - use Cloudflare or AWS WAF

#### LONG-TERM (Ongoing)

1. **Regular security audits**
2. **Dependency vulnerability scanning** (use `safety` or `snyk`)
3. **Penetration testing**
4. **Secrets management service** (AWS Secrets Manager, HashiCorp Vault)
5. **Zero-trust architecture** - mTLS, service mesh

---

## Performance & Scalability Analysis

### Current Performance Characteristics

Based on code analysis, typical request processing time:

#### Text Chat (`/v1/chat`)
```
Component               Time (est.)
----------------------------------
RAG Processing         1-3 seconds
├─ Query Reformulation  0.5-1s (LLM)
├─ Vector Search       0.1-0.3s (Pinecone)
└─ Answer Generation   0.5-2s (LLM)

Total: ~1-3 seconds
```

#### Audio Chat (`/v1/audio`)
```
Component               Time (est.)  Tracked in Response
----------------------------------------------------
Speech-to-Text         2-5 seconds   ✅ stt_time
Emotion Analysis       1-3 seconds   ✅ emotion_time
RAG Processing         1-3 seconds   ✅ rag_time
Text-to-Speech         2-4 seconds   ✅ tts_time
----------------------------------------------------
Total: ~6-15 seconds                 ✅ total
```

### Performance Bottlenecks

1. **Audio Processing (6-15s total)** - MAJOR UX CONCERN
   - STT: 2-5s (network + processing)
   - Emotion: 1-3s (audio compression + network)
   - TTS: 2-4s (network + synthesis)
   
2. **LLM Inference (0.5-2s)** - MODERATE
   - Together AI: typically 0.5-1.5s for 72B model
   - OpenAI: typically 0.5-1s for GPT-4o-mini
   
3. **Vector Search (0.1-0.3s)** - LOW
   - Pinecone is optimized, minimal concern

4. **In-Memory Conversation History** - SCALABILITY ISSUE
   - MemorySaver stores in-process memory
   - NOT shared across workers
   - NOT persistent across restarts
   - NOT suitable for production

### Scalability Constraints

#### Single-Process Flask (Current Setup)
```
Max Concurrent Requests: ~10-20 (due to async await in audio endpoint)
Memory per Request: ~50-100 MB
Max Requests/Second: ~2-5 (limited by audio processing)
Memory Usage (1000 conversations): ~5-10 GB (MemorySaver)
```

#### With Production WSGI (Gunicorn + Multiple Workers)
```
Workers: 4-8
Threads per Worker: 2-4
Max Concurrent: 32-64
Requests/Second: ~20-40 (still limited by audio)
Memory Usage: 2-4 GB per worker = 8-32 GB total
```

### Conversation Memory Scalability Issue

**CRITICAL: Current implementation uses in-memory MemorySaver**

```python
# agents/rag.py line 27
memory = MemorySaver()
```

**Problems:**
1. Not shared across multiple Gunicorn workers
2. Lost on application restart
3. Grows indefinitely (no eviction policy)
4. Not suitable for production

**Solutions:**
1. **Redis-based Checkpointer** (Recommended)
   ```python
   from langgraph.checkpoint.redis import RedisSaver
   memory = RedisSaver(redis_client)
   ```
   
2. **PostgreSQL-based Checkpointer**
   ```python
   from langgraph.checkpoint.postgres import PostgresSaver
   memory = PostgresSaver(connection_string)
   ```

3. **Custom TTL-based Checkpointer**
   - Implement conversation expiry (e.g., 24 hours)
   - Reduce memory footprint

### Caching Opportunities

#### High-Value Caching
1. **Embedding Cache** - cache embeddings for common queries
2. **Vector Search Results** - cache for identical queries (TTL: 1 hour)
3. **TTS Audio Cache** - cache common responses (TTL: 24 hours)
4. **Emotion Analysis** - cache by audio hash (TTL: 1 hour)

#### Implementation
```python
import redis
from functools import lru_cache

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Cache vector search results
def cached_vector_search(query_hash, search_func):
    cached = redis_client.get(f"search:{query_hash}")
    if cached:
        return json.loads(cached)
    result = search_func()
    redis_client.setex(f"search:{query_hash}", 3600, json.dumps(result))
    return result
```

### Load Testing Recommendations

**Test Scenarios:**

1. **Text Chat Endpoint**
   - 100 concurrent users
   - 1 request per minute per user
   - Duration: 10 minutes
   - Expected: 1000 requests, <3s p95 latency

2. **Audio Chat Endpoint**
   - 50 concurrent users
   - 1 request per 2 minutes per user
   - Duration: 10 minutes
   - Expected: 250 requests, <15s p95 latency

3. **Mixed Load**
   - 80 text chat, 20 audio chat
   - Simulate realistic usage pattern
   - Duration: 30 minutes

**Tools:**
- Locust (Python-based)
- Apache JMeter
- k6 (Go-based)

---

## Infrastructure Requirements

### Scenario 1: Minimal Production (100 users, text-only)

**Application Server:**
- **CPU:** 2 vCPUs (Intel/AMD x86_64)
- **RAM:** 4 GB
- **Storage:** 20 GB SSD
- **Network:** 1 Gbps
- **OS:** Ubuntu 22.04 LTS or Amazon Linux 2023

**Estimated Costs:**
- AWS EC2: t3.medium (~$30/month)
- DigitalOcean: Basic Droplet (~$24/month)
- GCP: e2-medium (~$25/month)

**Configuration:**
```
Gunicorn Workers: 2
Threads per Worker: 2
Max Concurrent Requests: 8
Expected RPS: ~5-10
```

### Scenario 2: Standard Production (1000 users, mixed workload)

**Application Server:**
- **CPU:** 4-8 vCPUs
- **RAM:** 16 GB
- **Storage:** 50 GB SSD (for logs, cache)
- **Network:** 10 Gbps

**Redis/Memory Server (for conversation state):**
- **CPU:** 2 vCPUs
- **RAM:** 8 GB (for conversation history + cache)
- **Storage:** 10 GB SSD

**Reverse Proxy/Load Balancer:**
- **CPU:** 2 vCPUs
- **RAM:** 4 GB
- **Network:** 10 Gbps

**Total Estimated Costs:**
- AWS: ~$200-300/month (EC2 c5.xlarge + ElastiCache + ALB)
- DigitalOcean: ~$150-200/month (multiple droplets)
- GCP: ~$220-280/month (compute + memorystore)

**Configuration:**
```
Gunicorn Workers: 8
Threads per Worker: 2
Max Concurrent Requests: 32
Expected RPS: ~20-40
Redis Memory: 8 GB (for ~10K conversations)
```

### Scenario 3: High-Scale Production (1000 users, audio-heavy)

**Application Servers (2x for HA):**
- **CPU:** 8-16 vCPUs each
- **RAM:** 32 GB each
- **Storage:** 100 GB SSD each

**Redis Cluster (for state + cache):**
- **CPU:** 4 vCPUs
- **RAM:** 16 GB
- **Storage:** 20 GB SSD

**Load Balancer:**
- Cloud-native (ALB, GCP LB)

**Object Storage (for audio files):**
- S3/GCS for audio caching

**Monitoring Stack:**
- Prometheus + Grafana (2 vCPUs, 8 GB RAM)

**Total Estimated Costs:**
- AWS: ~$600-800/month (with Auto Scaling)
- GCP: ~$650-850/month
- Azure: ~$680-880/month

**Configuration:**
```
Instances: 2-4 (auto-scale)
Workers per Instance: 16
Threads per Worker: 2
Max Concurrent per Instance: 64
Total Concurrent: 128-256
Expected RPS: ~50-100
Redis Memory: 16 GB (for ~50K conversations + cache)
```

### Scenario 4: Local Database (Pinecone Self-Hosted Alternative)

**⚠️ Note:** Pinecone doesn't offer self-hosted. Alternative: **Qdrant** or **Weaviate**

**Vector Database Server (Qdrant):**
- **CPU:** 8-16 vCPUs
- **RAM:** 32-64 GB (for index in-memory)
- **Storage:** 200-500 GB NVMe SSD
- **Network:** 10 Gbps

**Application Server (from Scenario 2):**
- **CPU:** 4-8 vCPUs
- **RAM:** 16 GB
- **Storage:** 50 GB SSD

**Total Estimated Costs:**
- AWS: ~$500-700/month (c5.2xlarge for DB + c5.xlarge for app)
- Bare Metal: ~$300-500/month (Hetzner dedicated)

**Pros:**
- No per-query costs
- Data sovereignty
- Lower latency (LAN)

**Cons:**
- Operational overhead (backups, updates, monitoring)
- Need vector DB expertise
- Upfront migration effort
- Scaling complexity

### Cloud Provider Recommendations

| Provider | Best For | Pros | Cons |
|----------|----------|------|------|
| **AWS** | Enterprise, High Scale | Most services, global reach | Complex, expensive |
| **GCP** | ML/AI Workloads | Good AI/ML tools, competitive pricing | Less mature than AWS |
| **Azure** | Microsoft Stack | Enterprise integration | Complex billing |
| **DigitalOcean** | Startups, Simple Deploys | Simple, affordable, good DX | Limited services |
| **Hetzner** | Cost-Conscious | Cheapest for dedicated, EU-based | No managed services |
| **Railway/Render** | Quick Prototypes | Easiest setup, auto-deploy | Expensive at scale |

**Recommendation for ITB:** Start with **DigitalOcean** or **AWS** (if using existing ITB AWS org)

### System Requirements Summary

| Users | Deployment | CPU | RAM | Storage | Monthly Cost |
|-------|------------|-----|-----|---------|--------------|
| 100 (text) | Single server | 2 vCPU | 4 GB | 20 GB | $25-40 |
| 1000 (mixed) | App + Redis | 4-8 vCPU | 16 GB | 50 GB | $150-300 |
| 1000 (audio) | 2x App + Redis + LB | 16-32 vCPU | 64 GB | 200 GB | $600-800 |
| 1000 (local vector DB) | App + Qdrant | 12-24 vCPU | 48-80 GB | 250-550 GB | $500-700 |

**External Service Costs (monthly, estimated):**
- Together AI: $100-500 (based on usage)
- OpenAI: $50-200 (embeddings + fallback)
- Pinecone: $70-200 (Starter to Standard plan)
- Prosa STT: $50-300 (based on audio minutes)
- Prosa TTS: $50-300 (based on character count)
- **Total External:** $320-1500/month

**Grand Total (1000 users, mixed):** $470-1800/month

---

## Monitoring & Observability

### Current State
❌ No monitoring configured  
❌ No metrics collection  
❌ No alerting  
❌ Basic `print()` and `logger.info()` only  
❌ No distributed tracing

### Required Monitoring Components

#### 1. Application Metrics
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active connections
- Worker health

#### 2. Business Metrics
- API key usage
- Conversation count
- Endpoint usage (/v1/chat vs /v1/audio)
- Average response length
- Source link click-through (if tracked)

#### 3. External Service Metrics
- Together AI latency
- OpenAI latency
- Pinecone latency
- Prosa STT/TTS latency
- Emotion API latency
- External service error rates

#### 4. Infrastructure Metrics
- CPU utilization
- Memory utilization
- Disk I/O
- Network throughput
- Redis memory usage (if implemented)

#### 5. Cost Metrics
- Together AI token usage
- OpenAI token usage
- Pinecone query count
- Prosa API usage
- Total estimated cost per day

### Recommended Monitoring Stack

#### Option 1: Cloud-Native (Easiest)
```
Application: LangSmith (built-in LangChain observability)
  ↓
Infrastructure: Cloud provider metrics (CloudWatch/Stackdriver)
  ↓
Logs: Cloud logging (CloudWatch Logs/Cloud Logging)
  ↓
Alerts: Cloud alerting (SNS/Cloud Monitoring)
```

**Setup:**
```python
# Add to app.py
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "itb-chatbot-prod"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
```

**Cost:** $0-100/month (LangSmith free tier → $39/month)

#### Option 2: Open Source (Most Control)
```
Application: OpenTelemetry + Prometheus
  ↓
Visualization: Grafana
  ↓
Logs: Loki
  ↓
Tracing: Jaeger
  ↓
Alerts: Alertmanager
```

**Cost:** Infrastructure only (~$50-100/month for monitoring server)

#### Option 3: Hybrid (Recommended)
```
LLM Observability: LangSmith
  ↓
APM: Sentry (errors + performance)
  ↓
Infrastructure: Cloud-native metrics
  ↓
Custom Dashboards: Grafana Cloud (free tier)
```

**Cost:** $50-150/month

### Key Alerts to Configure

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| Error rate > 5% | 5 minutes | CRITICAL | Page on-call |
| P95 latency > 30s | 10 minutes | HIGH | Investigate |
| CPU > 80% | 15 minutes | MEDIUM | Consider scaling |
| Memory > 90% | 10 minutes | HIGH | Check for leaks |
| Together AI errors > 10% | 5 minutes | CRITICAL | Switch to OpenAI |
| Pinecone down | 1 minute | CRITICAL | Page on-call |
| Conversation memory > 8GB | N/A | MEDIUM | Implement cleanup |

### Logging Strategy

#### Current: Basic Logging
```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

#### Recommended: Structured Logging
```python
import json
import logging
from datetime import datetime

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def log_request(self, endpoint, conversation_id, duration, status):
        self.logger.info(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "request",
            "endpoint": endpoint,
            "conversation_id": conversation_id,
            "duration_ms": duration * 1000,
            "status": status
        }))
    
    def log_external_call(self, service, duration, success):
        self.logger.info(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "external_call",
            "service": service,
            "duration_ms": duration * 1000,
            "success": success
        }))
```

**Benefits:**
- Easy to parse and query
- Integration with log aggregation tools
- Searchable by field

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| **Memory leak from MemorySaver** | HIGH | HIGH | 🔴 CRITICAL | Implement Redis checkpointer |
| **Pinecone API outage** | MEDIUM | HIGH | 🔴 CRITICAL | Implement fallback or cached responses |
| **Together AI rate limit** | MEDIUM | HIGH | 🔴 CRITICAL | Implement queuing and fallback to OpenAI |
| **CORS misconfiguration** | LOW | HIGH | 🟡 HIGH | Fix before production |
| **No rate limiting (DoS)** | MEDIUM | MEDIUM | 🟡 HIGH | Implement Flask-Limiter |
| **Outdated dependencies (CVEs)** | MEDIUM | MEDIUM | 🟡 HIGH | Update all dependencies |
| **Single point of failure (1 server)** | HIGH | MEDIUM | 🟡 HIGH | Implement HA with 2+ servers |
| **Audio file size DoS** | MEDIUM | LOW | 🟢 MEDIUM | Add file size limits |
| **Conversation hijacking** | LOW | MEDIUM | 🟢 MEDIUM | Validate conversation ID format |

### Operational Risks

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| **No monitoring (blind deployment)** | HIGH | HIGH | 🔴 CRITICAL | Implement monitoring before prod |
| **Cost overrun (LLM APIs)** | MEDIUM | MEDIUM | 🟡 HIGH | Set billing alerts, implement budgets |
| **Prosa staging endpoints in prod** | HIGH | LOW | 🟡 HIGH | Update to production URLs |
| **No backup/disaster recovery** | HIGH | MEDIUM | 🟡 HIGH | Implement backup strategy |
| **No rollback strategy** | HIGH | MEDIUM | 🟡 HIGH | Implement blue-green deployment |
| **Lack of documentation** | MEDIUM | MEDIUM | 🟢 MEDIUM | Create runbooks |

### Business Risks

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| **Poor UX due to latency (15s)** | HIGH | HIGH | 🔴 CRITICAL | Optimize or set expectations |
| **High operational costs** | MEDIUM | MEDIUM | 🟡 HIGH | Implement caching, monitor usage |
| **Vendor lock-in (Pinecone)** | LOW | MEDIUM | 🟢 MEDIUM | Document migration path |
| **Data privacy concerns** | LOW | HIGH | 🟡 HIGH | Review data retention policies |

### Risk Mitigation Priorities

**Week 1 (Before Production):**
1. ✅ Fix MemorySaver → Redis checkpointer
2. ✅ Update all dependencies
3. ✅ Add monitoring (LangSmith + Sentry)
4. ✅ Fix CORS configuration
5. ✅ Add rate limiting
6. ✅ Change Prosa endpoints to production

**Week 2-4 (Production Hardening):**
7. ✅ Implement HA (2+ servers + load balancer)
8. ✅ Add caching (Redis)
9. ✅ Set up alerting
10. ✅ Create runbooks
11. ✅ Implement backup strategy
12. ✅ Load testing

**Month 2+ (Ongoing):**
- Regular security audits
- Dependency updates
- Performance optimization
- Cost optimization

---

## Conclusion

The ITB RAG Chatbot is a well-architected application with a solid foundation but requires significant production hardening. Key priorities:

1. **Replace in-memory MemorySaver with Redis** (CRITICAL)
2. **Update dependencies** (HIGH)
3. **Implement monitoring and observability** (HIGH)
4. **Fix security issues (CORS, rate limiting)** (HIGH)
5. **Deploy with production WSGI server** (HIGH)
6. **Set up infrastructure for 1000 users** (MEDIUM)
7. **Implement caching strategies** (MEDIUM)
8. **Create operational runbooks** (MEDIUM)

With these improvements, the application can serve 1000 concurrent users reliably with 99.9% uptime.

**Estimated Time to Production-Ready:** 2-4 weeks with 1-2 engineers

**Recommended Next Steps:**
1. Review this analysis with technical team
2. Prioritize action items based on launch timeline
3. Proceed with Deployment Plan document for step-by-step implementation

---

**Document Prepared By:** AI Analysis  
**Review Status:** DRAFT  
**Next Review:** Before implementation begins

