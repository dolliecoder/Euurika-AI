import { useRef, useCallback } from 'react';

export function useAudioPlayer() {
  const audioQueue = useRef([]);
  const isPlaying = useRef(false);
  const currentSource = useRef(null);

  const playNext = useCallback(() => {
    if (audioQueue.current.length === 0) {
      isPlaying.current = false;
      return;
    }

    isPlaying.current = true;
    const url = audioQueue.current.shift();
    const audio = new Audio(url);
    currentSource.current = audio;

    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentSource.current = null;
      playNext();
    };

    audio.play().catch(e => console.error("Audio playback error:", e));
  }, []);

  const addChunk = useCallback((base64chunk) => {
    try {
      const binary = atob(base64chunk);
      const bytes = new Uint8Array(binary.length).map((_, i) => binary.charCodeAt(i));
      const blob = new Blob([bytes], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      audioQueue.current.push(url);
      
      if (!isPlaying.current) {
        playNext();
      }
    } catch (e) {
      console.error("Error adding chunk:", e);
    }
  }, [playNext]);

  const stopImmediately = useCallback(() => {
    if (currentSource.current) {
      currentSource.current.pause();
      currentSource.current = null;
    }
    audioQueue.current.forEach(url => URL.revokeObjectURL(url));
    audioQueue.current = [];
    isPlaying.current = false;
  }, []);

  return { addChunk, stopImmediately };
}