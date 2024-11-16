import asyncio
import json
import os
import requests
import websockets
from dotenv import load_dotenv

load_dotenv()

PROSA_TTS_API_KEY = os.getenv("PROSA_TTS_API_KEY")


async def text_to_speech(
    text: str,
    label: str = "test streaming",
    model_name: str = "tts-ghifari-professional",
):
    url = "wss://tts-api.stg.prosa.ai/v2/speech/tts/streaming"
    fmt = "wav"
    sample_rate = 8000

    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"token": PROSA_TTS_API_KEY}))

        config = {
            "label": label,
            "model": model_name,
            "audio_format": fmt,
            "sample_rate": sample_rate,
        }

        await ws.send(json.dumps(config))

        data = json.loads(await ws.recv())

        print("data: ", data)

        try:
            await ws.send(json.dumps({"text": text}))
            synthesized_audio = await ws.recv()

            assert isinstance(synthesized_audio, bytes), "No audio received"

            return synthesized_audio
        except websockets.exceptions.ConnectionClosedOK:
            print("WebSocket connection closed normally")
        except Exception as e:
            print(f"An error occurred: {e}")
            raise e


async def text_to_speech_polling(
    text: str,
    label: str = "test streaming",
    model_name: str = "tts-ghifari-professional",
):
    base_url = "https://api.prosa.ai/v2/speech/tts"
    headers = {"x-api-key": PROSA_TTS_API_KEY, "Content-Type": "application/json"}

    try:
        print(f"Submitting TTS request for text: {text}")

        request_body = {
            "config": {
                "model": model_name,
                "wait": False,
                "pitch": 0,
                "tempo": 1,
                "audio_format": "wav",
                "sample_rate": 8000,
            },
            "request": {"label": label, "text": text},
        }

        print("Request body:", json.dumps(request_body, indent=2))
        print("Headers:", headers)

        response = requests.post(base_url, headers=headers, json=request_body)
        print(f"Initial response status: {response.status_code}")
        print(f"Initial response content: {response.text}")

        response.raise_for_status()

        job_data = response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            print(f"No job_id in response: {job_data}")
            raise Exception("No job_id received from server")

        print(f"Job submitted successfully. Job ID: {job_id}")

        max_attempts = 30
        polling_interval = 1

        for attempt in range(max_attempts):
            print(f"Polling attempt {attempt + 1}/{max_attempts}")

            status_response = requests.get(f"{base_url}/{job_id}", headers=headers)
            print(f"Status response: {status_response.status_code}")
            print(f"Status content: {status_response.text}")

            status_response.raise_for_status()
            job_status = status_response.json()

            if job_status["status"] == "complete":
                audio_url = job_status["result"]["path"]
                print(f"Audio URL: {audio_url}")

                audio_response = requests.get(audio_url)
                print(f"Audio response status: {audio_response.status_code}")

                if audio_response.status_code != 200:
                    print(f"Audio download failed: {audio_response.text}")
                    raise Exception("Failed to download audio file")

                return audio_response.content

            elif job_status["status"] == "failed":
                error_msg = job_status.get("result", {}).get("error", "Unknown error")
                print(f"Job failed: {error_msg}")
                raise Exception(f"TTS job failed: {error_msg}")

            print(f"Job status: {job_status['status']}")
            await asyncio.sleep(polling_interval)

        raise Exception("Polling timeout: Job did not complete in time")

    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        print(f"Response content: {getattr(e.response, 'text', 'No response content')}")
        raise Exception(f"TTS request failed: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        raise Exception("Failed to parse server response")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise
