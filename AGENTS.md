# AGENTS.md - ITB RAG Chatbot Development Guide

## Build & Development Commands

### Docker (Primary)
```bash
docker-compose build    # Build images
docker-compose up -d    # Start all services
docker-compose down      # Stop services
docker-compose logs -f   # View logs
```

### Local Development
```bash
pip install -r requirements.txt
gunicorn --config gunicorn.conf.py wsgi:application
streamlit run streamlit.py
```

### Linting & Formatting
```bash
ruff check .           # Lint
ruff check --fix .     # Auto-fix
ruff format .           # Format
python validate.py        # Validate deployment
```

## Code Style Guidelines

### Python Conventions
- **Version**: 3.10.12+, type hints required
- **Naming**: snake_case (functions/variables), PascalCase (classes)
- **Docstrings**: Google-style for tools, complex functions, classes

### Imports (Standard → Third-party → Local)
```python
import os
from typing import List, Dict, Any

from flask import Flask, jsonify
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from config import Config
from agents.rag import process_rag
from utils.logging_config import setup_logging
```

### Error Handling
- Use custom `APIError` class: `raise APIError(message="...", code=400, details="...")`
- Log with structured logging: `logger.error("Message", extra={"key": "value"})`
- Gracefully degrade for optional services (emotion analysis → default "neutral")

### Logging
- **Structured**: JSON formatter via `setup_logging()`
- **Context**: request_id, conversation_id, endpoint, duration_ms
- **Levels**: INFO (normal), ERROR (failures), WARNING (deprecations)

### LangChain/LangGraph
- **Tools**: `@tool` decorator with clear docstrings
- **Agent**: `create_react_agent(llm=llm, tools=[...], checkpointer=get_checkpointer())`
- **Streaming**: `agent.stream(..., stream_mode="values")`

### Async/Await
**Required for**: STT, TTS, emotion analysis, HTTP, WebSocket operations

### Configuration
- **Never hardcode** secrets - use `Config` class from `config.py`
- **Required env vars**: `API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `QDRANT_URL`
- **Optional**: `QDRANT_API_KEY` (HTTPS only), `EMOTION_ANALYSIS_URL`

### Flask API
- **Validation**: Use decorators from `utils.validation`
- **Rate Limiting**: Flask-Limiter with Redis backend
- **CORS**: Configured for all origins (adjust for production)
- **Health Check**: `/health` endpoint returning JSON status

### Vector Store (Qdrant)
- **Embedding**: OpenAI `text-embedding-3-large` (default), OpenRouter `qwen3-embedding-8b`
- **Collection**: `informasi-umum-itb` (configurable via `QDRANT_COLLECTION_NAME`)
- **Retrieval**: Top-K similarity search (K=10)
- **Local Dev**: HTTP `http://localhost:6333` (no API key)
- **Production**: HTTPS with `QDRANT_API_KEY`

### Conversation Memory
- **Checkpointer**: Redis via LangGraph `MemorySaver`
- **TTL**: 24 hours default (`CONVERSATION_TTL`)
- **Thread ID**: UUID for `configurable.thread_id`

### Audio Processing
- **STT/TTS**: Prosa AI via WebSocket
- **Format**: FLAC (input), WAV 8kHz (output)
- **Encoding**: Audio bytes hex-encoded for JSON
- **Timeouts**: Configurable via `STT_TIMEOUT`, `TTS_TIMEOUT` (default 30s)

## Testing
- **No formal test suite**: `test.py` is a scraper
- **Validation**: `validate.py` checks imports, config, modules
- **Manual**: Use Streamlit UI or API with curl/Postman

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -H "X-Conversation-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{"message": "Apa program studi di STEI?"}'
```

## Project Structure
```
agentic-chatbot/
├── app.py              # Flask app
├── config.py           # Configuration
├── agents/             # LangChain agents (models.py, rag.py)
├── prompts/            # System prompts
├── utils/              # Utilities (stt, tts, emotion, checkpointer, logging, validation)
├── models/             # Custom models (APIError.py)
├── scripts/            # Utility scripts
└── streamlit.py        # Web UI
```

## Cursor Rules (.cursor/rules/general.md)

### Core Guidelines
- Use type hints for all functions
- Use async/await for I/O operations (STT, TTS, emotion, HTTP)
- Follow PEP 8 naming (snake_case)
- Add docstrings for LangChain tools and complex functions
- Never hardcode API keys - use Config class
- Gracefully handle external service failures

### LangChain/LangGraph
- Use `@tool` decorator for LangChain tools
- Use `create_react_agent` for agent creation
- Use `MemorySaver` for conversation memory
- Stream with `agent.stream()` and `stream_mode="values"`
- System messages in Llama chat template format

### Configuration
- Store secrets in `.env` file
- Use `python-dotenv` to load env vars
- Never commit `.env` to repository

### Language
- **Primary**: Bahasa Indonesia (Indonesian)
- System prompts in English, responses in Indonesian
- RAG agent designed for ITB (Indonesian university) context
- Use Indonesian TTS voice model (tts-ghifari-professional)

## Important Notes
- **Worker Limits**: Gunicorn capped at 4 workers (each creates Qdrant client)
- **No DML**: SQL agent must be read-only
- **Monitoring**: LangSmith tracing via `LANGCHAIN_TRACING_V2`
- **Redis Used**: Checkpointer + rate limiting backend
- **Snapshots**: Auto-restored on container start if collection missing
