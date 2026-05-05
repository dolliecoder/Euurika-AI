import os
import uuid
from typing import List

import chromadb
from chromadb.utils import embedding_functions
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from utils.parser import read_file
from utils.chunker import chunk_document

app = FastAPI()

# Initialize ChromaDB (in-memory)
chroma_client = chromadb.Client()
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

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