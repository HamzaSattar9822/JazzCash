import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type Offer, type Product, type Service, type Txn } from '../lib/api';

function PageShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  return (
    <div className="page">
      <header className="page-header">
        <h2 style={{ margin: 0, fontSize: 20 }}>{title}</h2>
        <button
          type="button"
          onClick={() => navigate('/ai')}
          style={{
            border: 'none',
            background: 'var(--jc-red)',
            color: 'white',
            borderRadius: 999,
            padding: '6px 10px',
            fontSize: 11,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Ask AI
        </button>
      </header>
      {children}
    </div>
  );
}

export function ServicesPage() {
  const navigate = useNavigate();
  const [services, setServices] = useState<Service[]>([]);
  useEffect(() => {
    api.services().then((r) => setServices(r.services)).catch(() => undefined);
  }, []);
  return (
    <PageShell title="Services">
      {services.map((s) => (
        <button
          key={s.id}
          type="button"
          className="list-row"
          style={{ width: '100%', cursor: 'pointer', textAlign: 'left', border: '1px solid var(--jc-line)' }}
          onClick={() => navigate(s.route)}
        >
          <div>
            <div className="title">{s.name}</div>
            <div className="meta">{s.description}</div>
          </div>
          <span>→</span>
        </button>
      ))}
    </PageShell>
  );
}

export function BillsPage() {
  const billers = ['LESCO Electricity', 'K-Electric', 'SSGC Gas', 'SNGPL', 'Passport Fee', 'PTCL'];
  return (
    <PageShell title="Bill Payment">
      <p style={{ color: 'var(--jc-muted)', fontSize: 13 }}>
        Demo screen — select a biller. No real payments.
      </p>
      {billers.map((b) => (
        <div key={b} className="list-row">
          <div className="title">{b}</div>
          <span style={{ color: 'var(--jc-red)', fontWeight: 700 }}>Pay</span>
        </div>
      ))}
    </PageShell>
  );
}

export function RechargePage() {
  return (
    <PageShell title="Mobile Recharge">
      <div className="list-row">
        <div>
          <div className="title">Jazz Prepaid</div>
          <div className="meta">Enter number & amount (demo)</div>
        </div>
      </div>
      <div className="list-row">
        <div>
          <div className="title">Other networks</div>
          <div className="meta">Telenor · Ufone · Zong</div>
        </div>
      </div>
    </PageShell>
  );
}

export function SendMoneyPage() {
  return (
    <PageShell title="Send Money">
      <p style={{ color: 'var(--jc-muted)', fontSize: 13 }}>
        Guidance only — this demo never executes transfers.
      </p>
      {['JazzCash Transfer', 'Raast', 'Bank Transfer', 'CNIC Transfer'].map((t) => (
        <div key={t} className="list-row">
          <div className="title">{t}</div>
          <span>→</span>
        </div>
      ))}
    </PageShell>
  );
}

export function TransactionsPage() {
  const [txns, setTxns] = useState<Txn[]>([]);
  useEffect(() => {
    api.transactions().then((r) => setTxns(r.transactions)).catch(() => undefined);
  }, []);
  return (
    <PageShell title="Transactions">
      {txns.map((t) => (
        <div key={t.id} className="list-row">
          <div>
            <div className="title">{t.title}</div>
            <div className="meta">
              {t.id} · {new Date(t.timestamp).toLocaleString()}
            </div>
            <span className={`badge ${t.status}`}>{t.status}</span>
            {t.failure_reason && (
              <div className="meta" style={{ color: 'var(--jc-danger)' }}>
                {t.failure_reason}
              </div>
            )}
          </div>
          <div className={`amount ${t.amount < 0 ? 'neg' : 'pos'}`}>
            {t.amount < 0 ? '-' : '+'}Rs. {Math.abs(t.amount).toLocaleString()}
          </div>
        </div>
      ))}
    </PageShell>
  );
}

export function SavingsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  useEffect(() => {
    api
      .products()
      .then((r) => setProducts(r.products.filter((p) => p.category === 'savings')))
      .catch(() => undefined);
  }, []);
  return (
    <PageShell title="Savings">
      {products.map((p) => (
        <div key={p.id} className="offer-card">
          <h3>{p.name}</h3>
          <p>{p.description}</p>
          {p.apr && (
            <div style={{ marginTop: 8, fontWeight: 700, fontSize: 13 }}>{p.apr}</div>
          )}
        </div>
      ))}
    </PageShell>
  );
}

export function InsurancePage() {
  const [products, setProducts] = useState<Product[]>([]);
  useEffect(() => {
    api
      .products()
      .then((r) => setProducts(r.products.filter((p) => p.category === 'insurance')))
      .catch(() => undefined);
  }, []);
  return (
    <PageShell title="Insurance">
      {products.map((p) => (
        <div key={p.id} className="offer-card">
          <h3>{p.name}</h3>
          <p>{p.description}</p>
        </div>
      ))}
    </PageShell>
  );
}

export function OffersPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  useEffect(() => {
    api.offers().then((r) => setOffers(r.offers)).catch(() => undefined);
  }, []);
  return (
    <PageShell title="Offers">
      {offers.map((o) => (
        <div key={o.id} className="offer-card">
          <h3>{o.title}</h3>
          <p>{o.description}</p>
          <div className="meta" style={{ marginTop: 8, fontSize: 11, color: 'var(--jc-muted)' }}>
            Valid until {o.valid_until}
          </div>
        </div>
      ))}
    </PageShell>
  );
}

export function SupportPage() {
  return (
    <PageShell title="Support">
      <div className="list-row">
        <div>
          <div className="title">Open ticket SUP-4401</div>
          <div className="meta">Failed SSGC bill payment · open</div>
        </div>
      </div>
      <div className="list-row">
        <div>
          <div className="title">Helpline</div>
          <div className="meta">Demo only — not a real number</div>
        </div>
      </div>
      <p style={{ fontSize: 13, color: 'var(--jc-muted)' }}>
        JazzCash AI can guide you, but never asks for MPIN or OTP.
      </p>
    </PageShell>
  );
}

export function MorePage() {
  const navigate = useNavigate();
  const links = [
    { label: 'Offers', route: '/offers' },
    { label: 'Insurance', route: '/insurance' },
    { label: 'Savings', route: '/savings' },
    { label: 'Support', route: '/support' },
    { label: 'Voice Assistant', route: '/voice' },
  ];
  return (
    <PageShell title="More">
      {links.map((l) => (
        <button
          key={l.route}
          type="button"
          className="list-row"
          style={{ width: '100%', cursor: 'pointer', textAlign: 'left' }}
          onClick={() => navigate(l.route)}
        >
          <div className="title">{l.label}</div>
          <span>→</span>
        </button>
      ))}
    </PageShell>
  );
}
