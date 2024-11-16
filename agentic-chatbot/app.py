from time import time
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

from agents.rag import process_rag
from models import APIError

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
def chat():
    try:
        json_data = request.get_json()

        message = json_data.get("message")
        if not message:
            raise APIError("Message is required", 400)

        conversation_id = json_data.get("conversation_id")
        if not conversation_id:
            raise APIError("Conversation ID is required", 400)

        response = process_rag(message, conversation_id)

        return jsonify(response)
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
