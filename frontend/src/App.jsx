import React, { useState, useRef, useCallback } from 'react';
import './App.css';
import { useWebSocket } from './hooks/useWebSocket';
import { useVAD } from './hooks/useVAD';
import { useAudioPlayer } from './hooks/useAudioPlayer';

const Icons = {
  Mic: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" x2="12" y1="19" y2="22" />
    </svg>
  ),
  Upload: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" x2="12" y1="3" y2="15" />
    </svg>
  ),
  Logo: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  )
};

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [toolStatus, setToolStatus] = useState(null);
  const [agentState, setAgentState] = useState('idle'); // idle, listening, thinking, speaking
  const fileInputRef = useRef(null);

  // Audio queue handling
  const { addChunk, stopImmediately } = useAudioPlayer();

  // WS Setup
  const wsUrl = sessionId ? `ws://localhost:8001/ws/${sessionId}` : null;
  const { sendMessage, isConnected } = useWebSocket(wsUrl, useCallback((msg) => {
    if (msg.type === "transcript") {
      setTranscript(`You: ${msg.text}`);
      setAgentState('thinking');
    }
    if (msg.type === "agent_text") {
      // Just showing typing indicator or the text
    }
    if (msg.type === "tool_call") {
      setToolStatus(`Searching Knowledge Base...`);
    }
    if (msg.type === "audio_chunk") {
      setAgentState('speaking');
      addChunk(msg.data);
    }
    if (msg.type === "agent_done") {
      setToolStatus(null);
      // It stays in speaking state until audio queue unloads, but simplified here
    }
    if (msg.type === "agent_interrupted") {
      setAgentState('listening');
    }
  }, [addChunk]));

  // VAD setup
  const vad = useVAD({
    onSpeechStart: () => {
      if (agentState === 'speaking' || agentState === 'thinking') {
        stopImmediately();
        sendMessage({ type: "barge_in" });
      }
      setAgentState('listening');
    },
    onAudioChunk: (b64Audio) => {
      sendMessage({ type: "audio_chunk", data: b64Audio });
    },
    onSpeechEnd: () => {
      setAgentState('idle');
      sendMessage({ type: "speech_end" });
    }
  });

  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files?.length) return;

    setIsUploading(true);
    const formData = new FormData();
    for (let f of files) {
      formData.append("files", f);
    }

    try {
      const res = await fetch("http://localhost:8001/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.session_id) {
        setSessionId(data.session_id);
        vad.start(); // Start listening once connected
      }
    } catch (e) {
      console.error("Upload failed", e);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Upload Overlay */}
      {!sessionId && (
        <div className="upload-overlay">
          <div className="upload-box">
            <h2>Welcome to Eurika AI</h2>
            <p>Upload a document (PDF, Markdown, TXT) to initialize the knowledge base for this session.</p>
            <input 
              type="file" 
              multiple 
              className="file-input" 
              ref={fileInputRef} 
              onChange={handleUpload}
            />
            <button 
              className="upload-btn" 
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              <Icons.Upload />
              {isUploading ? "Initializing..." : "Upload Document"}
            </button>
          </div>
        </div>
      )}

      {/* Main Interface */}
      <header className="app-header">
        <div className="app-logo"><Icons.Logo /></div>
        <h1>Eurika AI</h1>
      </header>

      <main className="main-content">
        <div className={`status-badge ${isConnected ? 'active' : ''}`}>
          {isConnected ? 'Session Active' : 'Waiting for connection...'}
        </div>

        <div className="orb-container">
          <div className={`orb ${agentState}`} />
          {agentState === 'listening' && (
            <div style={{position: 'absolute', color: 'white'}}><Icons.Mic /></div>
          )}
        </div>

        <div className="transcript-layer">
          {toolStatus && <div className="tool-status">{toolStatus}</div>}
          <div className="transcript-text">
            {agentState === 'listening' ? "Listening..." : transcript}
          </div>
        </div>
      </main>
    </div>
  );
}
