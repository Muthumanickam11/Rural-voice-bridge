import { useState } from 'react';
import { api } from '../api/client';

const PROFILE_FIELDS = [
  {
    key: 'occupation',
    label_ta: 'தொழில் / Occupation',
    options: [
      { value: 'farmer', label: 'விவசாயி (Farmer)' },
      { value: 'tenant_farmer', label: 'குத்தகை விவசாயி (Tenant Farmer)' },
      { value: 'labourer', label: 'விவசாய கூலி (Agricultural Labourer)' },
      { value: 'worker', label: 'பொதுத் தொழிலாளி (General Worker)' },
      { value: 'student', label: 'மாணவர் (Student)' },
      { value: 'women_head', label: 'குடும்பத் தலைவி (Women Head of Family)' },
      { value: 'senior', label: 'முதியோர் (Senior Citizen)' },
    ]
  },
  {
    key: 'gender',
    label_ta: 'பாலினம் / Gender',
    options: [
      { value: 'M', label: 'ஆண் (Male)' },
      { value: 'F', label: 'பெண் (Female)' },
      { value: 'Other', label: 'திருநங்கை / மற்றவர் (Transgender/Other)' },
    ]
  },
  {
    key: 'age_group',
    label_ta: 'வயது வகுப்பு / Age Group',
    options: [
      { value: 'under_18', label: '18 வயதிற்கு கீழ்' },
      { value: '18_to_59', label: '18 – 59 வயது' },
      { value: '60_plus', label: '60 வயது மேல் (முதியோர்)' },
    ]
  },
  {
    key: 'family_income_bucket',
    label_ta: 'குடும்ப ஆண்டு வருமானம் / Annual Family Income',
    options: [
      { value: 'below_1.2L', label: '₹1,20,000-க்கு கீழ்' },
      { value: '1.2L_to_2.5L', label: '₹1,20,000 – ₹2,50,000' },
      { value: 'above_2.5L', label: '₹2,50,000-க்கு மேல்' },
    ]
  },
  {
    key: 'ration_card',
    label_ta: 'ரேஷன் கார்டு வகை / Ration Card Type',
    options: [
      { value: 'AAY', label: 'அந்தியோதய (AAY – ஆரஞ்சு அட்டை)' },
      { value: 'PHH', label: 'முன்னுரிமை குடும்ப அட்டை (PHH)' },
      { value: 'NPHH', label: 'முன்னுரிமை அல்லாத (NPHH)' },
      { value: 'none', label: 'ரேஷன் கார்டு இல்லை' },
    ]
  },
  {
    key: 'owns_land',
    label_ta: 'நில உரிமை / Land Ownership',
    options: [
      { value: 'yes', label: 'ஆம், என் பெயரில் பட்டா உள்ளது' },
      { value: 'family_not_in_my_name', label: 'குடும்ப நிலம் உண்டு, என் பெயரில் இல்லை' },
      { value: 'no', label: 'இல்லை / நிலமற்றோர்' },
    ]
  },
  {
    key: 'family_taxpayer_or_govt',
    label_ta: 'வருமான வரி / அரசு ஊழியர் / Government Employee or Taxpayer',
    options: [
      { value: false, label: 'இல்லை (No – not in family)' },
      { value: true, label: 'ஆம் (Yes – someone in family pays income tax or is a govt employee)' },
    ]
  },
];

function SchemeResultCard({ scheme, type }) {
  const [expanded, setExpanded] = useState(false);
  const names = scheme.names || {};
  const benefit = scheme.benefit || {};
  return (
    <div className={`scheme-card ${type}`} onClick={() => setExpanded(!expanded)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="scheme-name">{names.ta || scheme.scheme_id}</div>
          <div className="scheme-benefit">{benefit.description_ta || benefit.frequency}</div>
        </div>
        <div className="scheme-amount">₹{(benefit.amount_inr || 0).toLocaleString('ta')}</div>
      </div>
      {type === 'eligible' && <span className="tag tag-green">✓ நீங்கள் தகுதியுடையவர்</span>}
      {type === 'maybe' && <span className="tag tag-amber">⚠ தகுதி சாத்தியம் – சரிபார்க்கவும்</span>}
      {scheme.maybe_notes?.length > 0 && expanded && (
        <div className="warning-item" style={{ fontSize: '0.8rem' }}>
          📋 {scheme.maybe_notes.join(' | ')}
        </div>
      )}
      {expanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {scheme.documents?.length > 0 && (
            <div className="docs-list" style={{ marginTop: '0.5rem' }}>
              {scheme.documents.map((d, i) => <span key={i} className="doc-tag">📄 {d}</span>)}
            </div>
          )}
          {scheme.apply?.offline && (
            <div style={{ fontSize: '0.8rem', color: 'var(--clr-text-muted)' }} className="ta">
              📍 {scheme.apply.offline}
            </div>
          )}
          {scheme.helpline?.length > 0 && (
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              {scheme.helpline.map(n => (
                <a key={n} href={`tel:${n}`} className="tag tag-blue">📞 {n}</a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SchemesPage() {
  const [profile, setProfile] = useState({});
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (key, val) => {
    setProfile(prev => ({ ...prev, [key]: val === 'true' ? true : val === 'false' ? false : val }));
  };

  const handleCheck = async () => {
    setLoading(true);
    setResults(null);
    try {
      const res = await api.schemesCheck(profile);
      setResults(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const totalBenefit = results?.likely_eligible?.reduce((s, sc) => s + (sc.benefit?.amount_inr || 0), 0) || 0;

  return (
    <div className="scheme-page">
      <div className="page-title">🧾 அரசு திட்டங்கள் சோதிக்கவும்</div>
      <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem', lineHeight: 1.7 }}>
        உங்கள் விவரங்களை தேர்வு செய்தால் நீங்கள் எந்தெந்த அரசு திட்டங்களுக்கு தகுதியுடையவர் என்பதை உடனடியாக சரிபார்க்கலாம்.
      </p>

      <div className="scheme-form">
        {PROFILE_FIELDS.map(f => (
          <div className="form-group" key={f.key}>
            <label className="form-label ta" htmlFor={`field-${f.key}`}>{f.label_ta}</label>
            <select
              id={`field-${f.key}`}
              className="form-select"
              value={profile[f.key] !== undefined ? String(profile[f.key]) : ''}
              onChange={e => handleChange(f.key, e.target.value)}
            >
              <option value="">-- தேர்வு செய்யவும் --</option>
              {f.options.map(o => (
                <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
              ))}
            </select>
          </div>
        ))}
        <button
          id="scheme-check-btn"
          className="btn btn-primary w-full"
          onClick={handleCheck}
          disabled={loading || Object.keys(profile).length === 0}
          style={{ marginTop: '0.5rem', padding: '0.9rem' }}
        >
          {loading ? <span className="spinner" /> : '🔍 திட்டங்கள் சோதிக்கவும்'}
        </button>
      </div>

      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Summary Banner */}
          {results.likely_eligible?.length > 0 && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(52,211,153,0.12), rgba(74,158,255,0.08))',
              border: '1px solid rgba(52,211,153,0.3)',
              borderRadius: 'var(--radius-lg)',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.35rem'
            }}>
              <div style={{ fontFamily: 'var(--font-en)', fontSize: '0.75rem', color: 'var(--clr-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>
                தகுதியான திட்டங்கள் ({results.likely_eligible.length})
              </div>
              <div style={{ fontFamily: 'var(--font-en)', fontSize: '1.9rem', fontWeight: 800, color: 'var(--clr-secondary)' }}>
                ₹{totalBenefit.toLocaleString()}+ / year
              </div>
              <div className="ta" style={{ fontSize: '0.85rem', color: 'var(--clr-text-muted)' }}>
                மொத்த சாத்தியமான ஆண்டு பலன் (ஆவணங்கள் சமர்ப்பித்த பிறகு)
              </div>
            </div>
          )}

          {results.likely_eligible?.length > 0 && (
            <div className="scheme-result-section eligible">
              <h3>✅ நேர்மையான தகுதி ({results.likely_eligible.length})</h3>
              {results.likely_eligible.map(s => (
                <SchemeResultCard key={s.scheme_id} scheme={s} type="eligible" />
              ))}
            </div>
          )}

          {results.maybe_eligible?.length > 0 && (
            <div className="scheme-result-section maybe">
              <h3>⚠️ சாத்தியமான தகுதி – சரிபார்க்கவும் ({results.maybe_eligible.length})</h3>
              {results.maybe_eligible.map(s => (
                <SchemeResultCard key={s.scheme_id} scheme={s} type="maybe" />
              ))}
            </div>
          )}

          {results.fix_list?.length > 0 && (
            <div style={{
              background: 'var(--clr-surface)',
              border: '1px solid var(--clr-border)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem 1.1rem'
            }}>
              <div className="answer-section-title" style={{ marginBottom: '0.5rem' }}>திட்டங்கள் பெற தயார் செய்ய வேண்டியவை</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {results.fix_list.map((f, i) => (
                  <div key={i} className="ta" style={{ fontSize: '0.85rem', color: 'var(--clr-text-muted)', display: 'flex', gap: '0.5rem' }}>
                    <span>📌</span><span>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.likely_eligible?.length === 0 && results.maybe_eligible?.length === 0 && (
            <div className="ta" style={{ textAlign: 'center', color: 'var(--clr-text-muted)', padding: '2rem', background: 'var(--clr-surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--clr-border)' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🔍</div>
              <p>தேர்ந்தெடுத்த விவரங்களுடன் நேர்மையான திட்ட தகுதி கிடைக்கவில்லை. விவரங்களை மாற்றி மீண்டும் முயற்சிக்கவும் அல்லது இ-சேவை மையத்தில் நேரில் சரிபார்க்கவும்.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
