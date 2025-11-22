# Agentic Chatbot - ITB RAG Chatbot System

## Project Overview
This is an intelligent chatbot system for Bandung Institute of Technology (Institut Teknologi Bandung / ITB) that answers questions about ITB's academic information. The system uses Retrieval-Augmented Generation (RAG) with multi-modal support (text and audio input), emotion analysis, and speech synthesis.

## Core Features
1. **RAG-based Question Answering**: Uses vector database (Pinecone) to retrieve relevant documents and answer questions about ITB
2. **Multi-modal Input**: Supports both text-based chat and audio input
3. **Emotion Analysis**: Analyzes user emotion from audio and adjusts responses accordingly
4. **Speech-to-Text (STT)**: Converts audio input to text using Prosa AI
5. **Text-to-Speech (TTS)**: Converts text responses to audio using Prosa AI
6. **Conversation Memory**: Maintains conversation context using LangGraph checkpointer
7. **Performance Tracking**: Tracks execution time for each component (STT, emotion, RAG, TTS)

## Technology Stack

### Backend Framework
- **Flask**: Web framework for REST API
- **Flask-CORS**: Cross-origin resource sharing support
- Python 3.x with async/await support

### LLM & AI Stack
- **LangChain**: LLM orchestration framework (v0.3.7)
- **LangGraph**: Agent workflow management (v0.2.48)
- **ChatTogether**: Primary LLM provider (Qwen/Qwen2.5-72B-Instruct-Turbo)
- **OpenAI**: Text embeddings (text-embedding-3-large) and fallback LLM (gpt-4o-mini)
- **Pinecone**: Vector database for document storage and retrieval

### External Services
- **Prosa AI**: Indonesian speech-to-text and text-to-speech services
- **Custom Emotion Analysis API**: Emotion detection from audio and text

### Other Dependencies
- **python-dotenv**: Environment variable management
- **websockets**: WebSocket connections for streaming STT/TTS
- **pydub**: Audio processing
- **httpx**: Async HTTP client
- **pydantic**: Data validation

## Project Structure

```
agentic-chatbot/
├── app.py                  # Main Flask application with API endpoints
├── agents/                 # Agent implementations
│   ├── models.py          # LLM and vector store initialization
│   ├── rag.py             # RAG agent with document fetching tool
│   └── sql.py             # SQL agent (currently unused)
├── prompts/               # System prompts for agents
│   ├── rag.py            # RAG agent system message
│   └── sql.py            # SQL agent system message
├── utils/                 # Utility functions
│   ├── emotion.py        # Emotion analysis integration
│   ├── stt.py            # Speech-to-text using Prosa AI
│   └── tts.py            # Text-to-speech using Prosa AI
├── models/                # Custom models
│   └── APIError.py       # Custom API error class
├── assets/               # Static assets (e.g., ITB logo)
└── requirements.txt      # Python dependencies
```

## API Endpoints

### 1. POST /v1/chat
Text-based chat endpoint
- **Headers**: `X-API-Key`, `X-Conversation-Id`
- **Body**: `{"message": "user question"}`
- **Response**: `{"answer": "...", "sources": "..."}`

### 2. POST /v1/audio
Audio-based chat endpoint with full pipeline
- **Headers**: `X-API-Key`, `X-Conversation-Id`
- **Body**: multipart/form-data with audio file
- **Response**: JSON with transcript, answer, sources, audio bytes, and execution times

## Code Style Guidelines

### Python Style
- Use type hints for function parameters and return values
- Use async/await for I/O-bound operations (STT, TTS, emotion analysis, HTTP requests)
- Follow PEP 8 naming conventions (snake_case for functions/variables)
- Use descriptive variable names
- Add docstrings for tools and complex functions

### LangChain/LangGraph Patterns
- Use `@tool` decorator for LangChain tools with clear docstrings
- Use `create_react_agent` for agent creation
- Use `MemorySaver` for conversation memory with thread_id-based checkpointing
- Stream agent responses using `agent.stream()` with `stream_mode="values"`
- Use system messages in Llama chat template format with `<|start_header_id|>` and `<|eot_id|>` tags

### Error Handling
- Use custom `APIError` class for API errors with status codes
- Handle exceptions at API route level and convert to appropriate error responses
- Log errors using Python's logging module
- Gracefully handle external service failures (emotion analysis, STT, TTS)

### Configuration Management
- Store all secrets and API keys in `.env` file
- Use `python-dotenv` to load environment variables
- Never hardcode API keys or sensitive data

## Environment Variables Required

```bash
# API Security
API_KEY=your_api_key_here

# LLM & Embeddings
OPENAI_API_KEY=your_openai_key
TOGETHER_API_KEY=your_together_key

# Vector Database
PINECONE_API_KEY=your_pinecone_key

# Speech Services (Prosa AI)
PROSA_STT_API_KEY=your_prosa_stt_key
PROSA_TTS_API_KEY=your_prosa_tts_key

# Emotion Analysis
EMOTION_ANALYSIS_URL=your_emotion_api_url

# Database (optional, for SQL agent)
SUPABASE_URI=your_database_uri
```

## Language & Localization
- Primary language: **Bahasa Indonesia** (Indonesian)
- System prompts are in English, but responses are in Indonesian
- RAG agent is specifically designed for ITB (Indonesian university) context
- Uses Indonesian TTS voice model (tts-ghifari-professional)

## RAG System Details

### Document Retrieval
- Tool: `fetch_documents(search_query: str)`
- Retrieves top 10 most relevant documents using similarity search
- Returns documents with similarity scores from Pinecone

### Response Generation
- Agent reformulates user questions into effective search queries
- Uses chat history for context-aware query reformulation
- Extracts thinking process with `</think>` separator
- Extracts source links with `<|source_sep|>` separator
- Responds with concise, TTS-friendly answers (single paragraph, no lists)

### Answer Format
```
<answer text> <|source_sep|> https://link-1.com, https://link-2.com
```

## LLM Configuration

### Primary LLM
- Model: `Qwen/Qwen2.5-72B-Instruct-Turbo` (via Together AI)
- Temperature: 0 (deterministic)
- Use case: Main RAG agent

### Secondary LLM
- Model: `gpt-4o-mini` (via OpenAI)
- Temperature: 0
- Use case: Fallback/alternative model

### Embeddings
- Model: `text-embedding-3-large` (OpenAI)
- Vector store: Pinecone index `informasi-umum-itb`

## Development Notes

### Commented/Unused Features
- SQL agent (`agents/sql.py`) is implemented but not currently used in main API
- Alternative LLM options are commented out in `agents/models.py` (Groq, Fireworks, DeepSeek)
- Jina embeddings option is commented out
- Alternative TTS polling method exists but streaming is preferred

### Performance Monitoring
- All major operations are timed: STT, emotion analysis, RAG processing, TTS
- Execution times are returned in API response for audio endpoint
- Use `logger.info()` for important events, `logger.error()` for errors

### Audio Processing
- Audio is compressed to FLAC format (64k bitrate) before emotion analysis
- TTS output is in WAV format at 8kHz sample rate
- Audio bytes are hex-encoded for JSON transport

## Testing & Debugging
- Use `pretty_print()` on messages for debugging agent output
- Print statements track tool calls and agent steps
- Check terminal output for streaming messages during development
- Test with both `/v1/chat` and `/v1/audio` endpoints

## Common Tasks

### Adding a New Tool
1. Define tool with `@tool` decorator in appropriate agent file
2. Add clear docstring with parameter descriptions
3. Add tool to tools list
4. Update agent system message to describe the tool

### Changing LLM Provider
1. Update imports in `agents/models.py`
2. Update `llm` variable initialization
3. Ensure temperature and model parameters are set
4. Test thoroughly as prompt formats may differ

### Modifying RAG Behavior
1. Edit system message in `prompts/rag.py`
2. Adjust retrieval parameters in `fetch_documents` tool (k value)
3. Modify answer extraction logic in `process_rag()` if needed

## Security Considerations
- API key authentication required for all endpoints
- CORS configured to allow all origins (adjust for production)
- No DML statements allowed in SQL agent
- Input validation for required fields
- Conversation isolation using unique thread IDs

## Future Enhancements
- Reactivate SQL agent for database queries
- Add rate limiting
- Implement caching for frequently asked questions
- Add more comprehensive logging and monitoring
- Consider adding user feedback mechanism
- Explore other LLM options (DeepSeek-V3, QwQ-32B, etc.)

