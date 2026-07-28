import { useState, useRef, useCallback, useMemo } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import StripeBg from '../components/StripeBg.jsx';
import Jackpot from '../components/Jackpot.jsx';
import Footer from '../components/Footer.jsx';
import PlotlyChart from './PlotlyChart.jsx';
import { WATCH_SUGGESTIONS } from '../data.js';

const API = 'http://localhost:8000';

function randomSuggestion() {
  return WATCH_SUGGESTIONS[Math.floor(Math.random() * WATCH_SUGGESTIONS.length)];
}

/*
  Growing panel sizing:
  - Idle / input focused: compact (width 55%, height 55%)
  - Each SSE event adds ~5% width and ~5% height
  - Caps at 96% × 92%
  - Clicking the input resets to compact
*/
function panelSize(eventCount, isCompact) {
  if (isCompact) return { width: '55%', height: '55%' };
  const w = Math.min(55 + eventCount * 5, 96);
  const h = Math.min(55 + eventCount * 5, 92);
  return { width: `${w}%`, height: `${h}%` };
}

function TraceEvent({ event }) {
  const cls = `trace-event trace-event--${event.type}`;

  if (event.type === 'stream_start') {
    return (
      <div className={cls}>
        <div className="trace-label">Stream Start</div>
        <div>Analysing: <strong>{event.data.question}</strong></div>
      </div>
    );
  }
  if (event.type === 'tool_call') {
    const { turn_index, tool_name, reasoning, args } = event.data;
    return (
      <div className={cls}>
        <div className="trace-label">
          Turn {turn_index} · {tool_name?.toUpperCase()}
        </div>
        {reasoning && <div className="trace-reasoning">↳ {reasoning}</div>}
        {args?.code && <pre className="trace-code">{args.code}</pre>}
      </div>
    );
  }
  if (event.type === 'observation') {
    const text = typeof event.data.result === 'object'
      ? JSON.stringify(event.data.result, null, 2)
      : String(event.data.result ?? '');
    return (
      <div className={cls}>
        <div className="trace-label">Observation</div>
        <pre className="trace-code">{text}</pre>
      </div>
    );
  }
  if (event.type === 'clarification') {
    return (
      <div className={cls}>
        <div className="trace-label">Clarification</div>
        <div>{event.data.question}</div>
      </div>
    );
  }
  if (event.type === 'thin_flag') {
    return (
      <div className={cls}>
        <div className="trace-label">Thin Finding (n={event.data.sample_size})</div>
        <div>{event.data.finding}</div>
      </div>
    );
  }
  if (event.type === 'final_answer') {
    return (
      <div className={cls}>
        <div className="trace-label">Final Answer</div>
        <div className="final-summary">{event.data.summary}</div>
        <div className="final-confidence">Confidence: {event.data.confidence}</div>
      </div>
    );
  }
  if (event.type === 'error') {
    return (
      <div className={cls}>
        <div className="trace-label">Error</div>
        <div>{event.data.message}</div>
      </div>
    );
  }
  return null;
}

export default function Chat({ apiKey, pastFindings, onEndSession }) {
  const [question, setQuestion] = useState('');
  const [events, setEvents] = useState([]);
  const [spinning, setSpinning] = useState(false);
  const [finalAnswer, setFinalAnswer] = useState(null);
  const [chartJson, setChartJson] = useState(null);
  const [toolCallsUsed, setToolCallsUsed] = useState([]);
  const [isCompact, setIsCompact] = useState(true);
  const suggestion = useMemo(randomSuggestion, []);
  const abortRef = useRef(null);
  const traceEndRef = useRef(null);

  const appendEvent = useCallback((ev) => {
    setEvents(prev => [...prev, ev]);
    setTimeout(() => traceEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
  }, []);

  async function sendQuestion() {
    if (!question.trim() || spinning) return;
    const q = question.trim();
    setQuestion('');
    setEvents([]);
    setFinalAnswer(null);
    setChartJson(null);
    setToolCallsUsed([]);
    setSpinning(true);
    setIsCompact(false); // start growing

    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await fetchEventSource(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, api_key: apiKey }),
        signal: ctrl.signal,
        openWhenHidden: true,

        onmessage(msg) {
          if (!msg.data) return;
          try {
            const payload = JSON.parse(msg.data);
            const eventType = msg.event || payload.type || 'unknown';
            appendEvent({ type: eventType, data: payload });

            if (eventType === 'tool_call') {
              setToolCallsUsed(prev => [...prev, {
                tool: payload.tool_name,
                args: payload.args || {},
              }]);
            }
            if (eventType === 'observation' && payload.result?.chart_json) {
              setChartJson(payload.result.chart_json);
            }
            if (eventType === 'final_answer') {
              setFinalAnswer(payload);
              setSpinning(false);
            }
            if (eventType === 'error') {
              setSpinning(false);
            }
          } catch (_) {}
        },
        onerror(err) {
          appendEvent({ type: 'error', data: { message: err?.message || 'Stream error' } });
          setSpinning(false);
          throw err;
        },
        onclose() { setSpinning(false); },
      });
    } catch (_) {
      setSpinning(false);
    }
  }

  async function saveAndEnd() {
    if (!finalAnswer) return;
    const q = events.find(e => e.type === 'stream_start')?.data?.question || '';
    try {
      await fetch(`${API}/api/session/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q,
          summary: finalAnswer.summary,
          confidence: finalAnswer.confidence,
          chart_ref: finalAnswer.chart_ref || '',
          tool_calls_used: toolCallsUsed,
        }),
      });
    } finally {
      onEndSession();
    }
  }

  function handleInputFocus() {
    // Clicking the input resets the panel to compact
    setIsCompact(true);
  }

  const size = panelSize(events.length, isCompact);
  const isIdle = !spinning && events.length === 0;

  return (
    <>
      {/* Poster stripes — always behind */}
      <StripeBg />

      <div className="overlay-page">
        {/* Top bar */}
        <div className="chat-topbar">
          <span className="chat-brand">Boxd<span>Bot</span></span>
          <div className="chat-topbar-actions">
            {finalAnswer && (
              <button className="btn-topbar" onClick={saveAndEnd}>
                Save &amp; End
              </button>
            )}
            <button className="btn-topbar" onClick={onEndSession}>Setup</button>
          </div>
        </div>

        {/* Centered growing panel */}
        <div className="chat-arena">
          <div
            className="chat-panel"
            style={{ width: size.width, height: size.height }}
          >
            {/* Inner split: jackpot left, content right */}
            <div className="chat-panel-inner">
              <Jackpot spinning={spinning} />

              <div className="chat-main">
                {/* Thinking bar */}
                {spinning && (
                  <div className="chat-thinking-bar">
                    <div className="chat-thinking-q">
                      {events.find(e => e.type === 'stream_start')?.data?.question || question}
                    </div>
                    <div className="chat-thinking-hint">{suggestion}</div>
                  </div>
                )}

                {/* Trace */}
                <div className="trace-panel">
                  {isIdle && pastFindings.length > 0 && (
                    <div className="past-findings-hint">
                      <div className="trace-label">Past Findings ({pastFindings.length})</div>
                      {pastFindings.slice(-3).map((f, i) => (
                        <div key={i} className="past-finding-item">· {f.finding_summary}</div>
                      ))}
                    </div>
                  )}

                  {events.map((ev, i) => <TraceEvent key={i} event={ev} />)}

                  {chartJson && (
                    <div className="chart-wrapper">
                      <PlotlyChart chartJson={chartJson} />
                    </div>
                  )}
                  <div ref={traceEndRef} />
                </div>

                {/* Input */}
                <div className="chat-input-row">
                  <input
                    id="chat-question-input"
                    className="chat-input"
                    type="text"
                    placeholder="Ask something about your Letterboxd data…"
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && sendQuestion()}
                    onFocus={handleInputFocus}
                    disabled={spinning}
                  />
                  <button
                    id="chat-send-btn"
                    className="btn-send"
                    onClick={sendQuestion}
                    disabled={spinning || !question.trim()}
                  >
                    {spinning ? '…' : 'Ask →'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <Footer />
      </div>
    </>
  );
}
