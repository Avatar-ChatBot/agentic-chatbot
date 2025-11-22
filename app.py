import logging
import secrets
import uuid
from time import time

from asgiref.wsgi import WsgiToAsgi
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from agents.rag import process_rag
from config import Config
from models import APIError
from utils import text_to_speech
from utils.emotion import analyze_emotion
from utils.logging_config import setup_logging
from utils.stt import speech_to_text_streaming
from utils.validation import validate_conversation_id, validate_message, validate_audio_file

load_dotenv()

# Setup structured logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
CORS(
    app,
    resources={r"/*": {"origins": Config.CORS_ORIGINS}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Conversation-Id", "X-API-Key"],
)

# Configure request size limit
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=lambda: request.headers.get("X-API-Key", get_remote_address()),
    default_limits=[f"{Config.RATE_LIMIT_PER_HOUR} per hour"] if Config.RATE_LIMIT_ENABLED else [],
    enabled=Config.RATE_LIMIT_ENABLED,
    storage_uri=f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}" if Config.RATE_LIMIT_ENABLED else None,
)


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
    if hasattr(request, 'start_time'):
        duration = (time() - request.start_time) * 1000
        
        logger.info(
            "Request completed",
            extra={
                "request_id": getattr(request, 'request_id', 'unknown'),
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
            }
        )
    
    return response


@app.errorhandler(APIError)
def handle_api_error(error: APIError):
    timestamp = int(time())
    logger.error(
        f"API Error: {error.message}",
        extra={
            "request_id": getattr(request, 'request_id', 'unknown'),
            "error_code": error.code,
            "error_details": error.details,
        }
    )

    return (
        jsonify(
            dict(
                status=error.code,
                message=error.message,
                details=error.details,
                timestamp=timestamp,
            )
        ),
        error.code,
    )


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
    return jsonify({"status": "ready"})


@app.route("/v1/chat", methods=["POST"])
@limiter.limit(f"{Config.RATE_LIMIT_PER_HOUR} per hour")
def process_chat():
    try:
        # Validate API key (timing-safe comparison)
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise APIError("X-API-Key header is required", 400)

        if not secrets.compare_digest(api_key, Config.API_KEY):
            raise APIError("Invalid API key", 401)

        # Validate conversation ID
        conversation_id = validate_conversation_id(
            request.headers.get("X-Conversation-Id")
        )

        json_data = request.get_json()

        # Validate message
        message = validate_message(json_data.get("message"))
        
        response = process_rag(message, conversation_id)

        return jsonify(response)
    except Exception as e:
        if isinstance(e, APIError):
            raise e
        else:
            logger.exception("Internal server error in /v1/chat")
            raise APIError(message="Internal server error", details=str(e), code=500)


@app.route("/v1/audio", methods=["POST"])
@limiter.limit(f"{Config.RATE_LIMIT_PER_HOUR} per hour")
async def process_audio():
    try:
        # Validate API key (timing-safe comparison)
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise APIError("X-API-Key header is required", 400)

        if not secrets.compare_digest(api_key, Config.API_KEY):
            raise APIError("Invalid API key", 401)

        # Validate conversation ID
        conversation_id = validate_conversation_id(
            request.headers.get("X-Conversation-Id")
        )

        if "audio" not in request.files:
            raise APIError("Audio file is required", 400)

        audio_file = request.files["audio"]
        if not audio_file.filename:
            raise APIError("No audio file selected", 400)

        audio_bytes = audio_file.read()
        
        # Validate audio file
        validate_audio_file(audio_file.filename, len(audio_bytes))

        # Track speech to text time
        stt_start = time()
        transcript = await speech_to_text_streaming(audio_bytes)
        stt_time = round(time() - stt_start, 2)

        if transcript is None:
            raise APIError("Failed to process audio", 500)

        # Analyze emotion
        emotion_start = time()
        try:
            emotion = await analyze_emotion(
                transcript, audio_bytes, audio_file.filename
            )
        except Exception as e:
            logger.error(f"Failed to analyze emotion: {str(e)}")
            emotion = "neutral"
        emotion_time = round(time() - emotion_start, 2)

        # Track RAG processing time
        logger.info(f"Detected emotion: {emotion}")

        rag_start = time()
        response = process_rag(transcript, conversation_id, emotion)
        answer = response["answer"]
        sources = response["sources"]
        rag_time = round(time() - rag_start, 2)

        # Track text to speech time
        tts_start = time()
        audio_bytes = await text_to_speech(answer)
        tts_time = round(time() - tts_start, 2)

        return jsonify(
            {
                "audio": audio_bytes.hex(),
                "transcript": transcript,
                "answer": answer,
                "sources": sources,
                "exec_time": {
                    "speech_to_text": stt_time,
                    "emotion_analysis": emotion_time,
                    "process_rag": rag_time,
                    "text_to_speech": tts_time,
                    "total": round(stt_time + emotion_time + rag_time + tts_time, 2),
                },
            }
        )
    except Exception as e:
        if isinstance(e, APIError):
            raise e
        else:
            logger.exception("Internal server error in /v1/audio")
            raise APIError(message="Internal server error", details=str(e), code=500)


# Wrap Flask app with ASGI to support async routes
asgi_app = WsgiToAsgi(app)


def main():
    """Main entry point for the application"""
    try:
        logger.info("Starting Flask application...")
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.FLASK_DEBUG,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise


if __name__ == "__main__":
    main()
