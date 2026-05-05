import os
import tempfile
from typing import Optional
from openai import AsyncOpenAI
import dotenv

dotenv.load_dotenv()

# We will initialize it lazily to avoid crashing on import if KEY is not set
_client: Optional[AsyncOpenAI] = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _client

async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribes audio bytes to text using OpenAI's Whisper model.
    """
    if not audio_bytes:
        return ""
        
    client = get_client()
    
    # Write bytes to a temporary file since Whisper API needs a file-like object with a name/extension
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = temp_audio.name
    
    try:
        with open(temp_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        return response.text.strip()
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
