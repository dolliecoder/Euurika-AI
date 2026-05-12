import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Voice Activity Detection using Web Audio API
 * Simple energy-based VAD for voice detection
 */
export class VoiceActivityDetector {
  constructor(options = {}) {
    this.threshold = options.threshold || 0.02;
    this.silenceDuration = options.silenceDuration || 1500; // ms
    this.sampleRate = options.sampleRate || 16000;
    this.lastVoiceTime = null;
    this.isSpeaking = false;
  }

  analyze(audioData) {
    // Calculate RMS energy
    let sum = 0;
    for (let i = 0; i < audioData.length; i++) {
      sum += audioData[i] * audioData[i];
    }
    const rms = Math.sqrt(sum / audioData.length);
    
    const now = Date.now();
    
    if (rms > this.threshold) {
      this.lastVoiceTime = now;
      if (!this.isSpeaking) {
        this.isSpeaking = true;
      }
    } else if (this.lastVoiceTime && now - this.lastVoiceTime > this.silenceDuration) {
      this.isSpeaking = false;
    }
    
    return this.isSpeaking;
  }
}

/**
 * Audio recorder that captures microphone input
 */
export class AudioRecorder {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 16000;
    this.recording = false;
    this.audioContext = null;
    this.stream = null;
    this.processor = null;
    this.onAudioData = options.onAudioData || (() => {});
  }

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: this.sampleRate,
        }
      });

      this.audioContext = new AudioContext({ sampleRate: this.sampleRate });
      const source = this.audioContext.createMediaStreamSource(this.stream);
      
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
      
      this.processor.onaudioprocess = (event) => {
        if (this.recording) {
          const inputData = event.inputBuffer.getChannelData(0);
          // Convert Float32 to Int16 PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          this.onAudioData(pcmData.buffer);
        }
      };

      source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      this.recording = true;
      
      return true;
    } catch (error) {
      console.error('Failed to start audio recording:', error);
      return false;
    }
  }

  async stop() {
    this.recording = false;
    
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
  }
}

export class TTSPlayer {
  constructor(sampleRate = 44100) {
    this.sampleRate = sampleRate;
    this.audioContext = null;
    this.nextTime = 0;
    this.isPlaying = false;
  }

  init() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: this.sampleRate });
    }
  }

  playChunk(base64Data) {
    this.init();
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
    
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    const float32Data = new Float32Array(bytes.buffer);
    const audioBuffer = this.audioContext.createBuffer(1, float32Data.length, this.sampleRate);
    audioBuffer.getChannelData(0).set(float32Data);
    
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);
    
    if (this.nextTime < this.audioContext.currentTime) {
      this.nextTime = this.audioContext.currentTime;
    }
    source.start(this.nextTime);
    this.nextTime += audioBuffer.duration;
    this.isPlaying = true;
  }

  stop() {
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.nextTime = 0;
    this.isPlaying = false;
  }
}

/**
 * Custom hook for voice agent with WebSocket and VAD
 */
export function useVoiceAgent(sessionId) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [agentTranscript, setAgentTranscript] = useState('');

  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const vadRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const playerRef = useRef(new TTSPlayer());
  const abortControllerRef = useRef(null);
  const isAgentSpeakingRef = useRef(false);
  const transcriptRef = useRef(''); // keep track of latest transcript for VAD trigger

  useEffect(() => {
    transcriptRef.current = transcript;
  }, [transcript]);

  // Define handleCallAgent using a ref to avoid stale closures in WS callback
  const handleCallAgentRef = useRef(null);
  
  handleCallAgentRef.current = async (text) => {
    if (!text || !text.trim() || !sessionId) return;
    
    // Stop any ongoing TTS
    playerRef.current.stop();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    setIsProcessing(true);
    isAgentSpeakingRef.current = true;
    abortControllerRef.current = new AbortController();
    
    try {
      // 1. Get agent response
      const chatRes = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId }),
        signal: abortControllerRef.current.signal
      });
      
      const chatData = await chatRes.json();
      if (!chatRes.ok) {
        console.error('Chat API returned non-ok response:', chatData);
        throw new Error(chatData.error || `Failed to get agent response (${chatRes.status})`);
      }
      
      if (chatData.error) {
        console.error('Agent response error:', chatData.error);
        throw new Error(chatData.error);
      }
      
      const agentText = chatData.text;
      
      // Reveal text line-by-line (sentence-by-sentence), replacing previous line
      const lines = agentText.match(/[^.!?]+[.!?]*/g) || [agentText];
      let currentLineIdx = 0;
      setAgentTranscript('');
      setTranscript(''); // Clear user transcript since we responded
      transcriptRef.current = '';
      
      const revealInterval = setInterval(() => {
        if (currentLineIdx < lines.length) {
          const line = lines[currentLineIdx].trim();
          if (line) {
            setAgentTranscript(line); // ONLY show the current line
          }
          currentLineIdx++;
        } else {
          // Keep the last line visible, or clear it if preferred. Let's clear it after a delay if we want, or just leave the last line.
          clearInterval(revealInterval);
        }
      }, 2000); // Reveal one line every 2 seconds to match reading speed

      // Clean up interval on abort (barge-in)
      abortControllerRef.current.signal.addEventListener('abort', () => {
        clearInterval(revealInterval);
      });
      
      // 2. Stream TTS
      const ttsRes = await fetch(`http://localhost:8000/tts/stream?text=${encodeURIComponent(agentText)}`, {
        method: 'POST',
        signal: abortControllerRef.current.signal
      });
      
      if (!ttsRes.ok) throw new Error('Failed to get TTS stream');
      
      const reader = ttsRes.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const linesStr = buffer.split('\n\n');
        buffer = linesStr.pop(); // Keep incomplete line
        
        for (const line of linesStr) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]' || dataStr.includes('{"type":"done"}')) {
              break;
            }
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'chunk' && data.audio) {
                playerRef.current.playChunk(data.audio);
              }
            } catch (e) {
              console.error('TTS SSE parse error:', e);
            }
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        console.error('Agent error:', e);
        setError(e.message || 'Failed to get response');
      }
    } finally {
      setIsProcessing(false);
      isAgentSpeakingRef.current = false;
    }
  };

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`ws://localhost:8000/stt/stream`);

    ws.onopen = () => {
      console.log('STT WebSocket connected');
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.error) {
          setError(data.error);
          return;
        }

        // Handle transcript messages
        if (data.transcript || data.text) {
          const newText = data.transcript || data.text;
          setTranscript(prev => {
             if (data.is_final) return newText;
             return newText; 
          });
        }
        
        // Handle final transcript
        if (data.is_final && data.text) {
          setTranscript(data.text);
          // Trigger the agent call
          if (handleCallAgentRef.current && !isAgentSpeakingRef.current) {
            handleCallAgentRef.current(data.text);
          }
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (e) => {
      console.error('WebSocket error:', e);
      setError('Connection error');
    };

    ws.onclose = () => {
      console.log('STT WebSocket disconnected');
      if (isListening) {
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      }
    };

    wsRef.current = ws;
  }, [isListening]);

  const startListening = useCallback(async () => {
    try {
      setError(null);
      setTranscript('');
      setAgentTranscript('');
      transcriptRef.current = '';
      setIsProcessing(true);

      // Initialize VAD
      vadRef.current = new VoiceActivityDetector({
        threshold: 0.02,
        silenceDuration: 2000,
      });

      // Initialize recorder
      const recorder = new AudioRecorder({
        sampleRate: 16000,
        onAudioData: (buffer) => {
          const int16Data = new Int16Array(buffer);
          const float32Data = new Float32Array(int16Data.length);
          for (let i = 0; i < int16Data.length; i++) {
            float32Data[i] = int16Data[i] / 32768.0;
          }

          // Check previous speaking state
          const wasSpeaking = vadRef.current?.isSpeaking || false;
          // Analyze with VAD
          const isSpeakingNow = vadRef.current?.analyze(float32Data) || false;
          
          // Interrupt agent if user starts speaking
          if (!wasSpeaking && isSpeakingNow) {
            setAgentTranscript(''); // clear agent text on interrupt
            if (isAgentSpeakingRef.current) {
              if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
              }
              playerRef.current.stop();
              isAgentSpeakingRef.current = false;
            }
          }

          // Trigger agent if user stopped speaking (VAD silence)
          if (wasSpeaking && !isSpeakingNow && transcriptRef.current.trim() && !isAgentSpeakingRef.current) {
            if (handleCallAgentRef.current) {
              handleCallAgentRef.current(transcriptRef.current);
            }
          }
          
          let sum = 0;
          for (let i = 0; i < float32Data.length; i++) {
            sum += Math.abs(float32Data[i]);
          }
          setAudioLevel(sum / float32Data.length);

          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(buffer);
          }
        },
      });

      const started = await recorder.start();
      if (!started) {
        throw new Error('Failed to access microphone');
      }

      recorderRef.current = recorder;
      
      connectWebSocket();

      setIsListening(true);
    } catch (err) {
      console.error('Failed to start listening:', err);
      setError(err.message || 'Failed to start microphone');
      setIsListening(false);
    }
  }, [connectWebSocket]);

  const stopListening = useCallback(() => {
    if (recorderRef.current) {
      recorderRef.current.stop();
      recorderRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    playerRef.current.stop();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setIsListening(false);
    setAudioLevel(0);
  }, []);

  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  return {
    isListening,
    transcript,
    agentTranscript,
    isProcessing,
    error,
    audioLevel,
    startListening,
    stopListening,
  };
}