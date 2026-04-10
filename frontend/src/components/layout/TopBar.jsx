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
      className="h-12 bg-[#ffffff] border-b border-[#e5e7eb] flex items-center justify-between px-4"
      data-testid="top-bar"
    >
      {/* Left: Page Title */}
      <h1 className="text-lg font-outfit font-semibold text-[#0f172a]">
        {pageTitles[currentPage] || 'Dashboard'}
      </h1>

      {/* Center: IST Clock */}
      <div className="flex items-center gap-2" data-testid="ist-clock">
        <span className="text-sm text-[#64748b]">IST</span>
        <span className="text-sm font-mono text-[#0f172a]">{formatIST(time)}</span>
      </div>

      {/* Right: DB Status + Last Refresh */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2" data-testid="db-status">
          <Database className="w-4 h-4 text-[#64748b]" />
          <span 
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[#16a34a]' : 'bg-[#dc2626]'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <span className="text-xs text-[#64748b]" data-testid="last-refresh">
          Last refresh: {formatIST(time)}
        </span>
      </div>
    </header>
  );
};
