import { useState } from 'react';
import StripeBg from '../components/StripeBg.jsx';
import Footer from '../components/Footer.jsx';

const API = 'http://localhost:8000';

export default function Setup({ onSessionStart }) {
  const [apiKey, setApiKey] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleStart() {
    if (!apiKey.trim()) { setError('API key is required.'); return; }
    if (!file) { setError('Please select a Letterboxd CSV file.'); return; }
    setError('');
    setLoading(true);

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API}/api/session/new`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      onSessionStart(apiKey.trim(), data.past_findings || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <StripeBg />
      <div className="overlay-page">
        <div className="setup-content">
          <div className="setup-tag">BoxdBot — Setup</div>

          <div className="setup-card">
            <h1>Configure<br />Session</h1>

            <div>
              <label className="setup-label" htmlFor="api-key-input">
                Groq API Key
              </label>
              <input
                id="api-key-input"
                className="setup-input"
                type="password"
                placeholder="gsk_..."
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleStart()}
                autoFocus
              />
            </div>

            <div>
              <label className="setup-label">Letterboxd CSV Export</label>
              <label
                htmlFor="csv-file-input"
                className={`file-drop${file ? ' has-file' : ''}`}
              >
                <input
                  id="csv-file-input"
                  type="file"
                  accept=".csv"
                  style={{ display: 'none' }}
                  onChange={e => setFile(e.target.files[0] || null)}
                />
                {file
                  ? <span className="file-name">✓ {file.name}</span>
                  : <span>Click to select diary.csv or ratings.csv</span>
                }
              </label>
            </div>

            {error && <div className="setup-error">{error}</div>}

            <button
              id="start-session-btn"
              className="btn-start"
              onClick={handleStart}
              disabled={loading}
            >
              {loading ? 'Starting…' : '→ Start Session'}
            </button>
          </div>
        </div>

        <Footer />
      </div>
    </>
  );
}
