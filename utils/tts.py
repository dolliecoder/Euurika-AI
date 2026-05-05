import os
import base64
from typing import AsyncGenerator
from fastapi import WebSocket
from elevenlabs.client import ElevenLabs
import dotenv

dotenv.load_dotenv()

# We initialize it lazily
_client = None

def get_tts_client():
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY", ""))
    return _client

async def stream_tts_chunk(text: str, ws: WebSocket, voice_id: str = None):
    """
    Converts a chunk of text to audio using ElevenLabs' streaming turbo model
    and sends base64 encoded audio chunks over the websocket.
    """
    if not text or not text.strip():
        return
        
    client = get_tts_client()
    voice = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel default
    
    try:
        audio_stream = client.text_to_speech.convert_as_stream(
            voice_id=voice,
            text=text,
            model_id="eleven_turbo_v2" # fastest latency model
        )
        
        for chunk in audio_stream:
            if chunk:
                encoded = base64.b64encode(chunk).decode("utf-8")
                await ws.send_json({"type": "audio_chunk", "data": encoded})
                
    except Exception as e:
        print(f"TTS Error: {e}")
        await ws.send_json({"type": "error", "message": "Failed to generate audio."})
