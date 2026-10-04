import { useState } from 'react';
import './App.css';
import VoicePage from './pages/VoicePage';
import SchemesPage from './pages/SchemesPage';
import RightsPage from './pages/RightsPage';
import RTIPage from './pages/RTIPage';
import HelpPage from './pages/HelpPage';
import AdminPage from './pages/AdminPage';
import FeedbackModal from './components/FeedbackModal';
import SOSModal from './components/SOSModal';

const TABS = [
  { id: 'voice',   icon: '🎤', label: 'குரல்',   labelEn: 'Voice' },
  { id: 'schemes', icon: '🧾', label: 'திட்டங்கள்', labelEn: 'Schemes' },
  { id: 'rights',  icon: '⚖️', label: 'உரிமை',   labelEn: 'Rights' },
  { id: 'rti',     icon: '📝', label: 'RTI',      labelEn: 'RTI' },
  { id: 'help',    icon: '📞', label: 'உதவி',    labelEn: 'Help' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('voice');
  const [feedbackReqId, setFeedbackReqId] = useState(null);
  const [showSOS, setShowSOS] = useState(false);

  return (
    <div className="app-shell">
      {/* Top Navigation */}
      <nav className="navbar">
        <a className="nav-brand" href="/">
          <div className="logo-icon">🌾</div>
          <div className="brand-text">
            <span className="brand-ta">கிராம குரல் பாலம்</span>
            <span className="brand-en">Rural Voice Bridge</span>
          </div>
        </a>
        <div className="nav-actions">
          <button
            id="sos-btn"
            className="sos-btn"
            onClick={() => setShowSOS(true)}
            aria-label="SOS Emergency"
          >
            🚨 SOS
          </button>
          <button
            className="btn btn-ghost"
            style={{ padding: '0.4rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setActiveTab('admin')}
            title="Admin Dashboard"
          >
            ⚙️
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="page-container">
        {activeTab === 'voice'   && <VoicePage   onFeedbackRequest={id => setFeedbackReqId(id)} />}
        {activeTab === 'schemes' && <SchemesPage />}
        {activeTab === 'rights'  && <RightsPage  />}
        {activeTab === 'rti'     && <RTIPage      />}
        {activeTab === 'help'    && <HelpPage     />}
        {activeTab === 'admin'   && <AdminPage    />}
      </main>

      {/* Bottom Tab Bar */}
      <nav className="bottom-nav">
        {TABS.map(t => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            className={`nav-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span className="tab-icon">{t.icon}</span>
            <span className="ta">{t.label}</span>
          </button>
        ))}
      </nav>

      {/* Modals */}
      {feedbackReqId && (
        <FeedbackModal requestId={feedbackReqId} onClose={() => setFeedbackReqId(null)} />
      )}
      {showSOS && <SOSModal onClose={() => setShowSOS(false)} />}
    </div>
  );
}
