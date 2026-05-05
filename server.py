import os
import base64
import asyncio
import uuid
from typing import List, Optional

import chromadb
from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from utils.parser import read_file
from utils.chunker import chunk_document
from utils.embedder import get_embedder
from utils.stt import get_stt
from utils.tts import get_tts
from utils.agent import get_agent
from utils.knowledge_base import get_knowledge_base

# Load environment variables
load_dotenv()

app = FastAPI(title="Eurika AI", version="1.0.0")

# Initialize ChromaDB (persistent storage)
chroma_client = chromadb.PersistentClient(path="./chroma_doc_db")

# Initialize embedder
embedder = get_embedder()
embedding_fn = embedder  # Use custom embedder instead of Chroma's default

# Active WebSocket sessions
active_sessions: dict[str, dict] = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",
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
    return {"status": "ok", "message": "Eurika AI Voice Agent API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "eurika-ai"}


@app.get("/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get document count for a session"""
    try:
        collection = chroma_client.get_collection(name=session_id)
        return {
            "session_id": session_id,
            "document_count": collection.count()
        }
    except Exception as e:
        return {"error": str(e), "document_count": 0}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its documents"""
    try:
        chroma_client.delete_collection(name=session_id)
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws/{session_id}")
async def websocket_handler(ws: WebSocket, session_id: str):
    """
    WebSocket handler for real-time voice interaction
    
    Message Protocol:
    Client -> Server:
        - {"type": "audio_chunk", "data": "<base64>"}
        - {"type": "speech_end"}
        - {"type": "barge_in"}
        - {"type": "session_init"}
    
    Server -> Client:
        - {"type": "transcript", "text": "..."}
        - {"type": "tool_call", "name": "...", "query": "..."}
        - {"type": "text", "content": "..."}
        - {"type": "audio_chunk", "data": "<base64>"}
        - {"type": "agent_done"}
        - {"type": "error", "message": "..."}
    """
    await ws.accept()
    
    # Initialize session state
    audio_buffer = bytearray()
    agent_task: Optional[asyncio.Task] = None
    conversation_history: list[dict] = []
    
    # Initialize components
    stt = get_stt()
    tts = get_tts()
    kb = get_knowledge_base()
    agent = get_agent(knowledge_base=kb, tts=tts)
    
    # Store session
    active_sessions[session_id] = {
        "websocket": ws,
        "started_at": asyncio.get_event_loop().time()
    }
    
    try:
        await ws.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to Eurika AI"
        })
        
        async for message in ws.iter_json():
            msg_type = message.get("type")
            
            if msg_type == "audio_chunk":
                # Accumulate audio while user speaks
                try:
                    audio_data = base64.b64decode(message.get("data", ""))
                    audio_buffer.extend(audio_data)
                except Exception as e:
                    print(f"Audio decode error: {e}")
            
            elif msg_type == "speech_end":
                # User stopped talking - transcribe and run agent
                if len(audio_buffer) > 0:
                    audio_bytes = bytes(audio_buffer)
                    audio_buffer.clear()
                    
                    try:
                        # Transcribe audio
                        transcript = await stt.transcribe(audio_bytes)
                        await ws.send_json({
                            "type": "transcript",
                            "text": transcript
                        })
                        
                        # Run agent as async task (allows barge-in)
                        if agent_task and not agent_task.done():
                            agent_task.cancel()
                        
                        agent_task = asyncio.create_task(
                            _run_agent(agent, transcript, session_id, ws, conversation_history)
                        )
                        
                    except Exception as e:
                        await ws.send_json({
                            "type": "error",
                            "message": f"Processing error: {str(e)}"
                        })
            
            elif msg_type == "barge_in":
                # User spoke while agent was talking - cancel immediately
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                    await ws.send_json({"type": "agent_interrupted"})
                audio_buffer.clear()
            
            elif msg_type == "session_init":
                # Client initializing session
                await ws.send_json({
                    "type": "session_ready",
                    "session_id": session_id
                })
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        await ws.send_json({
            "type": "error",
            "message": str(e)
        })
    
    finally:
        # Cleanup
        if session_id in active_sessions:
            del active_sessions[session_id]
        if agent_task and not agent_task.done():
            agent_task.cancel()


async def _run_agent(agent, transcript: str, session_id: str, ws: WebSocket, history: list[dict]):
    """Run the agent and stream responses to WebSocket"""
    try:
        async for event in agent.run_streaming(transcript, session_id, ws, history):
            event_type = event.get("type")
            
            if event_type == "text":
                # Text token - already streamed via TTS
                pass
            
            elif event_type == "tool_call":
                await ws.send_json({
                    "type": "tool_call",
                    "name": event.get("name"),
                    "query": event.get("arguments", {})
                })
            
            elif event_type == "tool_result":
                await ws.send_json({
                    "type": "tool_result",
                    "name": event.get("name"),
                    "result": event.get("result", "")
                })
            
            elif event_type == "done":
                await ws.send_json({"type": "agent_done"})
                break
    
    except asyncio.CancelledError:
        await ws.send_json({"type": "agent_interrupted"})
    except Exception as e:
        print(f"Agent error: {e}")
        await ws.send_json({
            "type": "error",
            "message": str(e)
        })