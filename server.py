import os
import uuid
import json
from typing import List

import chromadb
from chromadb.utils import embedding_functions
import httpx
from fastapi import FastAPI, UploadFile, File
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
        temp_path = f"/tmp/{file.filename}"
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


@app.get("/")
async def root():
    return {"status": "ok", "message": "FAQ Voice Agent API"}


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