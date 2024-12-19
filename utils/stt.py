import asyncio
import io
import json
import os

import scipy.signal
import soundfile as sf
import websockets
from dotenv import load_dotenv

load_dotenv()

PROSA_STT_API_KEY = os.getenv("PROSA_STT_API_KEY")


async def send_audio(
    audio_data: bytes, ws: websockets.WebSocketClientProtocol, chunk_size: int = 16000
):
    try:
        print("Sending audio in chunks")
        # Create BytesIO object from the audio data
        audio_io = io.BytesIO(audio_data)

        while chunk := audio_io.read(chunk_size):
            await ws.send(chunk)
        await ws.send(b"")  # Signifies the end of audio stream
        print("Audio sent")
    except Exception as e:
        print(f"Error sending audio: {e}")


async def receive_message(ws: websockets.WebSocketClientProtocol):
    while True:
        try:
            data = json.loads(await ws.recv())
            message_type = data["type"]
            if message_type == "result":
                transcript = data["transcript"]
                return transcript
        except Exception as e:
            print(f"Error receiving message: {e}")
            break


async def speech_to_text_streaming(audio_data: bytes) -> str:
    url = "wss://asr-api.stg.prosa.ai/v2/speech/stt/streaming"

    headers = {
        "x-api-key": PROSA_STT_API_KEY,
    }

    try:
        async with websockets.connect(url, extra_headers=headers) as ws:
            config = {
                "label": "Streaming STT Test",
                "model": "asr-general-online",
                "include_partial": False,
            }

            await ws.send(json.dumps(config))

            _, transcript = await asyncio.gather(
                send_audio(audio_data, ws), receive_message(ws)
            )
            # await send_audio(audio_data, ws)
            # transcript = await receive_message(ws)
            return transcript
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
        return None
    except Exception as e:
        print(f"An error occurred during speech-to-text processing: {e}")
        return None


# def speech_to_text(audio_data: bytes) -> str:
#     url = "https://api.prosa.ai/v2/speech/stt"
#     base64_audio = base64.b64encode(audio_data).decode("utf-8")
#     payload = {
#         "config": {"model": "stt-general", "wait": True},
#         "request": {"data": base64_audio},
#     }

#     response = requests.post(
#         url,
#         headers={"x-api-key": PROSA_STT_API_KEY},
#         json=payload,
#     )

#     print("JSON:", response.json())
#     return response.json()["data"]["transcript"]
