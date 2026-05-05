import os
import uuid
from typing import list

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

SUPPORTED_EXTENSIONS = {"pdf", "md", "txt"}


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)) -> dict:
    """
    Upload multiple files, chunk them, embed, and store in ChromaDB.
    Returns a session_id for WebSocket connection.
    """
    session_id = str(uuid.uuid4())
    
    for file in files:
        # Validate file extension
        extension = file.filename.split(".")[-1].lower()
        if extension not in SUPPORTED_EXTENSIONS:
            return {"error": f"Unsupported file type: {extension}"}
        
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Read file content
            text = read_file(temp_path)
            
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