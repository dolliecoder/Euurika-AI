"""
STT Module - Whisper Transcription for Eurika AI
Uses OpenAI's Whisper API for speech-to-text
"""

import os
import tempfile
from typing import Optional

import openai


class SpeechToText:
    """Whisper-based speech recognition"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize STT with OpenAI client"""
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
    
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe audio bytes to text
        
        Args:
            audio_bytes: Raw audio data
            filename: Filename for the temporary audio file
            
        Returns:
            Transcribed text string
        """
        # Create temp file with audio data
        suffix = ".webm" if filename.endswith(".webm") else ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        
        try:
            with open(tmp_path, "rb") as audio_file:
                result = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="text"
                )
            
            transcript = result.strip()
            return transcript if transcript else ""
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def transcribe_with_timestamps(
        self, audio_bytes: bytes, filename: str = "audio.webm"
    ) -> list[dict]:
        """
        Transcribe with word-level timestamps
        
        Args:
            audio_bytes: Raw audio data
            filename: Filename for the temporary audio file
            
        Returns:
            List of word segments with timestamps
        """
        suffix = ".webm" if filename.endswith(".webm") else ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        
        try:
            with open(tmp_path, "rb") as audio_file:
                result = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            return [
                {
                    "word": segment["word"],
                    "start": segment["start"],
                    "end": segment["end"]
                }
                for segment in result.words
            ]
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def get_stt(api_key: Optional[str] = None) -> SpeechToText:
    """Factory function to get STT instance"""
    return SpeechToText(api_key=api_key)
