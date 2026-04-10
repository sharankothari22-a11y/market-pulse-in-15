import { useState, useEffect } from 'react';
import { Database } from 'lucide-react';

const pageTitles = {
  '/': 'Market Overview',
  '/research': 'Research Session',
  '/signals': 'Signals & Alerts',
  '/macro': 'Macro Dashboard',
  '/settings': 'Settings',
};

export const TopBar = ({ currentPage }) => {
  const [time, setTime] = useState(new Date());
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatIST = (date) => {
    return date.toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  return (
    <header 
      className="h-12 bg-[#111827] border-b border-[#1f2937] flex items-center justify-between px-4"
      data-testid="top-bar"
    >
      {/* Left: Page Title */}
      <h1 className="text-lg font-outfit font-semibold text-[#f9fafb]">
        {pageTitles[currentPage] || 'Dashboard'}
      </h1>

      {/* Center: IST Clock */}
      <div className="flex items-center gap-2" data-testid="ist-clock">
        <span className="text-sm text-[#9ca3af]">IST</span>
        <span className="text-sm font-mono text-[#f9fafb]">{formatIST(time)}</span>
      </div>

      {/* Right: DB Status + Last Refresh */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2" data-testid="db-status">
          <Database className="w-4 h-4 text-[#9ca3af]" />
          <span 
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <span className="text-xs text-[#9ca3af]" data-testid="last-refresh">
          Last refresh: {formatIST(time)}
        </span>
      </div>
    </header>
  );
};
