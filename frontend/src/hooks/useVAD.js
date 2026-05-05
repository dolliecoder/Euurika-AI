import { useMicVAD } from "@ricky0123/vad-react";
import { useEffect, useRef } from "react";

export function useVAD({ onSpeechStart, onSpeechEnd, onAudioChunk }) {
  // Convert 32-bit float audio array to Base64 to send to server.
  const float32ToBase64 = (float32Array) => {
    // scale to 16-bit PCM
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      s = s < 0 ? s * 0x8000 : s * 0x7FFF;
      view.setInt16(i * 2, s, true); // true for little-endian
    }
    
    let binary = '';
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const vad = useMicVAD({
    startOnLoad: false,
    onSpeechStart: () => {
      onSpeechStart();
    },
    onFrameProcessed: (probabilities) => {
      // Custom audio extraction or chunk sending logic.
      // @ricky0123/vad-react does not stream raw chunks directly in onFrameProcessed by default
      // but we will capture the audio buffer in onSpeechEnd or chunk it if needed.
      // For real-streaming we'd grab the stream from navigator.mediaDevices.
    },
    onSpeechEnd: (audio) => {
      // Audio is Float32Array from the VAD buffer
      const b64 = float32ToBase64(audio);
      if (onAudioChunk) onAudioChunk(b64);
      onSpeechEnd();
    },
    positiveSpeechThreshold: 0.8,
    negativeSpeechThreshold: 0.6,
    minSpeechFrames: 5,
  });

  return vad;
}