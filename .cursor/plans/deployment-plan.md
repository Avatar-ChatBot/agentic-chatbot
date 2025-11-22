# ITB RAG Chatbot - Deployment Plan

**Document Version:** 1.0  
**Last Updated:** November 22, 2025  
**Target Launch:** [TO BE DETERMINED]  
**Status:** Action Plan

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Dependency Updates](#phase-1-dependency-updates)
4. [Phase 2: Environment Configuration](#phase-2-environment-configuration)
5. [Phase 3: Code Changes for Production](#phase-3-code-changes-for-production)
6. [Phase 4: Infrastructure Setup](#phase-4-infrastructure-setup)
7. [Phase 5: Monitoring & Observability](#phase-5-monitoring--observability)
8. [Phase 6: Security Hardening](#phase-6-security-hardening)
9. [Phase 7: Performance Optimization](#phase-7-performance-optimization)
10. [Phase 8: Testing & Validation](#phase-8-testing--validation)
11. [Phase 9: Deployment](#phase-9-deployment)
12. [Phase 10: Post-Deployment](#phase-10-post-deployment)
13. [Rollback Plan](#rollback-plan)
14. [Maintenance Plan](#maintenance-plan)

---

## Overview

This deployment plan provides a step-by-step guide to productionize the ITB RAG Chatbot from development to production-ready state.

**Timeline Estimate:** 2-4 weeks (with 1-2 engineers)

**Phases:**
- **Week 1:** Dependencies, Environment, Code Changes (Phases 1-3)
- **Week 2:** Infrastructure, Monitoring, Security (Phases 4-6)
- **Week 3:** Performance, Testing (Phases 7-8)
- **Week 4:** Deployment, Validation (Phases 9-10)

---

## Prerequisites

### Required Access

- [ ] GitHub/Git repository access
- [ ] Cloud provider account (AWS/GCP/DigitalOcean)
- [ ] Domain name for production (e.g., `chatbot.itb.ac.id`)
- [ ] SSL certificate (or Let's Encrypt setup)
- [ ] Together AI API access and credits
- [ ] OpenAI API access and credits
- [ ] Pinecone account and populated index
- [ ] Prosa AI API keys (production, not staging)
- [ ] Emotion analysis API access

### Required Tools

- [ ] Python 3.10+ installed locally
- [ ] Docker and Docker Compose
- [ ] Git
- [ ] SSH client
- [ ] Text editor / IDE
- [ ] Postman or curl (for API testing)

### Team Roles

- **DevOps Engineer:** Infrastructure, deployment, monitoring
- **Backend Engineer:** Code changes, testing, optimization
- **Security Review:** (Optional) External security audit

---

## Phase 1: Dependency Updates

**Duration:** 1 day  
**Priority:** HIGH  
**Risk:** MEDIUM (breaking changes possible)

### Step 1.1: Backup Current State

```bash
# Create a backup branch
git checkout -b backup-pre-production-$(date +%Y%m%d)
git push origin backup-pre-production-$(date +%Y%m%d)

# Return to main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feat/production-hardening
```

### Step 1.2: Update Requirements File

Create `requirements-production.txt` with pinned versions:

```txt
# Web Framework
Flask==3.1.0
Flask-Cors==5.0.0
gunicorn==21.2.0

# LangChain Core
langchain==0.3.15
langchain-community==0.3.15
langchain-core==0.3.30
langchain-openai==0.2.10
langchain-pinecone==0.2.0
langchain-together==0.3.1

# LangGraph
langgraph==0.2.60
langgraph-checkpoint==2.0.8
langgraph-sdk==0.1.40
langsmith==0.2.0

# Redis (for checkpointer)
redis==5.0.1
hiredis==2.3.2

# HTTP Clients
httpx==0.27.0
requests==2.32.3

# WebSockets
websockets==14.0

# Data Validation
pydantic==2.10.6
pydantic_core==2.27.3
pydantic-settings==2.7.0

# Audio Processing
pydub==0.25.1

# Utilities
python-dotenv==1.0.1
wsproto==1.2.0
yarl==1.18.0

# Monitoring & Security
sentry-sdk[flask]==1.40.0
flask-limiter==3.5.0

# Optional (for Streamlit demo)
streamlit==1.40.0
```

### Step 1.3: Update Dependencies

```bash
# Create fresh virtual environment
python3 -m venv venv-prod
source venv-prod/bin/activate  # On Windows: venv-prod\Scripts\activate

# Install updated dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements-production.txt

# Verify installation
pip list

# Generate frozen requirements
pip freeze > requirements-frozen.txt
```

### Step 1.4: Install System Dependencies

```bash
# macOS
brew install ffmpeg redis

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg redis-server

# Alpine (for Docker)
apk add --no-cache ffmpeg redis
```

### Step 1.5: Test Application with New Dependencies

```bash
# Start Redis
redis-server &

# Set minimal env vars
export API_KEY="test-key-12345"
export OPENAI_API_KEY="sk-test..."
export TOGETHER_API_KEY="test..."
export PINECONE_API_KEY="test..."

# Run application
python app.py

# In another terminal, test endpoints
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-12345" \
  -H "X-Conversation-Id: test-123" \
  -d '{"message": "Hello"}'
```

### Step 1.6: Commit Changes

```bash
git add requirements-production.txt requirements-frozen.txt
git commit -m "chore: update dependencies for production"
```

**Validation Checklist:**
- [ ] All dependencies installed without errors
- [ ] Application starts without import errors
- [ ] `/v1/chat` endpoint responds
- [ ] No breaking changes in LangChain API

---

## Phase 2: Environment Configuration

**Duration:** 0.5 days  
**Priority:** HIGH  
**Risk:** LOW

### Step 2.1: Create .env.example

Create `.env.example` file in project root:

```bash
# =============================================================================
# ITB RAG CHATBOT - ENVIRONMENT VARIABLES
# =============================================================================
# Copy this file to .env and fill in your actual values
# NEVER commit .env to version control!

# -----------------------------------------------------------------------------
# APPLICATION CONFIGURATION
# -----------------------------------------------------------------------------
# Custom API key for endpoint authentication (generate with: openssl rand -hex 32)
API_KEY=your_api_key_here_min_32_characters

# Flask configuration
FLASK_ENV=production
FLASK_DEBUG=0

# Server configuration
HOST=0.0.0.0
PORT=8000

# -----------------------------------------------------------------------------
# LLM PROVIDERS
# -----------------------------------------------------------------------------
# Together AI - Primary LLM provider (Qwen2.5-72B-Instruct-Turbo)
# Get API key from: https://api.together.xyz/settings/api-keys
TOGETHER_API_KEY=your_together_api_key_here

# OpenAI - Embeddings (text-embedding-3-large) and fallback LLM (gpt-4o-mini)
# Get API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your_openai_api_key_here

# -----------------------------------------------------------------------------
# VECTOR DATABASE
# -----------------------------------------------------------------------------
# Pinecone - Vector store for document retrieval
# Get API key from: https://app.pinecone.io/organizations/-/projects/-/keys
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=informasi-umum-itb
PINECONE_ENVIRONMENT=us-west1-gcp

# -----------------------------------------------------------------------------
# SPEECH SERVICES (Prosa AI)
# -----------------------------------------------------------------------------
# Prosa AI - Speech-to-Text (STT)
# IMPORTANT: Use PRODUCTION endpoint, not staging!
# Get API key from: https://prosa.ai/
PROSA_STT_API_KEY=your_prosa_stt_api_key_here
PROSA_STT_URL=wss://asr-api.prosa.ai/v2/speech/stt/streaming

# Prosa AI - Text-to-Speech (TTS)
# IMPORTANT: Use PRODUCTION endpoint, not staging!
PROSA_TTS_API_KEY=your_prosa_tts_api_key_here
PROSA_TTS_URL=wss://tts-api.prosa.ai/v2/speech/tts/streaming

# -----------------------------------------------------------------------------
# EMOTION ANALYSIS
# -----------------------------------------------------------------------------
# Custom emotion analysis API endpoint
# Replace with your actual emotion analysis service URL
EMOTION_ANALYSIS_URL=https://your-emotion-api.example.com

# -----------------------------------------------------------------------------
# CONVERSATION PERSISTENCE
# -----------------------------------------------------------------------------
# Redis - For conversation memory and caching
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
# Set TTL for conversations (in seconds, 86400 = 24 hours)
CONVERSATION_TTL=86400

# -----------------------------------------------------------------------------
# DATABASE (OPTIONAL - SQL Agent)
# -----------------------------------------------------------------------------
# PostgreSQL/Supabase - Only needed if SQL agent is enabled
# Currently not used in production
# SUPABASE_URI=postgresql://user:password@host:port/database

# -----------------------------------------------------------------------------
# MONITORING & OBSERVABILITY
# -----------------------------------------------------------------------------
# LangSmith - LLM observability (optional but recommended)
# Get API key from: https://smith.langchain.com/settings
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=itb-chatbot-production

# Sentry - Error tracking and performance monitoring (optional)
# Get DSN from: https://sentry.io/
SENTRY_DSN=https://your_sentry_dsn@sentry.io/project_id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# -----------------------------------------------------------------------------
# SECURITY
# -----------------------------------------------------------------------------
# CORS - Allowed origins (comma-separated)
CORS_ORIGINS=https://chatbot.itb.ac.id,https://www.itb.ac.id

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_HOUR=100

# Max request size (in bytes, 16777216 = 16 MB)
MAX_CONTENT_LENGTH=16777216

# -----------------------------------------------------------------------------
# PERFORMANCE
# -----------------------------------------------------------------------------
# Caching
CACHE_ENABLED=true
CACHE_TTL=3600

# Request timeouts (in seconds)
STT_TIMEOUT=30
TTS_TIMEOUT=30
EMOTION_TIMEOUT=30
LLM_TIMEOUT=60

# -----------------------------------------------------------------------------
# NOTES
# -----------------------------------------------------------------------------
# 1. Generate secure API_KEY with: openssl rand -hex 32
# 2. Ensure Prosa endpoints are PRODUCTION (not .stg.prosa.ai)
# 3. Set up billing alerts for Together AI and OpenAI
# 4. Enable LangSmith for production monitoring
# 5. Configure Sentry for error tracking
# 6. Update CORS_ORIGINS to match your domain
```

### Step 2.2: Create Environment Loading Utility

Create `config.py` in project root:

```python
"""Configuration management for ITB RAG Chatbot"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Application
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    API_KEY = os.getenv("API_KEY")
    
    # LLM Providers
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Vector Database
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "informasi-umum-itb")
    
    # Speech Services
    PROSA_STT_API_KEY = os.getenv("PROSA_STT_API_KEY")
    PROSA_STT_URL = os.getenv("PROSA_STT_URL", "wss://asr-api.prosa.ai/v2/speech/stt/streaming")
    PROSA_TTS_API_KEY = os.getenv("PROSA_TTS_API_KEY")
    PROSA_TTS_URL = os.getenv("PROSA_TTS_URL", "wss://tts-api.prosa.ai/v2/speech/tts/streaming")
    
    # Emotion Analysis
    EMOTION_ANALYSIS_URL = os.getenv("EMOTION_ANALYSIS_URL")
    
    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    CONVERSATION_TTL = int(os.getenv("CONVERSATION_TTL", "86400"))
    
    # Monitoring
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false") == "true"
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "itb-chatbot")
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "production")
    
    # Security
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true") == "true"
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))
    
    # Performance
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true") == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
    STT_TIMEOUT = int(os.getenv("STT_TIMEOUT", "30"))
    TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT", "30"))
    EMOTION_TIMEOUT = int(os.getenv("EMOTION_TIMEOUT", "30"))
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate required environment variables"""
        errors = []
        
        required = [
            ("API_KEY", cls.API_KEY),
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("TOGETHER_API_KEY", cls.TOGETHER_API_KEY),
            ("PINECONE_API_KEY", cls.PINECONE_API_KEY),
        ]
        
        for name, value in required:
            if not value:
                errors.append(f"Missing required environment variable: {name}")
        
        return errors

# Validate on import
validation_errors = Config.validate()
if validation_errors:
    raise EnvironmentError("\n".join(validation_errors))
```

### Step 2.3: Document Environment Dependencies

Create `docs/environment-setup.md`:

```markdown
# Environment Setup Guide

## Required Services

### 1. Together AI
- Sign up: https://api.together.xyz/signup
- Navigate to Settings → API Keys
- Create new API key
- Set billing alerts (recommended: $100/month)

### 2. OpenAI
- Sign up: https://platform.openai.com/signup
- Navigate to API Keys
- Create new API key
- Set usage limits (recommended: $50/month)

### 3. Pinecone
- Sign up: https://app.pinecone.io/
- Create index: `informasi-umum-itb`
- Dimension: 3072 (for text-embedding-3-large)
- Metric: cosine
- Populate index with ITB documents

### 4. Prosa AI
- Contact: https://prosa.ai/contact
- Request production API access
- Obtain both STT and TTS API keys

### 5. Emotion Analysis API
- Deploy emotion analysis service
- Note the API endpoint URL

### 6. Redis (Infrastructure)
- Option A: Managed Redis (AWS ElastiCache, Redis Cloud)
- Option B: Self-hosted (install via package manager)

## Environment Variable Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Generate secure API key:
   ```bash
   openssl rand -hex 32
   ```

3. Fill in all required values in `.env`

4. Validate configuration:
   ```bash
   python -c "from config import Config; print('Configuration valid!')"
   ```
```

### Step 2.4: Commit Changes

```bash
git add .env.example config.py docs/environment-setup.md
git commit -m "feat: add environment configuration management"
```

**Validation Checklist:**
- [ ] `.env.example` created with all variables documented
- [ ] `config.py` validates required variables
- [ ] Environment setup guide created
- [ ] `.env` file in `.gitignore` (should already be there)

---

## Phase 3: Code Changes for Production

**Duration:** 2-3 days  
**Priority:** CRITICAL  
**Risk:** HIGH

### Step 3.1: Implement Redis Checkpointer

**Problem:** Current `MemorySaver` is in-memory, not shared across workers

**Solution:** Use Redis-based checkpointer

Create `utils/checkpointer.py`:

```python
"""Redis-based conversation checkpointer for production"""
import json
import redis
from typing import Any, Dict, Optional
from datetime import timedelta
from langgraph.checkpoint.base import BaseCheckpointSaver
from config import Config

class RedisCheckpointer(BaseCheckpointSaver):
    """Redis-based checkpointer with TTL support"""
    
    def __init__(self, redis_client: redis.Redis, ttl: int = 86400):
        """
        Initialize Redis checkpointer
        
        Args:
            redis_client: Redis client instance
            ttl: Time to live for checkpoints in seconds (default: 24 hours)
        """
        self.redis = redis_client
        self.ttl = ttl
    
    def put(self, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> None:
        """Save checkpoint to Redis"""
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        self.redis.setex(
            key,
            timedelta(seconds=self.ttl),
            json.dumps(checkpoint)
        )
    
    def get(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve checkpoint from Redis"""
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def list(self, config: Dict[str, Any]) -> list[Dict[str, Any]]:
        """List all checkpoints (not implemented for Redis)"""
        return []


def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        password=Config.REDIS_PASSWORD if Config.REDIS_PASSWORD else None,
        decode_responses=False,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


def get_checkpointer() -> BaseCheckpointSaver:
    """Get checkpointer instance (Redis or fallback to Memory)"""
    try:
        redis_client = get_redis_client()
        redis_client.ping()  # Test connection
        return RedisCheckpointer(redis_client, ttl=Config.CONVERSATION_TTL)
    except Exception as e:
        import logging
        logging.warning(f"Redis connection failed, falling back to MemorySaver: {e}")
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
```

Update `agents/rag.py`:

```python
# Replace line 27
# OLD: memory = MemorySaver()
# NEW:
from utils.checkpointer import get_checkpointer
memory = get_checkpointer()
```

### Step 3.2: Update Prosa Endpoints

Update `utils/stt.py`:

```python
# Replace line 50
# OLD: url = "wss://asr-api.stg.prosa.ai/v2/speech/stt/streaming"
# NEW:
from config import Config
url = Config.PROSA_STT_URL
```

Update `utils/tts.py`:

```python
# Replace line 18
# OLD: url = "wss://tts-api.stg.prosa.ai/v2/speech/tts/streaming"
# NEW:
from config import Config
url = Config.PROSA_TTS_URL
```

### Step 3.3: Add Sentry Integration

Update `app.py` (add after imports):

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from config import Config

# Initialize Sentry
if Config.SENTRY_DSN:
    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        environment=Config.SENTRY_ENVIRONMENT,
    )
    logger.info("Sentry initialized")
```

### Step 3.4: Fix CORS Configuration

Update `app.py` CORS setup:

```python
# Replace lines 21-27
# OLD: CORS with origins="*"
# NEW:
from config import Config

CORS(
    app,
    resources={r"/*": {"origins": Config.CORS_ORIGINS}},
    supports_credentials=True,
    methods=["POST"],  # Only POST needed
    allow_headers=["Content-Type", "X-Conversation-Id", "X-API-Key"],
)
```

### Step 3.5: Add Rate Limiting

Update `app.py` (add after Flask initialization):

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=lambda: request.headers.get("X-API-Key", get_remote_address()),
    default_limits=[f"{Config.RATE_LIMIT_PER_HOUR} per hour"],
    enabled=Config.RATE_LIMIT_ENABLED,
    storage_uri=f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}",
)

# Apply to specific routes
@app.route("/v1/chat", methods=["POST"])
@limiter.limit("100 per hour")
def process_chat():
    # ... existing code
```

### Step 3.6: Add Request Size Limit

Update `app.py` (add after Flask initialization):

```python
from config import Config

app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
```

### Step 3.7: Fix API Key Comparison (Timing-Safe)

Update `app.py` (replace lines 55 and 84):

```python
import secrets
from config import Config

# Replace both occurrences
# OLD: if api_key != os.getenv("API_KEY"):
# NEW:
if not secrets.compare_digest(api_key, Config.API_KEY):
    raise APIError("Invalid API key", 401)
```

### Step 3.8: Disable Debug Mode

Update `app.py` (line 161):

```python
# Replace:
# OLD: app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
# NEW:
app.run(
    host=Config.HOST,
    port=Config.PORT,
    debug=Config.FLASK_DEBUG,
    use_reloader=False
)
```

### Step 3.9: Add Health Check Endpoint

Add to `app.py`:

```python
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for load balancer"""
    try:
        # Check Redis connection
        from utils.checkpointer import get_redis_client
        redis_client = get_redis_client()
        redis_client.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "redis": redis_status,
        "timestamp": int(time())
    })

@app.route("/ready", methods=["GET"])
def readiness_check():
    """Readiness check endpoint"""
    # Add checks for external services if needed
    return jsonify({"status": "ready"})
```

### Step 3.10: Create Production WSGI Entry Point

Create `wsgi.py` in project root:

```python
"""WSGI entry point for production deployment"""
from app import app
from config import Config

if __name__ == "__main__":
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=False
    )
```

### Step 3.11: Commit All Changes

```bash
git add .
git commit -m "feat: production hardening - Redis checkpointer, security, monitoring"
```

**Validation Checklist:**
- [ ] Redis checkpointer implemented and tested
- [ ] Prosa endpoints configurable via environment
- [ ] Sentry integration added
- [ ] CORS restricted to specific origins
- [ ] Rate limiting implemented
- [ ] Request size limit added
- [ ] Timing-safe API key comparison
- [ ] Debug mode disabled
- [ ] Health check endpoints added
- [ ] All tests passing

---

## Phase 4: Infrastructure Setup

**Duration:** 2-3 days  
**Priority:** HIGH  
**Risk:** MEDIUM

### Step 4.1: Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements-production.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-production.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
```

### Step 4.2: Create Docker Compose for Development

Create `docker-compose.yml`:

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
    env_file:
      - .env
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
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

volumes:
  redis_data:
```

### Step 4.3: Create .dockerignore

Create `.dockerignore`:

```
.env
.venv
venv
venv-prod
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.git
.gitignore
.dockerignore
docker-compose.yml
README.md
.cursor
*.md
.DS_Store
```

### Step 4.4: Test Docker Build

```bash
# Build image
docker build -t itb-chatbot:latest .

# Test run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f app

# Test health endpoint
curl http://localhost:8000/health

# Stop
docker-compose down
```

### Step 4.5: Choose Cloud Provider & Create Infrastructure

#### Option A: DigitalOcean (Recommended for Simplicity)

1. Create Droplet:
   ```
   - Ubuntu 22.04 LTS
   - 4 CPU, 16 GB RAM (for 1000 users)
   - 50 GB SSD
   - Region: Singapore (closest to Indonesia)
   ```

2. Create Managed Redis:
   ```
   - 2 CPU, 8 GB RAM
   - Region: Singapore
   ```

3. Set up Domain:
   ```
   - Add domain to DigitalOcean
   - Create A record pointing to Droplet IP
   ```

#### Option B: AWS

1. Create EC2 instance:
   ```
   - c5.xlarge (4 vCPU, 8 GB)
   - Ubuntu 22.04 AMI
   - 50 GB gp3 SSD
   - Region: ap-southeast-1 (Singapore)
   - Security group: Allow 22 (SSH), 80 (HTTP), 443 (HTTPS)
   ```

2. Create ElastiCache Redis:
   ```
   - cache.t3.medium (2 vCPU, 3.09 GB)
   - Engine version: 7.x
   - Same VPC as EC2
   ```

3. Create Application Load Balancer:
   ```
   - Internet-facing
   - Target: EC2 instance port 8000
   - Health check: /health
   ```

4. Set up Route 53:
   ```
   - Create hosted zone for domain
   - Create A record → ALB
   ```

### Step 4.6: Server Initial Setup

SSH into server:

```bash
ssh root@your-server-ip

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install -y docker-compose-plugin

# Create application directory
mkdir -p /opt/itb-chatbot
cd /opt/itb-chatbot

# Create deploy user
adduser --disabled-password deploy
usermod -aG docker deploy
chown -R deploy:deploy /opt/itb-chatbot
```

### Step 4.7: Set up SSL Certificate

```bash
# Install Certbot
apt-get install -y certbot python3-certbot-nginx

# Install Nginx
apt-get install -y nginx

# Get certificate
certbot certonly --nginx -d chatbot.itb.ac.id

# Certificate will be at:
# /etc/letsencrypt/live/chatbot.itb.ac.id/fullchain.pem
# /etc/letsencrypt/live/chatbot.itb.ac.id/privkey.pem
```

### Step 4.8: Configure Nginx as Reverse Proxy

Create `/etc/nginx/sites-available/itb-chatbot`:

```nginx
upstream app_server {
    server localhost:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name chatbot.itb.ac.id;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name chatbot.itb.ac.id;

    ssl_certificate /etc/letsencrypt/live/chatbot.itb.ac.id/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chatbot.itb.ac.id/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Request limits
    client_max_body_size 16M;
    client_body_timeout 120s;

    # Logging
    access_log /var/log/nginx/itb-chatbot-access.log;
    error_log /var/log/nginx/itb-chatbot-error.log;

    location / {
        proxy_pass http://app_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long requests (audio processing)
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://app_server;
        access_log off;
    }
}
```

Enable site:

```bash
ln -s /etc/nginx/sites-available/itb-chatbot /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Step 4.9: Commit Infrastructure Code

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker and infrastructure configuration"
```

**Validation Checklist:**
- [ ] Dockerfile builds successfully
- [ ] Docker Compose runs locally
- [ ] Cloud infrastructure provisioned
- [ ] SSL certificate obtained
- [ ] Nginx configured and running
- [ ] Health check accessible via HTTPS

---

## Phase 5: Monitoring & Observability

**Duration:** 1-2 days  
**Priority:** HIGH  
**Risk:** LOW

### Step 5.1: Enable LangSmith

Sign up and configure:

1. Go to https://smith.langchain.com/
2. Create account and project
3. Get API key from Settings
4. Add to `.env`:
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_key
   LANGCHAIN_PROJECT=itb-chatbot-production
   ```

### Step 5.2: Configure Sentry

1. Sign up at https://sentry.io/
2. Create new Python project
3. Get DSN
4. Add to `.env`:
   ```bash
   SENTRY_DSN=https://...@sentry.io/...
   SENTRY_ENVIRONMENT=production
   ```

### Step 5.3: Set up Structured Logging

Create `utils/logging_config.py`:

```python
"""Structured logging configuration"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """Format logs as JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields
        if hasattr(record, "conversation_id"):
            log_data["conversation_id"] = record.conversation_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        return json.dumps(log_data)

def setup_logging(level=logging.INFO):
    """Set up application logging"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
```

Update `app.py` to use structured logging:

```python
from utils.logging_config import setup_logging

# Replace line 17-18
# OLD: logging.basicConfig(level=logging.INFO)
# NEW:
setup_logging(level=logging.INFO)
```

### Step 5.4: Add Request Logging Middleware

Add to `app.py`:

```python
from time import time
import uuid

@app.before_request
def log_request_info():
    """Log incoming request"""
    request.start_time = time()
    request.request_id = str(uuid.uuid4())
    
    logger.info(
        "Incoming request",
        extra={
            "request_id": request.request_id,
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
        }
    )

@app.after_request
def log_response_info(response):
    """Log outgoing response"""
    duration = (time() - request.start_time) * 1000
    
    logger.info(
        "Request completed",
        extra={
            "request_id": request.request_id,
            "status_code": response.status_code,
            "duration_ms": duration,
        }
    )
    
    return response
```

### Step 5.5: Create Monitoring Dashboard Config

Create `monitoring/grafana-dashboard.json` (basic template):

```json
{
  "dashboard": {
    "title": "ITB Chatbot Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{"expr": "rate(http_requests_total[5m])"}]
      },
      {
        "title": "Response Time (p95)",
        "targets": [{"expr": "histogram_quantile(0.95, http_request_duration_seconds)"}]
      },
      {
        "title": "Error Rate",
        "targets": [{"expr": "rate(http_requests_total{status=~\"5..\"}[5m])"}]
      }
    ]
  }
}
```

### Step 5.6: Commit Monitoring Changes

```bash
git add utils/logging_config.py monitoring/
git commit -m "feat: add structured logging and monitoring"
```

**Validation Checklist:**
- [ ] LangSmith enabled and receiving traces
- [ ] Sentry enabled and receiving errors
- [ ] Structured JSON logging working
- [ ] Request/response logging middleware active
- [ ] Logs visible in Docker logs

---

## Phase 6: Security Hardening

**Duration:** 1 day  
**Priority:** CRITICAL  
**Risk:** LOW (mostly configuration)

### Step 6.1: Security Checklist Review

- [x] API key authentication (already implemented)
- [x] Timing-safe API key comparison (Phase 3)
- [x] CORS restricted (Phase 3)
- [x] Rate limiting (Phase 3)
- [x] Request size limits (Phase 3)
- [x] SSL/TLS enabled (Phase 4)
- [x] Security headers (Nginx config in Phase 4)
- [ ] Environment variable validation
- [ ] Input sanitization
- [ ] Dependency vulnerability scan
- [ ] Secrets rotation plan

### Step 6.2: Add Input Validation

Create `utils/validation.py`:

```python
"""Input validation utilities"""
import re
from typing import Optional
from models import APIError

def validate_conversation_id(conversation_id: str) -> str:
    """Validate conversation ID format"""
    # Allow alphanumeric, hyphens, underscores (UUID-like)
    if not re.match(r'^[a-zA-Z0-9_-]{1,128}$', conversation_id):
        raise APIError("Invalid conversation ID format", 400)
    return conversation_id

def validate_message(message: str) -> str:
    """Validate and sanitize user message"""
    if not message or not message.strip():
        raise APIError("Message cannot be empty", 400)
    
    # Limit message length
    if len(message) > 5000:
        raise APIError("Message too long (max 5000 characters)", 400)
    
    return message.strip()

def validate_audio_file(filename: str, size: int) -> None:
    """Validate audio file"""
    # Check file extension
    allowed_extensions = {'wav', 'mp3', 'flac', 'ogg', 'm4a', 'webm'}
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        raise APIError(
            f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}",
            400
        )
    
    # Check file size (already handled by Flask MAX_CONTENT_LENGTH, but double-check)
    max_size = 16 * 1024 * 1024  # 16 MB
    if size > max_size:
        raise APIError(f"Audio file too large (max {max_size // 1024 // 1024} MB)", 400)
```

Update `app.py` to use validation:

```python
from utils.validation import validate_conversation_id, validate_message, validate_audio_file

# In process_chat():
conversation_id = validate_conversation_id(request.headers.get("X-Conversation-Id"))
message = validate_message(json_data.get("message"))

# In process_audio():
conversation_id = validate_conversation_id(request.headers.get("X-Conversation-Id"))
validate_audio_file(audio_file.filename, len(audio_bytes))
```

### Step 6.3: Run Dependency Vulnerability Scan

```bash
# Install safety
pip install safety

# Scan dependencies
safety check --json

# Fix any vulnerabilities found
# Update requirements-production.txt accordingly
```

### Step 6.4: Create Security Policy

Create `SECURITY.md`:

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

Please report security vulnerabilities to: security@itb.ac.id

Do NOT open public issues for security vulnerabilities.

## Security Best Practices

### API Key Management
- Rotate API keys every 90 days
- Use separate keys for production and development
- Never commit API keys to version control

### Environment Variables
- Store in secure vault (not plain text on server)
- Use environment-specific values
- Audit access to production secrets

### Updates
- Update dependencies monthly
- Subscribe to security advisories for:
  - Flask
  - LangChain
  - OpenAI
  - All external services
```

### Step 6.5: Commit Security Enhancements

```bash
git add utils/validation.py SECURITY.md
git commit -m "feat: add input validation and security policy"
```

**Validation Checklist:**
- [ ] Input validation implemented
- [ ] Dependency scan completed and vulnerabilities fixed
- [ ] Security policy documented
- [ ] All security hardening items completed

---

## Phase 7: Performance Optimization

**Duration:** 1-2 days  
**Priority:** MEDIUM  
**Risk:** MEDIUM

### Step 7.1: Implement Caching Layer

Create `utils/cache.py`:

```python
"""Caching utilities"""
import hashlib
import json
from typing import Optional, Any
import redis
from config import Config

class CacheManager:
    """Manage caching for expensive operations"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = Config.CACHE_TTL
        self.enabled = Config.CACHE_ENABLED
    
    def _make_key(self, prefix: str, data: Any) -> str:
        """Create cache key from data"""
        data_str = json.dumps(data, sort_keys=True)
        hash_val = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"
    
    def get(self, prefix: str, data: Any) -> Optional[Any]:
        """Get cached value"""
        if not self.enabled:
            return None
        
        key = self._make_key(prefix, data)
        value = self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set(self, prefix: str, data: Any, value: Any) -> None:
        """Set cached value"""
        if not self.enabled:
            return
        
        key = self._make_key(prefix, data)
        self.redis.setex(key, self.ttl, json.dumps(value))
```

### Step 7.2: Cache Vector Search Results

Update `agents/rag.py`:

```python
from utils.cache import CacheManager
from utils.checkpointer import get_redis_client

# Add after memory initialization
cache = CacheManager(get_redis_client())

# Update fetch_documents tool
@tool
def fetch_documents(search_query: str) -> List[Document]:
    """Fetch documents from the vector database."""
    
    # Try cache first
    cached = cache.get("docs", search_query)
    if cached:
        print("CACHE HIT: fetch documents")
        return cached
    
    print("TOOL: fetch documents with search query:", search_query)
    docs = vectorstore.similarity_search_with_score(search_query, k=10)
    
    # Cache results
    cache.set("docs", search_query, docs)
    
    return docs
```

### Step 7.3: Optimize Gunicorn Configuration

Create `gunicorn.conf.py`:

```python
"""Gunicorn configuration for production"""
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "itb-chatbot"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if not using Nginx)
# keyfile = None
# certfile = None

def on_starting(server):
    """Called just before the master process is initialized."""
    print("Starting Gunicorn server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("Reloading Gunicorn server...")

def when_ready(server):
    """Called just after the server is started."""
    print("Gunicorn server is ready. Spawning workers...")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"Worker spawned (pid: {worker.pid})")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    print(f"Worker exited (pid: {worker.pid})")
```

Update Dockerfile CMD:

```dockerfile
# Replace:
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", ...]
# With:
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
```

### Step 7.4: Add Connection Pooling

Update `agents/models.py` to use connection pooling for Pinecone:

```python
# Configure Pinecone with connection pool
import pinecone

pinecone.init(
    api_key=os.getenv("PINECONE_API_KEY"),
    environment=os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp"),
    pool_threads=4  # Connection pooling
)
```

### Step 7.5: Commit Performance Optimizations

```bash
git add utils/cache.py gunicorn.conf.py
git commit -m "feat: add caching and optimize Gunicorn configuration"
```

**Validation Checklist:**
- [ ] Caching implemented for vector search
- [ ] Gunicorn configuration optimized
- [ ] Connection pooling configured
- [ ] Performance improvements validated

---

## Phase 8: Testing & Validation

**Duration:** 2-3 days  
**Priority:** HIGH  
**Risk:** LOW

### Step 8.1: Create Test Suite

Create `tests/test_api.py`:

```python
"""API endpoint tests"""
import pytest
import json
from app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_chat_no_auth(client):
    """Test chat endpoint without API key"""
    response = client.post('/v1/chat',
                           json={'message': 'Hello'},
                           headers={'X-Conversation-Id': 'test-123'})
    assert response.status_code == 400

def test_chat_invalid_key(client):
    """Test chat endpoint with invalid API key"""
    response = client.post('/v1/chat',
                           json={'message': 'Hello'},
                           headers={
                               'X-API-Key': 'invalid',
                               'X-Conversation-Id': 'test-123'
                           })
    assert response.status_code == 401

# Add more tests...
```

Run tests:

```bash
pytest tests/ -v
```

### Step 8.2: Manual Testing Checklist

Create `tests/manual-test-checklist.md`:

```markdown
# Manual Testing Checklist

## Pre-Deployment Testing

### Health Checks
- [ ] `/health` endpoint returns 200
- [ ] `/ready` endpoint returns 200
- [ ] Redis connection shown as "ok" in health check

### Text Chat Endpoint
- [ ] Send valid request → receives answer
- [ ] Send request without API key → 400 error
- [ ] Send request with invalid API key → 401 error
- [ ] Send request without conversation ID → 400 error
- [ ] Send empty message → 400 error
- [ ] Send very long message (>5000 chars) → 400 error
- [ ] Send multiple requests with same conversation ID → context maintained
- [ ] Rate limit triggers after 100 requests in 1 hour

### Audio Chat Endpoint
- [ ] Upload valid audio file → receives transcript and answer
- [ ] Upload without API key → 400 error
- [ ] Upload invalid file format → 400 error
- [ ] Upload very large file (>16MB) → 413 error
- [ ] Check exec_time in response for all components
- [ ] Verify audio response is valid WAV format

### Security
- [ ] CORS only allows configured origins
- [ ] Security headers present in all responses
- [ ] HTTPS redirects working (HTTP → HTTPS)
- [ ] SSL certificate valid and not expired

### Performance
- [ ] Text chat response < 5 seconds (p95)
- [ ] Audio chat response < 20 seconds (p95)
- [ ] Caching working (second identical request faster)
- [ ] Multiple concurrent requests handled correctly

### Monitoring
- [ ] Logs appearing in Sentry
- [ ] Traces appearing in LangSmith
- [ ] Structured JSON logs in Docker logs
- [ ] Error tracking working (trigger error, check Sentry)
```

### Step 8.3: Load Testing

Create `tests/load_test.py`:

```python
"""Load testing with locust"""
from locust import HttpUser, task, between
import random

class ChatbotUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Set up headers"""
        self.headers = {
            "X-API-Key": "your_test_api_key",
            "X-Conversation-Id": f"load-test-{random.randint(1, 1000)}",
            "Content-Type": "application/json"
        }
    
    @task(10)
    def chat_text(self):
        """Test text chat endpoint"""
        messages = [
            "Apa itu ITB?",
            "Fakultas apa saja di ITB?",
            "Bagaimana cara mendaftar?",
            "Kapan pendaftaran dibuka?"
        ]
        
        self.client.post(
            "/v1/chat",
            json={"message": random.choice(messages)},
            headers=self.headers
        )
    
    @task(1)
    def health_check(self):
        """Test health endpoint"""
        self.client.get("/health")
```

Run load test:

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=https://chatbot.itb.ac.id

# Access web UI at http://localhost:8089
# Test with:
# - 100 users
# - Spawn rate: 10 users/second
# - Duration: 10 minutes
```

### Step 8.4: Integration Testing with External Services

Test each external service:

```bash
# Test Together AI
curl -X POST https://api.together.xyz/v1/chat/completions \
  -H "Authorization: Bearer $TOGETHER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-72B-Instruct-Turbo", "messages": [{"role": "user", "content": "Hi"}]}'

# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Pinecone
python -c "from agents.models import vectorstore; print(vectorstore.similarity_search('test', k=1))"

# Test Redis
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
```

### Step 8.5: Commit Testing Code

```bash
git add tests/
git commit -m "test: add comprehensive test suite"
```

**Validation Checklist:**
- [ ] Unit tests written and passing
- [ ] Manual test checklist completed
- [ ] Load testing performed (100+ concurrent users)
- [ ] Integration tests with external services passing
- [ ] Performance meets requirements

---

## Phase 9: Deployment

**Duration:** 1 day  
**Priority:** CRITICAL  
**Risk:** HIGH

### Step 9.1: Pre-Deployment Checklist

- [ ] All code changes committed and pushed
- [ ] All tests passing
- [ ] Environment variables configured on server
- [ ] Infrastructure provisioned (server, Redis, domain, SSL)
- [ ] Nginx configured and tested
- [ ] Monitoring enabled (Sentry, LangSmith)
- [ ] Backups configured (if applicable)
- [ ] Team notified of deployment window
- [ ] Rollback plan reviewed

### Step 9.2: Deploy to Server

On local machine:

```bash
# Push latest code
git push origin feat/production-hardening

# Create release tag
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0
```

On server:

```bash
# SSH into server
ssh deploy@your-server-ip

# Navigate to app directory
cd /opt/itb-chatbot

# Clone repository (first time only)
git clone https://github.com/your-org/itb-chatbot.git .

# Or pull latest changes
git pull origin main
git checkout v1.0.0

# Create .env file (copy from secure location or set manually)
nano .env
# [Fill in all environment variables]

# Build and start with Docker Compose
docker-compose build
docker-compose up -d

# Check logs
docker-compose logs -f app

# Verify health
curl http://localhost:8000/health
```

### Step 9.3: Verify Deployment

```bash
# Check all containers running
docker-compose ps

# Check health via HTTPS
curl https://chatbot.itb.ac.id/health

# Test chat endpoint
curl -X POST https://chatbot.itb.ac.id/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Conversation-Id: deploy-test-$(date +%s)" \
  -d '{"message": "Apa itu ITB?"}'

# Check logs for errors
docker-compose logs app | grep -i error

# Monitor resource usage
docker stats
```

### Step 9.4: Smoke Testing

Run through manual test checklist (Phase 8.2) on production URL.

### Step 9.5: Configure Monitoring Alerts

In Sentry:
1. Go to Alerts → Create Alert
2. Set up alerts for:
   - Error rate > 5% for 5 minutes
   - Response time p95 > 30 seconds
3. Add notification channels (email, Slack)

In LangSmith:
1. Check that traces are appearing
2. Set up monitoring dashboard

### Step 9.6: Update Documentation

Update README.md with production deployment info:

```markdown
# ITB RAG Chatbot

## Production Deployment

**Production URL:** https://chatbot.itb.ac.id

**Version:** 1.0.0

**Deployed:** [Date]

## API Endpoints

- `POST /v1/chat` - Text-based chat
- `POST /v1/audio` - Audio-based chat
- `GET /health` - Health check
- `GET /ready` - Readiness check

## Monitoring

- **Sentry:** [Sentry project URL]
- **LangSmith:** [LangSmith project URL]

## Support

For issues, contact: support@itb.ac.id
```

**Validation Checklist:**
- [ ] Application deployed and running
- [ ] Health checks passing
- [ ] Smoke tests completed successfully
- [ ] Monitoring and alerting configured
- [ ] Documentation updated

---