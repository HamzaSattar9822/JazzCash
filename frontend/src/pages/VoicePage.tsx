import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useVoiceAssistant } from '../hooks/useChat';
import { useApp } from '../lib/AppContext';

const STATE_LABEL: Record<string, { en: string; ur: string }> = {
  idle: { en: 'Ready', ur: 'تیار' },
  listening: { en: 'Listening...', ur: 'سن رہا ہوں...' },
  processing: { en: 'Thinking...', ur: 'سمجھ رہا ہوں...' },
  speaking: { en: 'Speaking...', ur: 'جواب دے رہا ہوں...' },
  error: { en: 'Error', ur: 'خرابی' },
};

export function VoicePage() {
  const navigate = useNavigate();
  const { sessionId, setSessionId, setLastDebug } = useApp();
  const {
    state,
    transcript,
    reply,
    error,
    levels,
    debug,
    startListening,
    stopListening,
    bargeIn,
    interruptAndListen,
  } = useVoiceAssistant(sessionId, setSessionId);

  useEffect(() => {
    setLastDebug({
      language: debug.language,
      intent: debug.intent,
      latency: debug,
      agentState: state,
    });
  }, [debug, state, setLastDebug]);

  const label = STATE_LABEL[state] || STATE_LABEL.idle;

  return (
    <div className="voice-page">
      <button
        type="button"
        onClick={() => navigate(-1)}
        style={{
          alignSelf: 'flex-start',
          border: 'none',
          background: 'transparent',
          fontWeight: 600,
          cursor: 'pointer',
          marginBottom: 8,
        }}
      >
        ← Back
      </button>

      <div className="voice-state">
        {label.en} · {label.ur}
      </div>

      <div className={`voice-orb ${state}`}>
        <div className="ring" />
        <div className="core" />
      </div>

      <div className="waveform" aria-hidden>
        {levels.map((h, i) => (
          <i
            key={i}
            style={{ height: state === 'listening' || state === 'speaking' ? h : 6 }}
          />
        ))}
      </div>

      <div className={`transcript-box${transcript ? '' : ' empty'}`}>
        <div style={{ fontSize: 11, color: 'var(--jc-muted)', marginBottom: 4 }}>You</div>
        {transcript || 'Tap mic and speak in English, Urdu, or Roman Urdu…'}
      </div>

      <div className={`response-box${reply ? '' : ' empty'}`}>
        <div style={{ fontSize: 11, color: 'var(--jc-muted)', marginBottom: 4 }}>JazzCash AI</div>
        {error || reply || 'AI response will appear here'}
      </div>

      <div className="voice-controls">
        {state === 'listening' ? (
          <button type="button" className="btn-primary" onClick={stopListening}>
            Stop & Send
          </button>
        ) : state === 'speaking' ? (
          <>
            <button type="button" className="btn-danger" onClick={bargeIn}>
              Stop AI
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => void interruptAndListen()}
            >
              Interrupt
            </button>
          </>
        ) : state === 'processing' ? (
          <button type="button" className="btn-secondary" disabled>
            Processing…
          </button>
        ) : (
          <button type="button" className="btn-primary" onClick={() => void startListening()}>
            🎙 Tap to speak
          </button>
        )}
      </div>
    </div>
  );
}
