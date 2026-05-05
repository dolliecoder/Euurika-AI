import { useCallback, useRef, useState } from 'react';

export function useAudioPlayer() {
  const audioQueue = useRef([]);
  const currentAudio = useRef(null);
  const isPlaying = useRef(false);
  const [isCurrentlyPlaying, setIsCurrentlyPlaying] = useState(false);

  const playNext = useCallback(() => {
    if (audioQueue.current.length === 0) {
      isPlaying.current = false;
      setIsCurrentlyPlaying(false);
      return;
    }

    const url = audioQueue.current.shift();
    const audio = new Audio(url);
    
    audio.onended = () => {
      URL.revokeObjectURL(url);
      playNext();
    };
    
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      playNext();
    };

    currentAudio.current = audio;
    isPlaying.current = true;
    setIsCurrentlyPlaying(true);
    audio.play().catch(e => {
      console.error('Audio playback error:', e);
      playNext();
    });
  }, []);

  const addChunk = useCallback((base64Audio) => {
    // Decode base64 to binary
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Create blob and URL
    const blob = new Blob([bytes], { type: 'audio/mpeg' });
    const url = URL.createObjectURL(blob);
    
    audioQueue.current.push(url);
    
    // Start playing if not already playing
    if (!isPlaying.current) {
      playNext();
    }
  }, [playNext]);

  const stopImmediately = useCallback(() => {
    // Stop current audio
    if (currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current.currentTime = 0;
      currentAudio.current = null;
    }
    
    // Clear queue
    audioQueue.current = [];
    isPlaying.current = false;
    setIsCurrentlyPlaying(false);
  }, []);

  const pause = useCallback(() => {
    if (currentAudio.current) {
      currentAudio.current.pause();
      isPlaying.current = false;
      setIsCurrentlyPlaying(false);
    }
  }, []);

  const resume = useCallback(() => {
    if (currentAudio.current && !isPlaying.current) {
      currentAudio.current.play();
      isPlaying.current = true;
      setIsCurrentlyPlaying(true);
    } else if (!currentAudio.current && audioQueue.current.length > 0) {
      playNext();
    }
  }, [playNext]);

  return {
    addChunk,
    stopImmediately,
    pause,
    resume,
    isCurrentlyPlaying,
    hasAudio: audioQueue.current.length > 0 || isPlaying.current
  };
}
