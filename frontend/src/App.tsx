import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { BottomNav } from './components/BottomNav';
import { DevPanel, DevToggle } from './components/DevPanel';
import { AppProvider } from './lib/AppContext';
import { ChatPage } from './pages/ChatPage';
import { HomePage } from './pages/HomePage';
import {
  BillsPage,
  InsurancePage,
  MorePage,
  OffersPage,
  RechargePage,
  SavingsPage,
  SendMoneyPage,
  ServicesPage,
  SupportPage,
  TransactionsPage,
} from './pages/MockPages';
import { VoicePage } from './pages/VoicePage';

function Shell() {
  return (
    <div className="desktop-stage">
      <div className="stage-label">JazzCash AI — Concept Demo · 390×844</div>
      <div className="phone-frame">
        <div className="phone-screen">
          <div className="demo-banner">Concept Demo — No real transactions</div>
          <DevToggle />
          <div className="app-shell">
            <div className="app-content">
              <Routes>
                <Route path="/" element={<Navigate to="/home" replace />} />
                <Route path="/home" element={<HomePage />} />
                <Route path="/ai" element={<ChatPage />} />
                <Route path="/voice" element={<VoicePage />} />
                <Route path="/services" element={<ServicesPage />} />
                <Route path="/bills" element={<BillsPage />} />
                <Route path="/mobile-recharge" element={<RechargePage />} />
                <Route path="/send-money" element={<SendMoneyPage />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/savings" element={<SavingsPage />} />
                <Route path="/insurance" element={<InsurancePage />} />
                <Route path="/offers" element={<OffersPage />} />
                <Route path="/support" element={<SupportPage />} />
                <Route path="/more" element={<MorePage />} />
              </Routes>
            </div>
            <BottomNav />
            <DevPanel />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </AppProvider>
  );
}
