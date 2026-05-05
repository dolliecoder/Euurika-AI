import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url, onMessage) {
  const ws = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!url) return;

    console.log("Connecting to WS:", url);
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log("WS Connected");
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onMessage(msg);
      } catch (e) {
        console.error("Failed to parse WS msg", event.data);
      }
    };

    ws.current.onclose = () => {
      console.log("WS Disconnected");
      setIsConnected(false);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url, onMessage]);

  const sendMessage = useCallback((msg) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg));
    }
  }, []);

  return { sendMessage, isConnected };
}