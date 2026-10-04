import { useRef, useState, useCallback, useEffect } from 'react';

const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];

function getSupportedMime() {
  if (typeof MediaRecorder === 'undefined') return '';
  for (const mt of MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mt)) return mt;
  }
  return '';
}

export function useVoiceRecorder({ maxSeconds = 60 } = {}) {
  const [state, setState] = useState('idle'); // idle, requesting, recording, processing
  const [audioBlob, setAudioBlob] = useState(null);
  const [error, setError] = useState(null);
  const [durationSec, setDurationSec] = useState(0);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const durationRef = useRef(0);

  const releaseStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  }, []);

  // Declared before `start`: the auto-stop timer inside `start` calls this,
  // and referencing a later `const` binding there is a temporal-dead-zone trap.
  const stop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
      setState('processing');
    }
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setAudioBlob(null);
    setDurationSec(0);
    durationRef.current = 0;
    setState('requesting');

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('getUserMedia unavailable');
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = getSupportedMime();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        releaseStream();
        const blob = new Blob(chunksRef.current, { type: mimeType || 'audio/webm' });
        chunksRef.current = [];
        setAudioBlob(blob);
        setState('idle');
      };

      recorder.start(200); // collect chunks every 200ms
      setState('recording');

      timerRef.current = setInterval(() => {
        durationRef.current += 1;
        setDurationSec(durationRef.current);
        if (durationRef.current >= maxSeconds) {
          stop();
        }
      }, 1000);
    } catch (err) {
      releaseStream();
      setState('idle');
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('mic_denied');
      } else {
        setError('mic_unavailable');
      }
    }
  }, [maxSeconds, stop, releaseStream]);

  const reset = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    releaseStream();
    chunksRef.current = [];
    setAudioBlob(null);
    setError(null);
    setDurationSec(0);
    setState('idle');
  }, [releaseStream]);

  // Without this the microphone stays live after the user leaves the page.
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  return { state, audioBlob, error, durationSec, start, stop, reset };
}
