import { useState, useEffect, useRef, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { useVAD } from '../hooks/useVAD';
import styles from './AgentScreen.module.css';

export function AgentScreen({ sessionId, filesProcessed, onEndSession }) {
  const [messages, setMessages] = useState([]);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [currentTranscript, setCurrentTranscript] = useState('');
  const messagesEndRef = useRef(null);
  const audioContextRef = useRef(null);

  // Initialize audio context for VAD
  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // WebSocket handlers
  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'transcript':
        setCurrentTranscript(data.text);
        break;
      case 'response_start':
        setIsAgentSpeaking(true);
        setCurrentTranscript('');
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          id: data.message_id
        }]);
        break;
      case 'response_content':
        setMessages(prev => prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, content: msg.content + data.content }
            : msg
        ));
        break;
      case 'audio_chunk':
        addChunk(data.data);
        break;
      case 'response_end':
        setIsAgentSpeaking(false);
        break;
      case 'error':
        setIsAgentSpeaking(false);
        console.error('Server error:', data.message);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }, []);

  const handleConnect = useCallback(() => {
    setConnectionStatus('connected');
  }, []);

  const handleDisconnect = useCallback(() => {
    setConnectionStatus('disconnected');
  }, []);

  const handleError = useCallback((error) => {
    console.error('WebSocket error:', error);
    setConnectionStatus('error');
  }, []);

  // VAD handlers
  const handleSpeechStart = useCallback(() => {
    if (isAgentSpeaking) {
      // User interrupted - send barge-in
      sendBargeIn();
    }
    setCurrentTranscript('Listening...');
  }, [isAgentSpeaking, sendBargeIn]);

  const handleSpeechEnd = useCallback(() => {
    setCurrentTranscript('');
    sendSpeechEnd();
  }, [sendSpeechEnd]);

  const handleFrameProcessed = useCallback((audioData) => {
    sendAudioChunk(audioData);
  }, [sendAudioChunk]);

  // Hooks
  const { isConnected, sendBargeIn, sendSpeechEnd, sendAudioChunk } = useWebSocket(sessionId, {
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  });

  const { addChunk, stopImmediately } = useAudioPlayer();
  
  const { isListening, isSpeaking, startListening, stopListening, toggleListening } = useVAD({
    onSpeechStart: handleSpeechStart,
    onSpeechEnd: handleSpeechEnd,
    onFrameProcessed: handleFrameProcessed,
    enabled: connectionStatus === 'connected'
  });

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopImmediately();
      stopListening();
    };
  }, [stopImmediately, stopListening]);

  const handleToggleListening = () => {
    if (!isListening && !connectionStatus === 'connected') return;
    toggleListening();
  };

  const getStatusText = () => {
    if (connectionStatus === 'connecting') return 'Connecting...';
    if (connectionStatus === 'disconnected') return 'Disconnected';
    if (connectionStatus === 'error') return 'Connection error';
    if (isAgentSpeaking) return 'Speaking...';
    if (isSpeaking) return 'Listening...';
    if (isListening) return 'Ready';
    return 'Paused';
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.sessionInfo}>
          <div className={styles.logo}>
            <EurikaLogo />
          </div>
          <div className={styles.sessionDetails}>
            <h1>Eurika AI</h1>
            <span className={styles.filesCount}>
              {filesProcessed} document{filesProcessed !== 1 ? 's' : ''} loaded
            </span>
          </div>
        </div>
        <div className={styles.headerActions}>
          <StatusBadge status={connectionStatus} text={getStatusText()} />
          <button className={styles.endBtn} onClick={onEndSession}>
            End Session
          </button>
        </div>
      </header>

      {/* Messages */}
      <main className={styles.messages}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <WaveIcon />
            </div>
            <h2>Ready to help</h2>
            <p>Click the microphone and ask me anything about your documents</p>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <div key={msg.id || index} className={styles.message}>
                {msg.role === 'user' ? (
                  <div className={styles.userMessage}>
                    <div className={styles.messageBubble}>
                      <UserIcon />
                      <span>{msg.content}</span>
                    </div>
                  </div>
                ) : (
                  <div className={styles.assistantMessage}>
                    <div className={styles.assistantAvatar}>
                      <EurikaLogo />
                    </div>
                    <div className={styles.messageBubble}>
                      <p>{msg.content}</p>
                      {msg.content === '' && (
                        <div className={styles.typingIndicator}>
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </>
        )}
        
        {/* Current transcript */}
        {currentTranscript && (
          <div className={styles.transcriptPreview}>
            <span>{currentTranscript}</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </main>

      {/* Controls */}
      <footer className={styles.controls}>
        <div className={styles.controlsMain}>
          <button
            className={`${styles.micButton} ${isListening ? styles.active : ''} ${isSpeaking ? styles.speaking : ''}`}
            onClick={handleToggleListening}
            disabled={connectionStatus !== 'connected'}
            aria-label={isListening ? 'Stop listening' : 'Start listening'}
          >
            <div className={styles.micPulse} />
            {isListening ? <MicActiveIcon /> : <MicIcon />}
          </button>
          
          <div className={styles.controlsHint}>
            {isListening ? (
              <span>Tap to stop</span>
            ) : (
              <span>Tap to speak</span>
            )}
          </div>
        </div>

        <div className={styles.controlsSecondary}>
          {isAgentSpeaking && (
            <button className={styles.bargeInBtn} onClick={sendBargeIn}>
              <InterruptIcon />
              Interrupt
            </button>
          )}
        </div>
      </footer>
    </div>
  );
}

function StatusBadge({ status, text }) {
  const getStatusColor = () => {
    switch (status) {
      case 'connected': return 'var(--success)';
      case 'disconnected':
      case 'error': return 'var(--error)';
      default: return 'var(--warning)';
    }
  };

  return (
    <div className={styles.statusBadge} style={{ '--status-color': getStatusColor() }}>
      <span className={styles.statusDot} />
      <span>{text}</span>
    </div>
  );
}

// SVG Icons
export function EurikaLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
      <defs>
        <linearGradient id="agentLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14" stroke="url(#agentLogoGrad)" strokeWidth="2" fill="none" />
      <path 
        d="M10 16 L16 10 L22 16 M16 10 L16 24" 
        stroke="url(#agentLogoGrad)" 
        strokeWidth="2.5" 
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function MicIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

export function MicActiveIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" stroke="currentColor" strokeWidth="2" fill="none" />
      <line x1="12" y1="19" x2="12" y2="23" stroke="currentColor" strokeWidth="2" />
      <line x1="8" y1="23" x2="16" y2="23" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export function UserIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

export function WaveIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 12h2 M6 6v12 M10 4v16 M14 8v8 M18 6v12 M22 12h2" />
    </svg>
  );
}

export function InterruptIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="9" x2="15" y2="15" />
      <line x1="15" y1="9" x2="9" y2="15" />
    </svg>
  );
}