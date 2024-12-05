import io
import os

import httpx
from pydub import AudioSegment


async def analyze_emotion(text: str, audio_bytes: bytes, audio_name: str) -> str:
    try:

        stream = io.BytesIO(audio_bytes)
        audio = AudioSegment.from_file(stream)
        compressed_audio = io.BytesIO()
        audio.export(compressed_audio, format="flac", bitrate="64k")
        compressed_audio.seek(0)  #
        files = {"file": (audio_name, compressed_audio)}
        params = {"text": text}

        async with httpx.AsyncClient(timeout = httpx.Timeout(30)) as client:
            response = await client.post(
                os.getenv("EMOTION_ANALYSIS_URL") + "/predict", files=files, params=params
            )

            return response.json()["prediction"]
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Failed to analyze emotion: {str(e)}")
        print(f"Full error details:\n{error_details}")
        raise e
