import { useState, useCallback, useEffect, useRef } from 'react';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { api, errorMessage } from '../api/client';

const QUICK_PROMPTS = [
  'PM-KISAN பணம் எவ்வளவு?',
  'இலவச சட்ட உதவி எப்படி பெறுவது?',
  'மகளிர் உரிமை தொகை யாருக்கு?',
  'பட்டா மாறுதல் செய்வது எப்படி?',
  'RTI மனு எழுதுவது எப்படி?',
  '100 நாள் வேலை அட்டை எப்படி பெறுவது?',
];

function ThinkingCard() {
  return (
    <div className="thinking-card animate-fade-in">
      <div className="thinking-dots">
        <span /><span /><span />
      </div>
      <span className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem' }}>
        தகவல் தேடுகிறேன்...
      </span>
    </div>
  );
}

function AnswerCard({ answer, verification, onFeedback, onSpeak }) {
  const [open, setOpen] = useState(true);
  if (!answer) return null;

  // Only claim "verified" when the backend actually verified the answer.
  // The badge used to render unconditionally, including for ungrounded replies.
  const verified = verification?.passed === true;

  return (
    <div className="answer-card animate-slide-up">
      <div className="answer-header">
        <div className="answer-source">
          <span>📋</span>
          <span className="ta">அரசு அதிகாரப்பூர்வ தகவல்</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            className={verified ? 'verified-badge' : 'verified-badge unverified'}
            title={verified ? 'அரசு ஆவணத்திலிருந்து உறுதிப்படுத்தப்பட்டது' : 'அரசு ஆவணம் கிடைக்கவில்லை'}
          >
            {verified ? '✓ சரிபார்க்கப்பட்டது' : 'ℹ உறுதிப்படுத்தப்படவில்லை'}
          </span>
          <button className="icon-btn" onClick={() => setOpen(!open)} title="Toggle">
            {open ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {open && (
        <div className="answer-body">
          {answer.short && (
            <p className="answer-short ta">{answer.short}</p>
          )}

          {!verified && (
            <div className="answer-section">
              <div className="warning-item" style={{ borderRadius: 'var(--radius-md)' }}>
                ℹ️ இந்த விடை அதிகாரப்பூர்வ அரசு ஆவணத்திலிருந்து உறுதிப்படுத்தப்படவில்லை.
                முடிவெடுக்கும் முன் தாலுகா அலுவலகத்தில் உறுதி செய்யவும்.
              </div>
            </div>
          )}

          {answer.steps?.length > 0 && (
            <div className="answer-section">
              <div className="answer-section-title">செய்ய வேண்டியவை (Steps)</div>
              <div className="steps-list">
                {answer.steps.map((s, i) => (
                  <div className="step-item" key={i}>
                    <span className="step-num">{i + 1}</span>
                    <span className="ta">{s.replace(/^\d+[.)]\s*/, '')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {answer.documents?.length > 0 && (
            <div className="answer-section">
              <div className="answer-section-title">தேவையான ஆவணங்கள் (Documents)</div>
              <div className="docs-list">
                {answer.documents.map((d, i) => (
                  <span className="doc-tag" key={i}>📄 {d}</span>
                ))}
              </div>
            </div>
          )}

          {answer.where?.length > 0 && (
            <div className="answer-section">
              <div className="answer-section-title">எங்கு செல்வது (Where)</div>
              <div className="where-list">
                {answer.where.map((w, i) => (
                  <div className="where-item" key={i}>
                    <span className="where-name ta">{w.name}</span>
                    {w.phone && (
                      <a className="where-phone" href={`tel:${w.phone}`}>📞 {w.phone}</a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {(answer.cost || answer.time) && (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {answer.cost && <span className="tag tag-green">💰 {answer.cost}</span>}
              {answer.time && <span className="tag tag-blue">⏱ {answer.time}</span>}
            </div>
          )}

          {answer.warnings?.length > 0 && (
            <div className="answer-section">
              <div className="answer-section-title">கவனிக்கவும் (Caution)</div>
              <div className="warning-list">
                {answer.warnings.map((w, i) => (
                  <div className="warning-item" key={i}>⚠️ {w}</div>
                ))}
              </div>
            </div>
          )}

          {answer.sources?.length > 0 && (
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              {answer.sources.map((s, i) => (
                <a
                  key={i}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="tag tag-blue"
                  style={{ textDecoration: 'none' }}
                >
                  🔗 {s.name}
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="answer-footer">
        <div className="answer-meta">
          <span>📡 கிராம குரல் பாலம்</span>
        </div>
        <div className="answer-actions">
          <button className="icon-btn" title="கேட்க" onClick={onSpeak}>🔊</button>
          <button className="icon-btn" title="பகிர்" onClick={() => {
            if (navigator.share) navigator.share({ title: 'கிராம குரல் பாலம்', text: answer.short });
          }}>🔗</button>
          <button className="icon-btn" title="கருத்து தெரிவிக்க" onClick={onFeedback}>⭐</button>
        </div>
      </div>
    </div>
  );
}

function EmergencyBanner({ safety }) {
  if (!safety?.is_emergency) return null;
  const resp = safety.response || {};
  return (
    <div className="emergency-banner animate-slide-up">
      <h2>🚨 {resp.title_ta || 'அவசர உதவி'}</h2>
      <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem', lineHeight: 1.7 }}>
        {resp.message_ta}
      </p>
      <div className="emergency-numbers">
        {(resp.helpline_numbers || ['112']).map(n => (
          <a key={n} className="emergency-num" href={`tel:${n}`}>📞 {n}</a>
        ))}
      </div>
    </div>
  );
}

export default function VoicePage({ onFeedbackRequest }) {
  const { state: recState, audioBlob, error: recError, durationSec, start, stop } = useVoiceRecorder({ maxSeconds: 60 });
  const { playBase64, speakText, isPlaying, playbackError } = useAudioPlayer();

  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  const processResult = useCallback(async (res) => {
    setResult(res);
    if (res?.answer?.short && res?.audio_b64) {
      await playBase64(res.audio_b64);
    } else if (res?.answer?.short) {
      speakText(res.answer.short);
    }
  }, [playBase64, speakText]);

  const handleMicBtn = useCallback(async () => {
    if (recState === 'idle') {
      setResult(null);
      setErr(null);
      await start();
    } else if (recState === 'recording') {
      stop();
    }
  }, [recState, start, stop]);

  // Process the recorded audio once the recorder has finished and gone idle.
  // This was previously a `useState` initialiser, so it ran on mount and never
  // again: recorded audio was never sent to the backend.
  const handledBlobRef = useRef(null);

  useEffect(() => {
    if (recState !== 'idle' || !audioBlob) return;
    if (handledBlobRef.current === audioBlob) return;
    handledBlobRef.current = audioBlob;

    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const res = await api.voiceProcess(audioBlob);
        if (!cancelled) await processResult(res);
      } catch (e) {
        if (!cancelled) setErr(errorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [audioBlob, recState, processResult]);

  const handleTextSubmit = useCallback(async (text) => {
    if (!text?.trim()) return;
    setResult(null);
    setErr(null);
    setLoading(true);
    setTextInput('');
    try {
      const res = await api.textQuery(text.trim());
      await processResult(res);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [processResult]);

  const micState = (() => {
    if (recState === 'recording' || recState === 'requesting' || recState === 'processing') {
      return recState;
    }
    if (recError) return 'error';
    if (isPlaying) return 'playing';
    return 'idle';
  })();

  const micLabel = {
    idle: 'குரல் வழி கேளுங்கள்',
    requesting: 'மைக்ரோஃபோன் அனுமதி...',
    recording: `நிறுத்த அழுத்துங்கள் (${durationSec}s)`,
    processing: 'செயல்படுத்துகிறேன்...',
    playing: 'பதிவு ஒலிக்கிறது...',
    error: 'மீண்டும் முயற்சிக்கவும்'
  }[micState];

  const micGlyph = {
    idle: '🎤',
    requesting: '🎤',
    recording: '⏹',
    processing: '⏳',
    playing: '🔊',
    error: '⚠️'
  }[micState];

  return (
    <div className="voice-page">
      {/* Mic Area */}
      <div className="mic-area">
        <div className={`mic-btn-wrapper ${recState === 'recording' ? 'recording' : ''}`}>
          <div className="mic-btn-ring" style={{ width: 140, height: 140 }} />
          <div className="mic-btn-ring" style={{ width: 176, height: 176 }} />
          <button
            id="voice-mic-btn"
            className={`mic-btn ${micState}`}
            onClick={handleMicBtn}
            disabled={recState === 'requesting' || recState === 'processing' || loading}
            aria-label="Start voice recording"
          >
            {micGlyph}
          </button>
        </div>
        <p className="mic-status ta">{micLabel}</p>
        {recState === 'recording' && durationSec > 5 && (
          <span className="mic-timer">{durationSec}s / 60s</span>
        )}
      </div>

      {/* Text Input Row */}
      <div className="text-row">
        <input
          id="text-query-input"
          className="input ta"
          placeholder="தமிழில் தட்டச்சு செய்யவும்... உ.ம்: PM Kisan பணம் எப்படி பெறுவது?"
          value={textInput}
          onChange={e => setTextInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleTextSubmit(textInput)}
          disabled={loading}
        />
        <button
          id="text-submit-btn"
          className="btn btn-primary send-btn"
          onClick={() => handleTextSubmit(textInput)}
          disabled={loading || !textInput.trim()}
        >
          {loading ? <span className="spinner" /> : '➤'}
        </button>
      </div>

      {/* Quick Prompts */}
      <div className="quick-prompts">
        {QUICK_PROMPTS.map((q, i) => (
          <button key={i} className="quick-chip" onClick={() => handleTextSubmit(q)}>
            {q}
          </button>
        ))}
      </div>

      {/* Errors */}
      {(err || recError) && (
        <div className="warning-item" style={{ borderRadius: 'var(--radius-md)' }}>
          ⚠️ {err || (recError === 'mic_denied' ? 'மைக்ரோஃபோன் அனுமதி தேவை. அமைப்புகளில் அனுமதிக்கவும்.' : 'மைக்ரோஃபோன் கிடைக்கவில்லை.')}
        </div>
      )}

      {/* Audio playback failure - the text answer is still shown above */}
      {playbackError && (
        <div className="warning-item" style={{ borderRadius: 'var(--radius-md)' }}>
          🔇 {playbackError === 'audio_blocked'
            ? 'ஒலி தானியங்கு முடியவில்லை. பதிலைத் தெளிவாகப் படித்து பார்க்கவும்.'
            : 'ஒலி இயக்க முடியவில்லை. பதிலைத் தெளிவாகப் படித்து பார்க்கவும்.'}
        </div>
      )}

      {/* Thinking */}
      {loading && <ThinkingCard />}

      {/* Emergency Banner */}
      {result?.safety?.is_emergency && <EmergencyBanner safety={result.safety} />}

      {/* Answer */}
      {!loading && result?.answer && !result?.safety?.is_emergency && (
        <AnswerCard
          answer={result.answer}
          verification={result.verification}
          onSpeak={() => speakText(result.answer.short)}
          onFeedback={() => onFeedbackRequest(result.request_id)}
        />
      )}

      {/* Follow-ups */}
      {result?.follow_ups?.length > 0 && !loading && (
        <div>
          <div className="section-title" style={{ marginBottom: '0.5rem' }}>தொடர்ந்து கேளுங்கள்</div>
          <div className="followups">
            {result.follow_ups.map((f, i) => (
              <button key={i} className="followup-chip" onClick={() => handleTextSubmit(f)}>{f}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
