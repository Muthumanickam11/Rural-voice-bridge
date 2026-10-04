import { useState } from 'react';
import { api, errorMessage } from '../api/client';

const DEPARTMENTS = [
  'வருவாய் துறை (Revenue Department)',
  'வேளாண்மை துறை (Agriculture Department)',
  'கல்வி துறை (Education Department)',
  'சுகாதார துறை (Health Department)',
  'காவல் துறை (Police Department)',
  'குடிசை மாற்று வாரியம் (Slum Clearance Board)',
  'மின்வாரியம் (TANGEDCO)',
  'தமிழ் வளர்ச்சி துறை (Tamil Development)',
  'சமூக நலத் துறை (Social Welfare)',
  'மாவட்ட ஆட்சியர் அலுவலகம் (Collectorate)',
];

const DISTRICTS = [
  'Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem',
  'Tirunelveli', 'Vellore', 'Thanjavur', 'Dharmapuri', 'Villupuram',
  'Erode', 'Tiruppur', 'Kancheepuram', 'Dindigul', 'Nagercoil'
].sort();

export default function RTIPage() {
  const [form, setForm] = useState({
    problem: '',
    department: '',
    district: '',
    is_bpl: false,
    ref_numbers: '',
    applicant_name: '',
    applicant_address: ''
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('en');

  const handleSubmit = async () => {
    if (!form.problem || !form.department || !form.district) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.generateRti(form);
      setResult(res);
    } catch (e) {
      // Show the Tamil user-facing message instead of a silent console error.
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).catch(() => {});
  };

  return (
    <div className="rti-page">
      <div className="page-title">📝 RTI மனு உருவாக்குங்கள்</div>
      <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem', lineHeight: 1.7 }}>
        உங்கள் பிரச்சனை விவரங்களை உள்ளிட்டால் அதிகாரப்பூர்வ RTI விண்ணப்பம் உடனடியாக உருவாக்கப்படும்.
      </p>

      {!result && (
        <div className="scheme-form">
          {error && (
            <div className="warning-item ta" style={{ borderRadius: 'var(--radius-md)' }}>{error}</div>
          )}
          <div className="form-group">
            <label className="form-label ta" htmlFor="rti-problem">பிரச்சனை என்ன? (உங்கள் மொழியில் விவரிக்கவும்)</label>
            <textarea
              id="rti-problem"
              className="input ta"
              rows={4}
              placeholder="உ.ம்: என் PM-KISAN விண்ணப்பம் ஏன் நிராகரிக்கப்பட்டது என்று தெரியவில்லை. வேளாண் அலுவலகத்திற்கு சென்றேன், பதில் இல்லை..."
              value={form.problem}
              onChange={e => setForm(p => ({ ...p, problem: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label className="form-label ta" htmlFor="rti-dept">அரசு துறை</label>
            <select id="rti-dept" className="form-select" value={form.department} onChange={e => setForm(p => ({ ...p, department: e.target.value }))}>
              <option value="">-- துறையை தேர்வு செய்யவும் --</option>
              {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label ta" htmlFor="rti-dist">மாவட்டம்</label>
            <select id="rti-dist" className="form-select" value={form.district} onChange={e => setForm(p => ({ ...p, district: e.target.value }))}>
              <option value="">-- மாவட்டம் தேர்வு செய்யவும் --</option>
              {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label ta" htmlFor="rti-ref">முந்தைய விண்ணப்ப / கோப்பு எண் (விரும்பினால்)</label>
            <input id="rti-ref" className="input" placeholder="Optional reference number..." value={form.ref_numbers} onChange={e => setForm(p => ({ ...p, ref_numbers: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label ta" htmlFor="rti-name">விண்ணப்பதாரர் பெயர் (விரும்பினால்)</label>
            <input id="rti-name" className="input ta" placeholder="உங்கள் பெயர்..." value={form.applicant_name} onChange={e => setForm(p => ({ ...p, applicant_name: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label ta" htmlFor="rti-addr">முகவரி (விரும்பினால்)</label>
            <input id="rti-addr" className="input ta" placeholder="கிராமம், தாலுகா, மாவட்டம்..." value={form.applicant_address} onChange={e => setForm(p => ({ ...p, applicant_address: e.target.value }))} />
          </div>
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.is_bpl} onChange={e => setForm(p => ({ ...p, is_bpl: e.target.checked }))} style={{ width: 18, height: 18 }} />
              <span className="form-label ta" style={{ margin: 0 }}>BPL / AAY ரேஷன் கார்டு உள்ளது (கட்டணம் இலவசம்)</span>
            </label>
          </div>
          <button
            id="rti-generate-btn"
            className="btn btn-primary w-full"
            onClick={handleSubmit}
            disabled={loading || !form.problem || !form.department || !form.district}
            style={{ padding: '0.9rem', marginTop: '0.5rem' }}
          >
            {loading ? <span className="spinner" /> : '📄 RTI மனு உருவாக்கு'}
          </button>
        </div>
      )}

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <button className="back-btn" onClick={() => setResult(null)}>← மீண்டும் திருத்து</button>

          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className={`btn ${activeTab === 'en' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setActiveTab('en')}>English Letter</button>
            <button className={`btn ${activeTab === 'ta' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setActiveTab('ta')}>தமிழ் விளக்கம்</button>
          </div>

          <div className="rti-letter">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span className="section-title" style={{ borderBottom: 'none', paddingBottom: 0 }}>
                {activeTab === 'en' ? 'Official RTI Application Letter' : 'தமிழ் விளக்கம்'}
              </span>
              <button
                className="btn btn-ghost"
                style={{ padding: '0.3rem 0.7rem', fontSize: '0.78rem' }}
                onClick={() => copyToClipboard(activeTab === 'en' ? result.letter_en : result.letter_ta)}
              >
                📋 நகல் எடுக்கவும்
              </button>
            </div>
            <pre>{activeTab === 'en' ? result.letter_en : result.letter_ta}</pre>
          </div>

          {/* Checklist */}
          <div>
            <div className="section-title" style={{ marginBottom: '0.6rem' }}>✅ மனு அனுப்பும் முன் சரிபார்க்க வேண்டியவை</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {result.checklist?.map((c, i) => (
                <div key={i} className="checklist-item">
                  <span className="checklist-icon">✓</span>
                  <span className="ta">{c.replace(/^\d+[.)] ?/, '')}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Route advice */}
          {result.route_advice && (
            <div className="warning-item ta" style={{ background: 'rgba(74,158,255,0.06)', borderColor: 'rgba(74,158,255,0.2)', color: 'var(--clr-primary)' }}>
              💡 {result.route_advice}
            </div>
          )}

          {/* Deadline reminder */}
          <div className="tag tag-green" style={{ fontSize: '0.88rem', padding: '0.6rem 1rem', borderRadius: 'var(--radius-md)' }}>
            ⏱ மனு அனுப்பிய நாளிலிருந்து {result.deadline_days} நாட்களுக்குள் தகவல் கிடைக்க வேண்டும்.
          </div>
        </div>
      )}
    </div>
  );
}
