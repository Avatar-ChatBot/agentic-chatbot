"""Configuration management for ITB RAG Chatbot"""
import os
from typing import List
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
    def validate(cls) -> List[str]:
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
    import logging
    logging.warning("Configuration validation warnings:")
    for error in validation_errors:
        logging.warning(f"  - {error}")



