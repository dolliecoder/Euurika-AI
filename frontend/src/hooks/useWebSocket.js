import { useCallback, useEffect, useRef, useState } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';
const RECONNECT_DELAY = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(sessionId, { onMessage, onConnect, onDisconnect, onError }) {
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    try {
      const ws = new WebSocket(`${WS_URL}/ws/${sessionId}`);
      
      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
        onConnect?.();
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
      
      ws.onclose = () => {
        setIsConnected(false);
        onDisconnect?.();
        
        // Attempt reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, RECONNECT_DELAY);
        }
      };
      
      ws.onerror = (error) => {
        setConnectionError('Connection error');
        onError?.(error);
      };
      
      wsRef.current = ws;
    } catch (e) {
      setConnectionError(e.message);
      onError?.(e);
    }
  }, [sessionId, onMessage, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const sendAudioChunk = useCallback((audioData) => {
    return sendMessage({
      type: 'audio_chunk',
      data: btoa(String.fromCharCode(...new Uint8Array(audioData)))
    });
  }, [sendMessage]);

  const sendSpeechEnd = useCallback(() => {
    return sendMessage({ type: 'speech_end' });
  }, [sendMessage]);

  const sendBargeIn = useCallback(() => {
    return sendMessage({ type: 'barge_in' });
  }, [sendMessage]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    connectionError,
    sendMessage,
    sendAudioChunk,
    sendSpeechEnd,
    sendBargeIn,
    connect,
    disconnect
  };
}
