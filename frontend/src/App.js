import { useState } from "react";
import "@/App.css";

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { ChatPanel } from '@/components/layout/ChatPanel';

import MarketOverview from '@/pages/MarketOverview';
import ResearchSession from '@/pages/ResearchSession';
import SignalsAlerts from '@/pages/SignalsAlerts';
import MacroDashboard from '@/pages/MacroDashboard';

function App() {
  const [currentPage, setCurrentPage] = useState('/');
  const [currentSessionId, setCurrentSessionId] = useState(null);

  const renderPage = () => {
    switch (currentPage) {
      case '/':
        return <MarketOverview />;
      case '/research':
        return <ResearchSession onSessionChange={setCurrentSessionId} />;
      case '/signals':
        return <SignalsAlerts />;
      case '/macro':
        return <MacroDashboard />;
      default:
        return <MarketOverview />;
    }
  };

  return (
    <div className="app-container flex h-screen overflow-hidden bg-[#ffffff]" data-testid="app-root">
      {/* Left Sidebar */}
      <Sidebar activePage={currentPage} onNavigate={setCurrentPage} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar currentPage={currentPage} />
        <main className="flex-1 overflow-hidden bg-[#ffffff]">
          {renderPage()}
        </main>
      </div>

      {/* Right Chat Panel */}
      <ChatPanel sessionId={currentPage === '/research' ? currentSessionId : null} />
    </div>
  );
}

export default App;
