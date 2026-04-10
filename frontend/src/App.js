import { useState } from "react";
import "@/App.css";

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { ChatPanel } from '@/components/layout/ChatPanel';

import MarketOverview from '@/pages/MarketOverview';
import ResearchSession from '@/pages/ResearchSession';
import SignalsAlerts from '@/pages/SignalsAlerts';
import MacroDashboard from '@/pages/MacroDashboard';

const PageRenderer = ({ currentPage }) => {
  switch (currentPage) {
    case '/':
      return <MarketOverview />;
    case '/research':
      return <ResearchSession />;
    case '/signals':
      return <SignalsAlerts />;
    case '/macro':
      return <MacroDashboard />;
    default:
      return <MarketOverview />;
  }
};

function App() {
  const [currentPage, setCurrentPage] = useState('/');

  return (
    <div className="app-container flex h-screen overflow-hidden bg-[#ffffff]" data-testid="app-root">
      {/* Left Sidebar */}
      <Sidebar activePage={currentPage} onNavigate={setCurrentPage} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar currentPage={currentPage} />
        <main className="flex-1 overflow-hidden bg-[#ffffff]">
          <PageRenderer currentPage={currentPage} />
        </main>
      </div>

      {/* Right Chat Panel */}
      <ChatPanel />
    </div>
  );
}

export default App;
