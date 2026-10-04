const EMERGENCY_LINES = [
  { number: '112', label: 'காவல் / மருத்துவம் / தீ' },
  { number: '181', label: 'பெண்கள் உதவி' },
  { number: '108', label: 'ஆம்புலன்ஸ்' },
  { number: '1098', label: 'குழந்தைகள் பாதுகாப்பு' },
  { number: '15100', label: 'இலவச சட்ட உதவி' },
];

export default function SOSModal({ onClose }) {
  return (
    <div className="sos-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="sos-modal">
        <div style={{ fontSize: '3rem' }}>🚨</div>
        <h2 style={{ color: 'var(--clr-danger)', fontFamily: 'var(--font-ta)', fontSize: '1.3rem' }}>
          அவசர உதவி தேவையா?
        </h2>
        <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.88rem', lineHeight: 1.7 }}>
          உடனடியாக அழைக்கவும். அனைத்தும் 24/7 இலவச சேவை.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', width: '100%' }}>
          {EMERGENCY_LINES.map(e => (
            <a
              key={e.number}
              href={`tel:${e.number}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.8rem 1.1rem',
                background: 'rgba(248,113,113,0.1)',
                border: '1px solid rgba(248,113,113,0.25)',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none'
              }}
            >
              <span className="ta" style={{ fontSize: '0.88rem', color: 'var(--clr-text-muted)' }}>{e.label}</span>
              <span style={{ fontFamily: 'var(--font-en)', fontSize: '1.2rem', fontWeight: 800, color: 'var(--clr-danger)' }}>
                📞 {e.number}
              </span>
            </a>
          ))}
        </div>
        <button className="btn btn-ghost w-full" onClick={onClose} style={{ marginTop: '0.5rem' }}>மூடு</button>
      </div>
    </div>
  );
}
