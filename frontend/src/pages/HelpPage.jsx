import { useState, useEffect } from 'react';
import { api } from '../api/client';

const TYPE_LABELS = {
  emergency: { label: 'அவசர', color: 'var(--clr-danger)' },
  safety: { label: 'பாதுகாப்பு', color: 'var(--clr-warning)' },
  health: { label: 'மருத்துவம்', color: 'var(--clr-secondary)' },
  legal: { label: 'சட்டம்', color: 'var(--clr-primary)' },
  social: { label: 'சமூக நலன்', color: 'var(--clr-secondary)' },
  grievance: { label: 'புகார்', color: 'var(--clr-warning)' },
  agriculture: { label: 'வேளாண்மை', color: 'var(--clr-secondary)' },
};

export default function HelpPage() {
  const [helplines, setHelplines] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [offices, setOffices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    Promise.all([
      api.helplines().then(r => r.helplines || []).catch(() => []),
      api.helpcentersDistricts()
        // /helpcenters/districts now returns { districts: [...], total: n }.
        .then(r => r?.districts || [])
        .catch(() => [])
    ]).then(([h, d]) => {
      setHelplines(h);
      setDistricts(Array.isArray(d) ? d : []);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // Clearing synchronously in the effect is what trips set-state-in-effect, so
    // derive "no district selected" during render instead of pushing state here.
    if (!selectedDistrict) return;
    let cancelled = false;
    api
      .helpcentersDistrict(selectedDistrict)
      .then(r => { if (!cancelled) setOffices(r.offices || []); })
      .catch(() => { if (!cancelled) setOffices([]); });
    return () => { cancelled = true; };
  }, [selectedDistrict]);

  const visibleOffices = selectedDistrict ? offices : [];

  const filteredHelplines = filter === 'all' ? helplines : helplines.filter(h => h.type === filter);
  const uniqueTypes = [...new Set(helplines.map(h => h.type))];

  return (
    <div className="help-page">
      <div className="page-title">📞 உதவி மையங்கள்</div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
        <button className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-ghost'}`} style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem' }} onClick={() => setFilter('all')}>
          அனைத்தும்
        </button>
        {uniqueTypes.map(t => (
          <button key={t} className={`btn ${filter === t ? 'btn-primary' : 'btn-ghost'}`} style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem' }} onClick={() => setFilter(t)}>
            {TYPE_LABELS[t]?.label || t}
          </button>
        ))}
      </div>

      {/* Helplines */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 72 }} />)}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {filteredHelplines.map(h => {
            return (
              <div className="helpline-card" key={h.id}>
                <a className="helpline-number" href={`tel:${h.number}`}>{h.number}</a>
                <div className="helpline-info">
                  <div className="helpline-name ta">{h.name_ta}</div>
                  <div className="helpline-hours">{h.hours}</div>
                </div>
                <a className="call-link" href={`tel:${h.number}`}>📞 அழைக்க</a>
              </div>
            );
          })}
        </div>
      )}

      {/* District Offices */}
      <div className="section-title" style={{ marginTop: '0.5rem' }}>மாவட்ட அலுவலகங்கள்</div>
      <div className="form-group">
        <select
          className="form-select"
          value={selectedDistrict}
          onChange={e => setSelectedDistrict(e.target.value)}
        >
          <option value="">-- மாவட்டம் தேர்வு செய்யவும் --</option>
          {districts.map(d => (
            <option key={d.id} value={d.id}>{d.name_ta} ({d.name_en})</option>
          ))}
        </select>
      </div>

      {visibleOffices.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {visibleOffices.map((o, i) => (
            <div className="office-card" key={i}>
              <div className="office-type">{o.type?.toUpperCase()}</div>
              <div className="office-name ta">{o.name_ta}</div>
              {o.address && <div className="office-address">{o.address}</div>}
              {o.phone && (
                <a href={`tel:${o.phone}`} className="where-phone" style={{ marginTop: '0.25rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                  📞 {o.phone}
                </a>
              )}
              {o.timing && (
                <div style={{ fontSize: '0.72rem', color: 'var(--clr-text-subtle)' }}>🕐 {o.timing}</div>
              )}
              {o.services?.length > 0 && (
                <div className="office-services">
                  {o.services.map((s, j) => <span key={j} className="service-tag ta">{s}</span>)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
