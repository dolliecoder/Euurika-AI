# Eurika AI - Voice Assistant

Eurika AI is a real-time voice-to-voice AI assistant that can answer questions based on uploaded documents. It uses Cartesia for low-latency Speech-to-Text (STT) and Text-to-Speech (TTS), and OpenCode Zen (GPT-5-nano) for reasoning and knowledge retrieval.

## Features
- **Real-Time Speech-to-Text**: High-performance STT streaming using Cartesia.
- **RAG (Retrieval-Augmented Generation)**: Upload PDFs, Markdown, or text files to generate a custom knowledge base.
- **Intelligent LLM Agent**: Uses OpenCode Zen to dynamically search the knowledge base and respond to user queries.
- **Real-Time TTS**: Synthesizes human-like voice responses with Cartesia Sonic 3.5.
- **Voice Barge-in / Interruption**: If the user interrupts the agent while it's speaking, the agent will instantly pause and listen to the new query.

## Architecture
- **Frontend**: React + Vite application capturing audio via the Web Audio API, performing client-side Voice Activity Detection (VAD), and communicating over WebSockets.
- **Backend**: FastAPI Python backend handling file parsing, ChromaDB embeddings, WebSocket proxying to Cartesia STT, and managing the LLM agent tool calls.

## Installation

### 1. Backend Setup
Navigate to the root directory and install the required Python dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory using the provided `.env.example` as a template:
```bash
cp .env.example .env
```
Ensure you add your actual API keys for Cartesia and OpenCode Zen.

### 3. Frontend Setup
Navigate to the `frontend` directory and install the Node dependencies:
```bash
cd frontend
npm install
```

## Running the Application

1. **Start the Backend Server**:
Open a terminal in the root directory:
```bash
source .venv/bin/activate
uvicorn server:app --reload
```
The backend will be available on `http://localhost:8000`.

2. **Start the Frontend Server**:
Open a new terminal in the `frontend` directory:
```bash
npm run dev
```
The frontend will be available on `http://localhost:5173`.

## Usage
1. Open the frontend in your browser.
2. Upload one or more documents (.pdf, .md, .txt) using the "Add Source" button. Wait for them to process.
3. Click "Start Voice" to begin recording. Speak into your microphone.
4. When you stop speaking, the agent will process your query, search your documents, and speak the answer back to you!
