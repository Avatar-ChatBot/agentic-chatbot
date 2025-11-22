"""Input validation utilities"""
import re
from typing import Optional
from models import APIError


def validate_conversation_id(conversation_id: str) -> str:
    """Validate conversation ID format"""
    if not conversation_id:
        raise APIError("X-Conversation-Id header is required", 400)
    
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
    
    # Check file size
    max_size = 16 * 1024 * 1024  # 16 MB
    if size > max_size:
        raise APIError(f"Audio file too large (max {max_size // 1024 // 1024} MB)", 400)

