import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useApp } from '../lib/AppContext';

export function ChatPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { sessionId, setSessionId, setLastDebug } = useApp();
  const { messages, loading, prompts, debug, send } = useChat(sessionId, setSessionId);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const autoSent = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    setLastDebug(debug as Record<string, unknown>);
  }, [debug, setLastDebug]);

  useEffect(() => {
    const state = location.state as { prefill?: string; autoSend?: boolean } | null;
    if (state?.prefill && !autoSent.current) {
      autoSent.current = true;
      if (state.autoSend) {
        void send(state.prefill);
      } else {
        setInput(state.prefill);
      }
      navigate('/ai', { replace: true, state: {} });
    }
  }, [location.state, navigate, send]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const t = input;
    setInput('');
    void send(t);
  };

  const isUrdu = (lang?: string, text?: string) =>
    lang === 'urdu' || (text ? /[\u0600-\u06FF]/.test(text) : false);

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div>
          <div className="brand-mark" style={{ fontSize: 16 }}>
            <div className="brand-logo" style={{ width: 28, height: 28 }} />
            JazzCash AI
          </div>
          <div style={{ fontSize: 11, color: 'var(--jc-muted)', marginTop: 2 }}>
            Concept Demo · No real transactions
          </div>
        </div>
        <button
          type="button"
          onClick={() => navigate('/voice')}
          style={{
            border: 'none',
            background: 'var(--jc-red)',
            color: 'white',
            borderRadius: 999,
            padding: '8px 12px',
            fontWeight: 700,
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          Voice
        </button>
      </header>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="bubble ai">
            Assalamualaikum! Main JazzCash AI hoon. English, Urdu, ya Roman Urdu mein poochhein —
            services, fees, offers, troubleshooting, ya navigation.
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`bubble ${m.role === 'user' ? 'user' : 'ai'}${
              isUrdu(m.language, m.content) ? ' urdu' : ''
            }`}
          >
            {m.content}
            {m.action && (
              <div>
                <button
                  type="button"
                  className="action-btn"
                  onClick={() => navigate(m.action!.route)}
                >
                  {m.action.label} →
                </button>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="bubble ai">
            <div className="typing" aria-label="Thinking">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="quick-prompts">
        {prompts.map((p) => (
          <button key={p} type="button" onClick={() => void send(p)} disabled={loading}>
            {p}
          </button>
        ))}
      </div>

      <form className="chat-composer" onSubmit={onSubmit}>
        <button
          type="button"
          aria-label="Voice"
          onClick={() => navigate('/voice')}
          style={{
            width: 42,
            height: 42,
            borderRadius: '50%',
            border: 'none',
            background: 'var(--jc-red)',
            color: 'white',
            cursor: 'pointer',
          }}
        >
          🎙
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            width: 42,
            height: 42,
            borderRadius: '50%',
            border: 'none',
            background: 'var(--jc-ink)',
            color: 'white',
            cursor: 'pointer',
          }}
        >
          ↑
        </button>
      </form>
    </div>
  );
}
