import { useCallback, useEffect, useRef, useState } from 'react';

export function useAudioPlayer() {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackError, setPlaybackError] = useState(null);

  const playBase64 = useCallback((base64, mimeType = 'audio/mpeg') => {
    try {
      setPlaybackError(null);
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }
      const byteString = atob(base64);
      const byteArray = new Uint8Array(byteString.length);
      for (let i = 0; i < byteString.length; i++) byteArray[i] = byteString.charCodeAt(i);
      const blob = new Blob([byteArray], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.addEventListener('ended', () => setIsPlaying(false));
      audio.addEventListener('error', () => {
        setIsPlaying(false);
        setPlaybackError('audio_failed');
      });
      setIsPlaying(true);
      const played = audio.play();
      if (played && typeof played.catch === 'function') {
        played.catch(() => {
          setIsPlaying(false);
          setPlaybackError('audio_blocked');
        });
      }
      return played;
    } catch {
      setIsPlaying(false);
      setPlaybackError('audio_failed');
    }
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    setIsPlaying(false);
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, []);

  const speakText = useCallback((text, lang = 'ta-IN') => {
    if (!text) return;
    const synth = window.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    setPlaybackError(null);
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = lang;
    utt.rate = 0.9;
    utt.pitch = 1;
    setIsPlaying(true);
    utt.onend = () => setIsPlaying(false);
    utt.onerror = () => {
      setIsPlaying(false);
      setPlaybackError('speech_failed');
    };
    synth.speak(utt);
  }, []);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
        audioRef.current = null;
      }
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return { playBase64, stop, speakText, isPlaying, playbackError };
}