import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type User } from '../lib/api';

const POPULAR = [
  { name: 'Send Money', route: '/send-money', icon: '↗' },
  { name: 'Bills', route: '/bills', icon: '⌁' },
  { name: 'Recharge', route: '/mobile-recharge', icon: '☎' },
  { name: 'Savings', route: '/savings', icon: '◆' },
  { name: 'Offers', route: '/offers', icon: '%' },
  { name: 'Raast', route: '/send-money', icon: '⚡' },
  { name: 'Insurance', route: '/insurance', icon: '◈' },
  { name: 'Support', route: '/support', icon: '?' },
];

const SUGGESTIONS = [
  'Mujhe electricity bill pay karna hai',
  'What is Raast?',
  'JazzCash mein savings ke kya options hain?',
  'Where can I find my transaction history?',
  'Any cashback offers?',
];

export function HomePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    api.user().then((u) => setUser(u as unknown as User)).catch(() => {
      setUser({
        id: 'demo',
        name: 'Fahem',
        phone: '',
        wallet_balance: 24850.75,
        currency: 'PKR',
        environment: 'Concept Demo — No real transactions',
      });
    });
  }, []);

  const ask = (text: string) => {
    navigate('/ai', { state: { prefill: text, autoSend: true } });
  };

  return (
    <div className="page">
      <header className="page-header">
        <div className="brand-mark">
          <div className="brand-logo" />
          JazzCash AI
        </div>
        <button
          type="button"
          className="icon-btn"
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: 'none',
            background: 'white',
            cursor: 'pointer',
          }}
          onClick={() => navigate('/voice')}
          aria-label="Open voice assistant"
        >
          🎙
        </button>
      </header>

      <h1 className="greeting">How can I help you?</h1>
      <p className="greeting-ur">آپ کیا کرنا چاہتے ہیں؟</p>

      {user && (
        <div className="balance-chip">
          <div className="balance-label">Hi {user.name} · Demo wallet</div>
          <div className="balance-value">
            Rs. {user.wallet_balance.toLocaleString('en-PK', { minimumFractionDigits: 2 })}
          </div>
        </div>
      )}

      <form
        className="ask-bar"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) ask(query.trim());
        }}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything… English / اردو / Roman"
          aria-label="Ask JazzCash AI"
        />
        <button
          type="button"
          className="icon-btn mic-btn"
          onClick={() => navigate('/voice')}
          aria-label="Voice"
        >
          🎙
        </button>
        <button type="submit" className="icon-btn send-btn" aria-label="Send">
          →
        </button>
      </form>

      <div className="section-title">Popular services</div>
      <div className="service-grid">
        {POPULAR.map((s) => (
          <button
            key={s.name}
            type="button"
            className="service-tile"
            onClick={() => navigate(s.route)}
          >
            <span className="tile-icon">{s.icon}</span>
            {s.name}
          </button>
        ))}
      </div>

      <div className="section-title">Suggested questions</div>
      <div className="prompt-list">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" className="prompt-chip" onClick={() => ask(s)}>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
