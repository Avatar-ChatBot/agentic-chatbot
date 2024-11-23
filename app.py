from time import time
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

from agents.rag import process_rag
from audio import text_to_speech
from audio.stt import speech_to_text
from models import APIError

import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Conversation-Id"],
)


@app.errorhandler(APIError)
def handle_api_error(error: APIError):
    timestamp = int(time())
    logger.error(f"API Error: {error.message}")

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


@app.route("/v1/chat", methods=["POST"])
def process_chat():
    try:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise APIError("X-API-Key header is required", 400)

        if api_key != os.getenv("API_KEY"):
            raise APIError("Invalid API key", 401)
        
        conversation_id = request.headers.get("X-Conversation-Id")
        if not conversation_id:
            raise APIError("X-Conversation-Id header is required", 400)
        
        json_data = request.get_json()
        
        message = json_data.get("message")
        if not message:
            raise APIError("Message is required", 400)
        response = process_rag(message, conversation_id)

        return jsonify(response)
    except Exception as e:
        if isinstance(e, APIError):
            raise e
        else:
            raise APIError(message="Internal server error", details=str(e), code=500)


@app.route("/v1/audio", methods=["POST"])
async def process_audio():
    try:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise APIError("X-API-Key header is required", 400)

        if api_key != os.getenv("API_KEY"):
            raise APIError("Invalid API key", 401)

        conversation_id = request.headers.get("X-Conversation-Id")
        if not conversation_id:
            raise APIError("X-Conversation-Id header is required", 400)

        if "audio" not in request.files:
            raise APIError("Audio file is required", 400)

        audio_file = request.files["audio"]
        if not audio_file.filename:
            raise APIError("No audio file selected", 400)

        audio_bytes = audio_file.read()

        # Track speech to text time
        stt_start = time()
        transcript = await speech_to_text(audio_bytes)
        stt_time = round(time() - stt_start, 2)

        if transcript is None:
            raise APIError("Failed to process audio", 500)

        # Track RAG processing time
        rag_start = time()
        response = process_rag(transcript, conversation_id)
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
                    "process_rag": rag_time,
                    "text_to_speech": tts_time,
                },
            }
        )
    except Exception as e:
        if isinstance(e, APIError):
            raise e
        else:
            raise APIError(message="Internal server error", details=str(e), code=500)


def main():
    """Main entry point for the application"""
    try:
        logger.info("Starting Flask application...")
        app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise


if __name__ == "__main__":
    main()
