# ITB RAG Chatbot - Deployment Guide

## ✅ Deployment Status

**Status:** ✅ READY FOR PRODUCTION  
**Docker:** ✅ Running  
**Health Check:** ✅ Passing  
**Redis:** ✅ Connected  

---

## 🎉 What Has Been Implemented

### 1. **Production Configuration Management** (`config.py`)
- Centralized environment variable management
- Validation for required variables
- Defaults for optional settings
- Type-safe configuration access

### 2. **Async Support**
- ASGI wrapper using `asgiref.wsgi.WsgiToAsgi`
- Uvicorn workers for handling async routes (`/v1/audio`)
- Proper async/await support for STT, TTS, and emotion analysis

### 3. **Redis-Based Conversation Persistence** (`utils/checkpointer.py`)
- Replaced in-memory `MemorySaver` with `RedisCheckpointer`
- TTL-based conversation expiry (default: 24 hours)
- Automatic fallback to `MemorySaver` if Redis is unavailable
- Thread-safe conversation history across workers

### 4. **Structured JSON Logging** (`utils/logging_config.py`)
- JSON-formatted logs for easy parsing
- Request IDs for tracing
- Duration tracking for performance monitoring
- Before/after request middleware for automatic logging

### 5. **Input Validation** (`utils/validation.py`)
- API key validation (timing-safe comparison)
- Conversation ID format validation
- Message length and content validation
- Audio file type and size validation

### 6. **Security Hardening**
- Timing-safe API key comparison using `secrets.compare_digest()`
- CORS configuration (configurable origins)
- Rate limiting using Redis backend (100 req/hour by default)
- Request size limits (16 MB default)
- Security headers (can be added via Nginx in production)

### 7. **Health Check Endpoints**
- `GET /health` - Detailed health status with Redis connection check
- `GET /ready` - Readiness probe for Kubernetes/load balancers

### 8. **Docker Setup**
- **Dockerfile**: Multi-stage build with security best practices
  - Non-root user (`appuser`)
  - System dependencies (ffmpeg, curl)
  - Health check built-in
  - Exposes ports 8000 (Flask) and 8501 (Streamlit)
- **docker-compose.yml**: Complete stack with Redis
  - **app**: Flask API container with health checks (port 8000)
  - **streamlit**: Streamlit web interface (port 8501)
  - **redis**: Redis container with persistence
  - Volume mounting for Redis data
  - Automatic dependency management
  - All services share the same environment variables

### 9. **Gunicorn Configuration** (`gunicorn.conf.py`)
- Uvicorn workers for ASGI support
- Worker count: `CPU * 2 + 1`
- Graceful shutdown and reload
- Worker lifecycle hooks
- Request timeout: 120s

### 10. **Environment-Based Configuration**
- Production-ready URLs for Prosa services (configurable)
- All hardcoded values moved to environment variables
- Centralized timeout configurations

---

## 📦 Project Structure

```
agentic-chatbot/
├── app.py                      # Main Flask app with async support
├── streamlit.py                # Streamlit web interface
├── wsgi.py                     # ASGI entry point
├── config.py                   # Configuration management
├── gunicorn.conf.py            # Gunicorn configuration
├── validate.py                 # Deployment validation script
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker stack definition
├── .dockerignore               # Docker build exclusions
├── requirements.txt            # Python dependencies
├── agents/
│   ├── models.py              # LLM and vector store setup
│   └── rag.py                 # RAG agent with Redis checkpointer
├── utils/
│   ├── checkpointer.py        # Redis-based conversation persistence
│   ├── logging_config.py      # Structured JSON logging
│   ├── validation.py          # Input validation utilities
│   ├── stt.py                 # Speech-to-text (uses config)
│   ├── tts.py                 # Text-to-speech (uses config)
│   └── emotion.py             # Emotion analysis (uses config)
└── prompts/
    └── rag.py                 # RAG system prompts
```

---

## 🚀 Quick Start

### 1. Start the Application

```bash
# Start all services (app + Streamlit + Redis)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app        # Flask API logs
docker-compose logs -f streamlit  # Streamlit logs
```

### 2. Verify Health

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "redis": "ok",
#   "timestamp": 1763803034
# }
```

### 3. Access the Streamlit Web Interface

```bash
# Streamlit app is available at:
# http://localhost:8501

# Open in your browser
open http://localhost:8501  # macOS
# or
xdg-open http://localhost:8501  # Linux
# or just navigate to http://localhost:8501 in any browser
```

The Streamlit interface provides a user-friendly chat interface with:
- Chat history
- Source citations
- ITB logo
- Conversation persistence (uses same Redis backend)

### 4. Test Chat Endpoint (API)

```bash
# Set your API key
export API_KEY="your-api-key-from-env"

# Test text chat
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: test-$(date +%s)" \
  -d '{"message": "Apa itu ITB?"}'
```

---

## 🔧 Configuration

### Environment Variables

All configuration is managed through environment variables in `.env`:

**Required:**
- `API_KEY` - API authentication key
- `OPENAI_API_KEY` - OpenAI API key (embeddings)
- `OPENROUTER_API_KEY` - OpenRouter API key (LLM)
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
- `QDRANT_API_KEY` - Qdrant API key for authentication
- `QDRANT_COLLECTION_NAME` - Qdrant collection name (default: informasi-umum-itb)

**Optional (with defaults):**
- `REDIS_HOST` - Redis host (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `CONVERSATION_TTL` - Conversation expiry in seconds (default: 86400)
- `RATE_LIMIT_PER_HOUR` - Rate limit (default: 100)
- `CORS_ORIGINS` - Allowed CORS origins (default: *)

See `.env.sample` or deployment plan for full list.

---

## 📊 Monitoring & Observability

### Structured Logs

All logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2025-11-22T09:17:23.567364",
  "level": "INFO",
  "logger": "app",
  "message": "Request completed",
  "duration_ms": 2147.81,
  "request_id": "0587328d-e98a-4ee9-8139-b01501f82573"
}
```

### View Logs

```bash
# Application logs
docker-compose logs app

# Follow logs in real-time
docker-compose logs -f app

# Filter for errors
docker-compose logs app | grep ERROR

# View JSON logs
docker-compose logs app --no-log-prefix | grep "^\{"
```

### Metrics Tracked

- Request duration (ms)
- Request ID for tracing
- STT/TTS/Emotion/RAG execution times
- Redis connection status

---

## 🧪 Testing & Validation

### Run Validation Script

```bash
python3 validate.py
```

This checks:
- ✅ All dependencies installed
- ✅ Configuration valid
- ✅ App module imports
- ✅ Agent modules load
- ✅ Utility modules work
- ✅ Docker files present

### Manual Testing Checklist

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Ready check
curl http://localhost:8000/ready

# 3. Chat endpoint (valid)
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: test-123" \
  -d '{"message": "Hello"}'

# 4. Error handling (no API key)
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Conversation-Id: test-123" \
  -d '{"message": "Hello"}'

# 5. Conversation persistence
CONV_ID="persist-test-$(date +%s)"
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: ${CONV_ID}" \
  -d '{"message": "Saya tertarik dengan ITB"}'

curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: ${CONV_ID}" \
  -d '{"message": "Bagaimana cara mendaftar?"}'
```

---

## 🐳 Docker Commands

### Basic Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f app        # Flask API
docker-compose logs -f streamlit  # Streamlit app
docker-compose logs -f            # All services

# Execute command in container
docker-compose exec app bash
docker-compose exec streamlit bash
```

### Debugging

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats

# Inspect Redis data
docker-compose exec redis redis-cli
> KEYS checkpoint:*
> GET checkpoint:your-conversation-id

# Check health from inside container
docker-compose exec app curl localhost:8000/health
```

---

## 🎯 API Endpoints

### POST /v1/chat
Text-based chat endpoint.

**Headers:**
- `X-API-Key` (required) - API authentication key
- `X-Conversation-Id` (required) - Unique conversation identifier

**Request Body:**
```json
{
  "message": "Your question here"
}
```

**Response:**
```json
{
  "answer": "Response from chatbot",
  "sources": "https://source1.com, https://source2.com"
}
```

### POST /v1/audio
Audio-based chat endpoint with full pipeline (STT → Emotion → RAG → TTS).

**Headers:**
- `X-API-Key` (required)
- `X-Conversation-Id` (required)

**Request Body:**
- `multipart/form-data` with `audio` file

**Response:**
```json
{
  "audio": "hex-encoded-wav-bytes",
  "transcript": "Transcribed text",
  "answer": "Response from chatbot",
  "sources": "https://source1.com",
  "exec_time": {
    "speech_to_text": 2.5,
    "emotion_analysis": 1.2,
    "process_rag": 3.8,
    "text_to_speech": 2.1,
    "total": 9.6
  }
}
```

### GET /health
Health check endpoint with detailed status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis": "ok",
  "timestamp": 1763803034
}
```

### GET /ready
Simple readiness check for load balancers.

**Response:**
```json
{
  "status": "ready"
}
```

---

## 🔒 Security Features

1. **API Key Authentication**: All endpoints require valid API key
2. **Timing-Safe Comparison**: Prevents timing attacks on API keys
3. **Rate Limiting**: 100 requests/hour per API key (configurable)
4. **Input Validation**: 
   - Message length limits (max 5000 chars)
   - Conversation ID format validation
   - Audio file type and size limits
5. **CORS Configuration**: Configurable allowed origins
6. **Request Size Limits**: 16 MB maximum (configurable)
7. **Non-root Container**: Docker runs as `appuser` (UID 1000)

---

## 🔄 Redis Conversation Management

### How It Works

1. Each conversation is identified by `X-Conversation-Id`
2. Conversation history stored in Redis: `checkpoint:{conversation_id}`
3. Automatic expiry after 24 hours (configurable via `CONVERSATION_TTL`)
4. Fallback to in-memory storage if Redis is unavailable

### Inspect Conversations

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# List all conversations
KEYS checkpoint:*

# View specific conversation
GET checkpoint:your-conversation-id

# Check expiry time (TTL in seconds)
TTL checkpoint:your-conversation-id
```

---

## 📈 Performance

### Current Configuration

- **Workers**: CPU count * 2 + 1 (e.g., 9 workers on 4-core machine)
- **Worker Class**: Uvicorn (ASGI support)
- **Request Timeout**: 120 seconds
- **Keepalive**: 5 seconds
- **Max Requests per Worker**: 1000 (with jitter)

### Typical Response Times

- `/health`: < 10ms
- `/v1/chat`: 2-5 seconds (depends on LLM)
- `/v1/audio`: 10-20 seconds (full pipeline)

---

## 🚨 Troubleshooting

### Container won't start

```bash
# Check logs for errors
docker-compose logs app

# Verify environment variables
docker-compose config

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

### Redis connection errors

```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Health check failing

```bash
# Check app logs
docker-compose logs app --tail 50

# Test health endpoint directly
curl -v http://localhost:8000/health

# Verify port binding
docker-compose ps
```

### High memory usage

```bash
# Check resource usage
docker stats

# Reduce worker count in gunicorn.conf.py
# Edit: workers = 4  # Instead of CPU * 2 + 1

# Restart
docker-compose restart app
```

---

## 🎓 Next Steps

### For Production Deployment

1. **SSL/TLS**: Set up Nginx reverse proxy with Let's Encrypt
2. **Domain**: Configure DNS A record to server IP
3. **Monitoring**: Add Sentry for error tracking
4. **Observability**: Enable LangSmith for LLM tracing
5. **Backups**: Set up Redis persistence and backups
6. **Scaling**: Use Docker Swarm or Kubernetes for multi-server deployment
7. **CI/CD**: Automate deployment with GitHub Actions

### Recommended Production Stack

```
[Client] → [Nginx + SSL] → [Load Balancer] → [Docker Containers] → [Managed Redis]
                                                     ↓
                                              [Sentry + LangSmith]
```

---

## 📚 Additional Resources

- Deployment Plan: `.cursor/plans/deployment-plan.md`
- Validation Script: `validate.py`
- Example Environment: `.env.sample`
- Gunicorn Docs: https://docs.gunicorn.org/
- Docker Compose: https://docs.docker.com/compose/

---

## ✅ Verification Results

**All systems tested and working:**

✅ Docker build successful  
✅ Containers running (app + redis)  
✅ Health check passing  
✅ Redis connection active  
✅ Chat endpoint responding  
✅ Error handling working  
✅ Input validation working  
✅ Conversation persistence working  
✅ Structured logging active  
✅ Rate limiting configured  
✅ Async support enabled  

**Ready for production deployment! 🚀**



