import os

import httpx
from werkzeug.datastructures import FileStorage


async def analyze_emotion(text: str, audio_file: FileStorage) -> str:
    files = {"file": (audio_file.filename, audio_file)}
    params = {"text": text}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            os.getenv("EMOTION_ANALYSIS_URL") + "/predict", files=files, params=params
        )

    return response.json()["prediction"]
