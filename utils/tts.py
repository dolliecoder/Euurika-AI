"""
TTS Module - ElevenLabs Streaming for Eurika AI
Streams audio chunks as they're generated for low latency
"""

import os
import base64
from typing import AsyncGenerator, Optional, AsyncIterator

from elevenlabs.client import ElevenLabs


class TextToSpeech:
    """ElevenLabs streaming TTS with chunked audio output"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None
    ):
        """Initialize TTS with ElevenLabs client"""
        self.client = ElevenLabs(
            api_key=api_key or os.getenv("ELEVENLABS_API_KEY")
        )
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
        self.model_id = "eleven_turbo_v2"  # Lowest latency model
    
    async def stream_audio(self, text: str) -> AsyncGenerator[str, None]:
        """
        Stream audio chunks as base64-encoded MP3
        
        Args:
            text: Text to convert to speech
            
        Yields:
            Base64-encoded MP3 audio chunks
        """
        if not text.strip():
            return
        
        try:
            # Use the streaming API
            audio_stream = self.client.text_to_speech.convert_as_stream(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                # Try to get lowest latency
                latency="normal"  # Use "normal" or "fastest" based on availability
            )
            
            # Convert sync iterator to async
            for chunk in audio_stream:
                if chunk:
                    encoded = base64.b64encode(chunk).decode()
                    yield encoded
                    
        except Exception as e:
            # Log error but don't crash - just yield nothing
            print(f"TTS streaming error: {e}")
            return
    
    async def generate_audio(self, text: str) -> bytes:
        """
        Generate full audio response (non-streaming)
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Raw MP3 audio bytes
        """
        if not text.strip():
            return b""
        
        try:
            result = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id
            )
            return result
            
        except Exception as e:
            print(f"TTS generation error: {e}")
            return b""
    
    def get_available_voices(self) -> list[dict]:
        """Get list of available voices"""
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    "voice_id": v.voice_id,
                    "name": v.name,
                    "category": v.category
                }
                for v in voices.voices
            ]
        except Exception as e:
            print(f"Error fetching voices: {e}")
            return []


def get_tts(api_key: Optional[str] = None, voice_id: Optional[str] = None) -> TextToSpeech:
    """Factory function to get TTS instance"""
    return TextToSpeech(api_key=api_key, voice_id=voice_id)
