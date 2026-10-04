import { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function RightsPage() {
  const [topics, setTopics] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    api.rightsTopics()
      .then(r => setTopics(r.topics || []))
      .catch(() => setTopics([]))
      .finally(() => setLoadingTopics(false));
  }, []);

  const handleTopicClick = async (topic) => {
    setSelected(topic);
    setLoadingDetail(true);
    setDetail(null);
    try {
      const d = await api.rightsTopic(topic.id);
      setDetail(d);
    } catch {
      setDetail({ chunks: [] });
    } finally {
      setLoadingDetail(false);
    }
  };

  if (selected) {
    return (
      <div className="topic-detail">
        <button className="back-btn" onClick={() => { setSelected(null); setDetail(null); }}>
          ← திரும்பு
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '2rem' }}>{selected.icon}</span>
          <div>
            <div className="page-title" style={{ fontSize: '1.1rem' }}>{selected.title_ta}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-subtle)' }}>{selected.title_en}</div>
          </div>
        </div>
        {selected.description_ta && (
          <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem', lineHeight: 1.7, background: 'var(--clr-surface)', padding: '0.9rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--clr-border)' }}>
            {selected.description_ta}
          </p>
        )}
        {loadingDetail && (
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', color: 'var(--clr-text-muted)' }}>
            <span className="spinner" /><span className="ta">தகவல் ஏற்றுகிறேன்...</span>
          </div>
        )}
        {detail?.chunks?.map((chunk, i) => (
          <div className="chunk-card animate-fade-in" key={i} style={{ animationDelay: `${i * 0.06}s` }}>
            <div className="chunk-section-title">{chunk.section || chunk.title}</div>
            <p className="chunk-content ta">{chunk.content?.replace(/^[^\\n]+\n/, '') || chunk.content}</p>
            {chunk.source_url && (
              <a href={chunk.source_url} target="_blank" rel="noopener noreferrer" className="tag tag-blue" style={{ textDecoration: 'none', width: 'fit-content', marginTop: '0.25rem' }}>
                🔗 {chunk.source_name}
              </a>
            )}
          </div>
        ))}
        {detail && detail.chunks?.length === 0 && !loadingDetail && (
          <div className="ta" style={{ textAlign: 'center', color: 'var(--clr-text-muted)', padding: '2rem' }}>
            இத்தலைப்பில் இப்போது நேரடி வழிகாட்டல் இல்லை. குரல் வழியில் கேளுங்கள்.
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rights-page">
      <div className="page-title">⚖️ உங்கள் உரிமைகள் அறியுங்கள்</div>
      <p className="ta" style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem', lineHeight: 1.7 }}>
        சட்டம், நில உரிமைகள், தொழிலாளர் உரிமைகள் மற்றும் அரசு சேவைகளை இலவசமாக அறியுங்கள்.
      </p>
      {loadingTopics ? (
        <div className="topics-grid">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="skeleton" style={{ height: 130 }} />
          ))}
        </div>
      ) : (
        <div className="topics-grid">
          {topics.map((t, i) => (
            <div
              key={t.id}
              className="topic-card animate-fade-in"
              style={{ animationDelay: `${i * 0.05}s` }}
              onClick={() => handleTopicClick(t)}
            >
              <span className="topic-icon">{t.icon}</span>
              <div className="topic-title ta">{t.title_ta}</div>
              <div className="topic-desc ta">{t.description_ta?.slice(0, 80)}...</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
