import React, { useState, useRef } from 'react';
import './App.css';

// SVG Icons as components
const Icons = {
  Logo: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  Plus: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  File: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  Sparkle: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
      <path d="M5 19l.5 1.5L7 21l-1.5.5L5 23l-.5-1.5L3 21l1.5-.5L5 19z" />
      <path d="M19 13l.5 1.5L21 15l-1.5.5L19 17l-.5-1.5L17 15l1.5-.5L19 13z" />
    </svg>
  ),
  VoiceWave: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="14" rx="3" />
      <path d="M8 19h1" />
      <path d="M15 19h1" />
      <path d="M12 12v4" />
      <path d="M9 9.5c.5 1 1.5 1.5 3 1.5s2.5-.5 3-1.5" />
    </svg>
  ),
  Upload: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  X: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  Mic: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  ),
};

// Get file extension for icon color
const getFileExtension = (filename) => {
  const ext = filename.split('.').pop().toLowerCase();
  return ext;
};

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

function App() {
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const fileInputRef = useRef(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    // Validate file types
    const allowedTypes = ['.pdf', '.md', '.txt'];
    const invalidFiles = files.filter(
      (file) => !allowedTypes.some((type) => file.name.toLowerCase().endsWith(type))
    );

    if (invalidFiles.length > 0) {
      showToast(`Unsupported files: ${invalidFiles.map((f) => f.name).join(', ')}`, 'error');
      return;
    }

    setIsLoading(true);

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    try {
      const response = await fetch('http://localhost:8001/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();

      // Add uploaded files to sources list
      const newSources = files.map((file) => ({
        id: `${Date.now()}-${file.name}`,
        name: file.name,
        size: file.size,
        type: getFileExtension(file.name),
        sessionId: data.session_id,
      }));

      setSources((prev) => [...prev, ...newSources]);
      showToast(`${files.length} file${files.length > 1 ? 's' : ''} uploaded successfully!`, 'success');
    } catch (error) {
      console.error('Upload error:', error);
      showToast('Failed to upload files. Please try again.', 'error');
    } finally {
      setIsLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleAddSourceClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="app-container">
      {/* Loading Overlay */}
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <p className="loading-text">Processing documents...</p>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          <span className="toast-icon">
            {toast.type === 'success' ? <Icons.Check /> : <Icons.X />}
          </span>
          {toast.message}
        </div>
      )}

      {/* Left Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Icons.Logo />
          </div>
          <div className="sidebar-brand">
            <span className="sidebar-brand-name">Eurika</span>
            <span className="sidebar-brand-title">AI</span>
          </div>
        </div>

        <button className="add-source-btn" onClick={handleAddSourceClick}>
          <Icons.Plus />
          Add Source
        </button>

        <div className="sources-section">
          <div className="sources-header">Sources</div>
          <div className="sources-list">
            {sources.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">
                  <Icons.File />
                </div>
                <p className="empty-state-text">No sources added yet</p>
              </div>
            ) : (
              sources.map((source) => (
                <div key={source.id} className="source-item">
                  <div className="source-icon">
                    <Icons.File />
                  </div>
                  <div className="source-info">
                    <div className="source-name">{source.name}</div>
                    <div className="source-meta">
                      {source.type.toUpperCase()} • {formatFileSize(source.size)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="connection-status">
            <span className={`status-indicator ${sources.length > 0 ? 'connected' : ''}`} />
            <span className="connection-text">
              {sources.length > 0 ? 'Ready' : 'Waiting for sources'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="main-panel">
        <div className="main-content">
          <h1 className="welcome-title">Welcome to Eurika AI</h1>
          <p className="welcome-subtitle">
            Your intelligent voice assistant powered by advanced AI. Add sources to get started.
          </p>

          <div className="orb-container">
            <div className="orb">
              <div className="orb-inner">
                {sources.length > 0 ? <Icons.VoiceWave /> : <Icons.Sparkle />}
              </div>
            </div>
          </div>

          <div className={`status-badge ${sources.length > 0 ? 'active' : ''}`}>
            <span className="dot" />
            {sources.length > 0 ? 'Ready to assist' : 'Awaiting input'}
          </div>

          {sources.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state-text">
                Upload documents (PDF, MD, TXT) to enable voice interactions
              </p>
              <div className="upload-action">
                <button className="btn-primary" onClick={handleAddSourceClick}>
                  <Icons.Upload />
                  Upload Documents
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p className="empty-state-text">
                {sources.length} source{sources.length > 1 ? 's' : ''} loaded • Voice feature coming soon
              </p>
            </div>
          )}
        </div>
      </main>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        className="file-input"
        accept=".pdf,.md,.txt"
        multiple
        onChange={handleFileUpload}
      />
    </div>
  );
}

export default App;