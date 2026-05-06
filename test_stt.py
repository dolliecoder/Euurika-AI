import httpx
import os
from dotenv import load_dotenv

# Load env from project directory
load_dotenv('/Users/luciferxt5/Documents/Coding/voice agent project/.env')

# Test STT endpoint with a simple audio file
audio_path = "/System/Library/Sounds/Hero.aiff"  # macOS built-in sound

try:
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    print(f"Sending audio file: {audio_path} ({len(audio_data)} bytes)")
    
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "http://localhost:8000/stt/transcribe",
            files={"audio": ("hero.aiff", audio_data, "audio/aiff")},
            data={"model": "ink-whisper"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
except Exception as e:
    print(f"Error: {e}")