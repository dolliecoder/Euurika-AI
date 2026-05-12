import os
import uuid
import json
import asyncio
from typing import List

import chromadb
from chromadb.utils import embedding_functions
import httpx
import websockets
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils.parser import read_file
from utils.chunker import chunk_document
from utils.embedder import get_embedder

app = FastAPI()

# Initialize ChromaDB (in-memory/ephemeral storage only)
chroma_client = chromadb.EphemeralClient()
# Initialize custom embedder (Gemma-300M quantized)
embedder = get_embedder()
embedding_fn = embedder  # Use custom embedder instead of Chroma's default

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default dev server
        "http://localhost:5175",  # Vite default dev server
        "http://localhost:5176",  # Vite default dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "text/markdown",
    "text/x-markdown",
    "text/plain",
}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> dict:
    """
    Upload multiple files, chunk them, embed, and store in ChromaDB.
    Returns a session_id for WebSocket connection.
    """
    session_id = str(uuid.uuid4())
    
    for file in files:
        # Determine which MIME type/extension to use
        mime_type = file.content_type
        extension = file.filename.split(".")[-1].lower() if "." in file.filename else None
        
        # Fallback to extension if MIME type is generic
        if mime_type in ("application/octet-stream", None) and extension:
            mime_type = {
                "pdf": "application/pdf",
                "md": "text/markdown",
                "txt": "text/plain",
            }.get(extension)
        
        if not mime_type:
            return {"error": f"Unsupported file type: {extension or file.content_type}"}
        
        # Save file temporarily
        import os
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Read file content using MIME type
            text = await read_file(temp_path, mime_type)
            
            # Chunk the document
            chunks = chunk_document(text)
            
            # Create or get collection for this session
            collection = chroma_client.get_or_create_collection(
                name=session_id,
                embedding_function=embedding_fn
            )
            
            # Generate IDs for chunks
            chunk_ids = [f"{file.filename}_{i}" for i in range(len(chunks))]
            
            # Store in ChromaDB
            collection.add(
                documents=chunks,
                ids=chunk_ids
            )
            
        finally:
            # Clean up temp file
            os.remove(temp_path)
    
    return {"session_id": session_id, "message": f"Uploaded {len(files)} files successfully"}


from pydantic import BaseModel
from utils.agent import get_agent

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"Chat request received: session_id={request.session_id} message={request.message[:120]}")
    agent = get_agent()
    response = await agent.get_response(request.message, request.session_id)
    if response.get("error"):
        print(f"Chat response error: {response['error']}")
    return response

@app.get("/")
async def root():
    return {"status": "ok", "message": "FAQ Voice Agent API"}


@app.websocket("/stt/stream")
async def stt_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech-to-text using Cartesia streaming STT.
    Sends audio chunks and receives transcriptions in real-time.
    """
    await websocket.accept()
    
    api_key = os.getenv("CARTESIA_API_KEY")
    CARTESIA_WS_URL = (
        "wss://api.cartesia.ai/stt/websocket?"
        "model=ink-whisper&"
        "language=en&"
        "encoding=pcm_s16le&"
        "sample_rate=16000&"
        "min_volume=0.1&"
        "max_silence_duration_secs=1.0"
    )
    
    try:
        # Connect to Cartesia WebSocket with proper authentication headers
        async with websockets.connect(
            CARTESIA_WS_URL,
            additional_headers={
                "Authorization": f"Bearer {api_key}",
                "Cartesia-Version": "2025-04-16"
            }
        ) as cartesia_ws:
            
            async def receive_from_client():
                """Receive audio from client and forward to Cartesia"""
                try:
                    while True:
                        audio_chunk = await websocket.receive_bytes()
                        await cartesia_ws.send(audio_chunk)
                except Exception:
                    pass
            
            async def send_to_client():
                """Receive transcriptions from Cartesia and forward to client"""
                try:
                    while True:
                        result = await cartesia_ws.recv()
                        # Handle both string and binary messages
                        if isinstance(result, str):
                            try:
                                data = json.loads(result)
                                await websocket.send_json(data)
                            except json.JSONDecodeError:
                                # Not JSON, might be a text response
                                await websocket.send_json({"text": result})
                        elif isinstance(result, bytes):
                            # Binary audio data - ignore for now
                            pass
                except Exception:
                    pass
            
            # Run both tasks concurrently
            await asyncio.gather(receive_from_client(), send_to_client())
            
    except WebSocketDisconnect:
        # Normal disconnect
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
        await websocket.close()

@app.post("/stt/transcribe")
async def stt_transcribe(audio: UploadFile = File(...)):
    """
    Transcribe audio to text using Cartesia ink-whisper STT model.
    Accepts audio file upload and returns the transcription.
    """
    CARTESIA_STT_URL = "https://api.cartesia.ai/stt"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CARTESIA_API_KEY')}",
        "Cartesia-Version": "2025-04-16",
    }
    
    # Read audio file
    audio_data = await audio.read()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                CARTESIA_STT_URL,
                files={"file": (audio.filename or "audio.wav", audio_data, audio.content_type or "audio/wav")},
                data={"model": "ink-whisper"},
                headers=headers
            )
            
            if response.status_code != 200:
                return {"error": f"STT Error: HTTP {response.status_code}", "details": response.text}
            
            result = response.json()
            return {
                "text": result.get("text", ""),
                "language": result.get("language", "en"),
                "duration": result.get("duration", 0)
            }
            
    except Exception as e:
        return {"error": str(e)}


@app.post("/tts/stream")
async def tts_stream(text: str):
    """
    Stream TTS audio using Cartesia SSE endpoint.
    Returns Server-Sent Events with audio chunks (base64 encoded).
    """
    CARTESIA_URL = "https://api.cartesia.ai/tts/sse"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CARTESIA_API_KEY')}",
        "Content-Type": "application/json",
        "Cartesia-Version": "2025-04-16",
    }
    
    data = {
        "model_id": os.getenv("CARTESIA_MODEL_ID", "sonic-3.5"),
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": os.getenv("CARTESIA_VOICE_ID"),
        },
        "output_format": {
            "container": "raw",
            "encoding": "pcm_f32le",
            "sample_rate": 44100,
        },
    }
    
    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", CARTESIA_URL, json=data, headers=headers) as response:
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'error': f'HTTP {response.status_code}'})}\n\n"
                        return
                    
                    async for line in response.aiter_lines():
                        if line and line.startswith("data: "):
                            json_str = line[6:].strip()
                            if json_str == "[DONE]":
                                yield "data: {\"type\":\"done\"}\n\n"
                                break
                            
                            try:
                                event = json.loads(json_str)
                                # Cartesia SSE: data field contains base64 audio
                                if event.get("type") == "chunk" and event.get("data"):
                                    audio_b64 = event["data"]
                                    yield f"data: {json.dumps({'type': 'chunk', 'audio': audio_b64})}\n\n"
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )