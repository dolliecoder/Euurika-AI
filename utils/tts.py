"""
Cartesia Sonic 3 TTS Utility
"""
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()


class CartesiaTTS:
    """Cartesia Sonic 3.5 text-to-speech client."""
    
    BASE_URL = "https://api.cartesia.ai"
    
    def __init__(self, api_key: str = None, voice_id: str = None):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        self.voice_id = voice_id or os.getenv("CARTESIA_VOICE_ID")
        self.model_id = os.getenv("CARTESIA_MODEL_ID", "sonic-3.5")
        
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech using Cartesia REST API.
        Returns audio bytes (MP3 format).
        """
        url = f"{self.BASE_URL}/tts/bytes"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Cartesia-Version": "2025-04-16",
        }
        
        data = {
            "model_id": self.model_id,
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": self.voice_id,
            },
            "output_format": {
                "container": "mp3",
                "sample_rate": 44100,
                "bit_rate": 128000,
            },
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Cartesia TTS error: {response.status_code} - {response.text}")
        
        return response.content
    
    def synthesize_base64(self, text: str) -> str:
        """Synthesize and return as base64 encoded string."""
        audio_bytes = self.synthesize(text)
        return base64.b64encode(audio_bytes).decode("utf-8")


# Singleton instance
_tts_client = None

def get_tts() -> CartesiaTTS:
    """Get the TTS client singleton."""
    global _tts_client
    if _tts_client is None:
        _tts_client = CartesiaTTS()
    return _tts_client
