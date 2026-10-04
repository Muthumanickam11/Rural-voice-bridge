import { useState } from 'react';
import { api } from '../api/client';

const REASONS = [
  { value: 'wrong', label: 'தவறான தகவல்' },
  { value: 'outdated', label: 'பழைய / காலாவதியான தகவல்' },
  { value: 'confusing', label: 'புரியவில்லை' },
  { value: 'too_long', label: 'மிக நீளமாக உள்ளது' },
  { value: 'audio_bad', label: 'ஆடியோ சரியில்லை' },
  { value: 'other', label: 'மற்றவை' },
];

export default function FeedbackModal({ requestId, onClose }) {
  const [rating, setRating] = useState(0);
  const [reason, setReason] = useState('');
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!rating) return;
    setLoading(true);
    try {
      await api.feedback({ request_id: requestId, rating, reason, comment });
      setSubmitted(true);
      setTimeout(onClose, 1500);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feedback-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="feedback-modal">
        {submitted ? (
          <div style={{ textAlign: 'center', padding: '1rem' }}>
            <div style={{ fontSize: '3rem' }}>🙏</div>
            <p className="ta" style={{ color: 'var(--clr-secondary)', fontWeight: 600, marginTop: '0.5rem' }}>
              உங்கள் கருத்துக்கு மிக்க நன்றி!
            </p>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="ta" style={{ fontSize: '1.05rem', color: 'var(--clr-text)' }}>கருத்து தெரிவிக்கவும்</h3>
              <button className="icon-btn" onClick={onClose}>✕</button>
            </div>
            <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.88rem' }}>இந்த பதில் பயனுள்ளதாக இருந்ததா?</p>
            <div className="star-row">
              {[1,2,3,4,5].map(s => (
                <button key={s} className={`star-btn ${rating >= s ? 'active' : ''}`} onClick={() => setRating(s)}>
                  ⭐
                </button>
              ))}
            </div>
            {rating > 0 && rating <= 3 && (
              <>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {REASONS.map(r => (
                    <button
                      key={r.value}
                      className={`tag ta ${reason === r.value ? 'tag-blue' : ''}`}
                      style={{ cursor: 'pointer', background: reason === r.value ? '' : 'var(--clr-surface-2)', border: '1px solid var(--clr-border)', padding: '0.35rem 0.7rem', borderRadius: 'var(--radius-full)', fontSize: '0.78rem', color: reason === r.value ? '' : 'var(--clr-text-muted)' }}
                      onClick={() => setReason(r.value)}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
                <textarea
                  className="input ta"
                  rows={2}
                  placeholder="கூடுதல் கருத்து (விரும்பினால்)..."
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                />
              </>
            )}
            <button
              id="feedback-submit-btn"
              className="btn btn-primary w-full"
              onClick={handleSubmit}
              disabled={!rating || loading}
            >
              {loading ? <span className="spinner" /> : 'அனுப்பு'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
