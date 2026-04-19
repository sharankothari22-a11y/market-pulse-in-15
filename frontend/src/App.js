import { useState } from 'react';
import '@/App.css';

import { TopBar } from '@/components/layout/TopBar';
import { ChatPanel } from '@/components/layout/ChatPanel';
import { SplashScreen } from '@/components/SplashScreen';

import MarketOverview from '@/pages/MarketOverview';
import ResearchSession from '@/pages/ResearchSession';
import SignalsAlerts from '@/pages/SignalsAlerts';
import MacroDashboard from '@/pages/MacroDashboard';

function App() {
  const [currentPage, setCurrentPage] = useState('/');
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [splashDone, setSplashDone] = useState(false);
  const [pendingTicker, setPendingTicker] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);

  const handleAnalyzeTicker = (t) => {
    const cleaned = String(t || '').trim().toUpperCase();
    if (!cleaned) return;
    setPendingTicker({ ticker: cleaned, nonce: Date.now() });
    setCurrentPage('/research');
  };

  const renderPage = () => {
    switch (currentPage) {
      case '/':
        return <MarketOverview onAnalyzeTicker={handleAnalyzeTicker} />;
      case '/research':
        return <ResearchSession onSessionChange={setCurrentSessionId} pendingTicker={pendingTicker} />;
      case '/signals':
        return <SignalsAlerts />;
      case '/macro':
        return <MacroDashboard />;
      default:
        return <MarketOverview />;
    }
  };

  return (
    <>
      {!splashDone && <SplashScreen onDone={() => setSplashDone(true)} />}

      <div
        className="app-container flex flex-col h-screen overflow-hidden"
        style={{ backgroundColor: 'var(--bi-bg-page)' }}
        data-testid="app-root"
      >
        <TopBar currentPage={currentPage} onNavigate={setCurrentPage} />
        <main
          className="flex-1 overflow-auto"
          style={{ backgroundColor: 'var(--bi-bg-page)' }}
        >
          <div style={{ maxWidth: 1600, margin: '0 auto', padding: '24px 48px' }}>
            {renderPage()}
          </div>
        </main>

        <ChatPanel
          sessionId={currentPage === '/research' ? currentSessionId : null}
          open={chatOpen}
          onOpen={() => setChatOpen(true)}
          onClose={() => setChatOpen(false)}
        />
      </div>
    </>
  );
}

export default App;
