import { useCallback, useEffect, useRef, useState } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';

export function useVAD({ 
  onSpeechStart, 
  onSpeechEnd,
  onFrameProcessed,
  enabled = true,
  minSpeechFrames = 3
}) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const vadWorkletNode = useRef(null);

  const vad = useMicVAD({
    onSpeechStart: () => {
      setIsSpeaking(true);
      onSpeechStart?.();
    },
    onFrameProcessed: (audioFrame, isSpeech) => {
      // Send audio frame to server if speaking
      if (isSpeech && onFrameProcessed) {
        // Convert audio frame to base64
        const int16Array = new Int16Array(audioFrame.buffer);
        const uint8Array = new Uint8Array(int16Array.buffer);
        onFrameProcessed(uint8Array);
      }
    },
    onSpeechEnd: (audioFrame) => {
      setIsSpeaking(false);
      onSpeechEnd?.();
    },
    positiveSpeechThreshold: 0.5,
    negativeSpeechThreshold: 0.35,
    minSpeechFrames: minSpeechFrames,
    preSpeechProcessorFrames: 5,
    rediationAdjustment: 1.0,
    // VAD model settings
    modelFetchUrl: '/models/',
    modelURL: '/models/silero_vad.onnx',
    workletNodeOptions: {
      outputProbability: 0.4,
      onnxModelFetchOptions: {
        progressCallback: (progress) => {
          console.log(`VAD model download: ${(progress.loaded / progress.total * 100).toFixed(1)}%`);
        }
      }
    }
  });

  const startListening = useCallback(() => {
    vad.start();
    setIsListening(true);
  }, [vad]);

  const stopListening = useCallback(() => {
    vad.pause();
    setIsListening(false);
    setIsSpeaking(false);
  }, [vad]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  useEffect(() => {
    if (enabled && !isListening) {
      startListening();
    } else if (!enabled && isListening) {
      stopListening();
    }
    return () => {
      if (isListening) {
        stopListening();
      }
    };
  }, [enabled, isListening, startListening, stopListening]);

  return {
    isListening,
    isSpeaking,
    startListening,
    stopListening,
    toggleListening,
    vad
  };
}
