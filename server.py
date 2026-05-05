import os
import uuid
import base64
import asyncio
from typing import List

import chromadb
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from utils.parser import read_file
from utils.chunker import chunk_document
from utils.embedder import get_embedder
from utils.stt import transcribe_audio
from utils.agent import run_agent, SYSTEM_PROMPT
from utils.tts import stream_tts_chunk

app = FastAPI()

# Initialize ChromaDB (in-memory storage)
chroma_client = chromadb.EphemeralClient()
# Initialize custom embedder
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

@app.websocket("/ws/{session_id}")
async def websocket_handler(ws: WebSocket, session_id: str):
    await ws.accept()
    
    audio_buffer = bytearray()
    agent_task = None
    history = []
    
    try:
        while True:
            message = await ws.receive_json()
            
            if message["type"] == "audio_chunk":
                # accumulate audio while user speaks
                data = message.get("data", "")
                if data:
                    audio_buffer.extend(base64.b64decode(data))
                    
            elif message["type"] == "speech_end":
                # user stopped talking → transcribe + run agent
                if len(audio_buffer) > 0:
                    audio_bytes = bytes(audio_buffer)
                    audio_buffer.clear()
                    
                    try:
                        transcript = await transcribe_audio(audio_bytes)
                        if transcript:
                            await ws.send_json({"type": "transcript", "text": transcript})
                            
                            # run agent as async task so barge-in can cancel it
                            agent_task = asyncio.create_task(
                                run_agent(transcript, session_id, chroma_client, history, ws)
                            )
                    except Exception as e:
                        print(f"Error processing audio: {e}")
                        await ws.send_json({"type": "error", "message": "Failed to process audio."})
                        
            elif message["type"] == "barge_in":
                # user spoke while agent was talking → cancel immediately
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                audio_buffer.clear()
                await ws.send_json({"type": "agent_interrupted"})
                
            elif message["type"] == "session_init":
                pass
                
    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
