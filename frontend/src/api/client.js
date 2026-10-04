// All API calls go through this central client
const BASE = '/api/v1';

const ADMIN_TOKEN_KEY = 'rvb_admin_token';

export function getAdminToken() {
  try {
    return localStorage.getItem(ADMIN_TOKEN_KEY) || '';
  } catch {
    return '';
  }
}

export function setAdminToken(token) {
  try {
    if (token) localStorage.setItem(ADMIN_TOKEN_KEY, token);
    else localStorage.removeItem(ADMIN_TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getSessionId() {
  try {
    let id = sessionStorage.getItem('rvb_session_id');
    if (!id) {
      id = newId();
      sessionStorage.setItem('rvb_session_id', id);
    }
    return id;
  } catch {
    return newId();
  }
}

async function request(path, opts = {}) {
  const sessionId = getSessionId();
  const headers = {
    'X-Session-Id': sessionId,
    ...(opts.headers || {})
  };

  // An explicit requestId is passed through so a query and its later feedback
  // submission share the same correlation id. Otherwise one is minted here.
  headers['X-Request-Id'] = opts.requestId || newId();
  if (opts.adminToken) headers['X-Admin-Token'] = opts.adminToken;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { ...opts, headers });
  } catch {
    const err = new Error('Network unavailable');
    err.code = 'E_NO_NET';
    err.message_ta = 'இணைய இணைப்பு இல்லை. அவசர உதவி எண்கள் வழக்கம் போல் செயல்படும்.';
    err.retryable = true;
    throw err;
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    // Normalise every error shape into { code, message_en, message_ta, retryable, status }.
    const env = data && data.error ? data.error : null;
    const detail = data && data.detail;
    const err = new Error(
      env?.message_en ||
      (typeof detail === 'string' ? detail : 'Unexpected error')
    );
    err.status = res.status;
    err.code = env?.code || (res.status === 429 ? 'E_LIMIT' : 'E_INTERNAL');
    err.message_en = env?.message_en || err.message;
    err.message_ta =
      env?.message_ta ||
      (Array.isArray(detail)
        ? 'உள்ளீடு சரியாக இல்லை. மீண்டும் முயற்சிக்கவும்.'
        : typeof detail === 'string'
          ? detail
          : 'தொழில்நுட்ப கோளாறு ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.');
    err.retryable = env?.retryable ?? res.status >= 500;
    err.request_id = env?.request_id || res.headers.get('X-Request-Id');
    throw err;
  }

  return data;
}

// Single call site for error messages, so no page shows a raw English string.
export function errorMessage(err, fallback = 'தொழில்நுட்ப கோளாறு ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.') {
  return err?.message_ta || fallback;
}

export const api = {
  health: () => request('/health'),
  ready: () => request('/ready'),

  textQuery: (text, language = 'ta', requestId = null) =>
    request('/text/query', {
      method: 'POST',
      requestId,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language })
    }),

  voiceProcess: (audioBlob, language = 'ta', requestId = null) => {
    const fd = new FormData();
    fd.append('audio', audioBlob, 'voice.webm');
    fd.append('language', language);
    return request('/voice/process', { method: 'POST', body: fd, requestId });
  },

  voiceTranscript: (transcript, language = 'ta', requestId = null) => {
    const fd = new FormData();
    fd.append('transcript', transcript);
    fd.append('language', language);
    return request('/voice/process', { method: 'POST', body: fd, requestId });
  },

  tts: (text, speed = 1.0) =>
    request('/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, speed })
    }),

  schemesCheck: (profile) =>
    request('/schemes/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile })
    }),

  schemesList: () => request('/schemes'),
  schemeDetail: (id) => request(`/schemes/${encodeURIComponent(id)}`),

  generateRti: (payload) =>
    request('/rti/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),

  rightsTopics: () => request('/rights/topics'),
  rightsTopic: (id) => request(`/rights/${encodeURIComponent(id)}`),

  helpcentersList: () => request('/helpcenters'),
  helpcentersDistricts: () => request('/helpcenters/districts'),
  helpcentersDistrict: (id) => request(`/helpcenters?district=${encodeURIComponent(id)}`),
  helplines: () => request('/helpcenters/helplines'),

  feedback: (payload) =>
    request('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),

  adminMetrics: (token) => request('/admin/metrics', { adminToken: token || getAdminToken() }),
  adminLogs: (limit = 30, token) =>
    request(`/admin/logs?limit=${limit}`, { adminToken: token || getAdminToken() })
};
