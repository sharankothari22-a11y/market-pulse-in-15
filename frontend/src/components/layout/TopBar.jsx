import { useState, useEffect } from 'react';
import { Database } from 'lucide-react';
import { apiGet, API_ENDPOINTS } from '@/services/api';

const pageTitles = {
  '/':         'MARKET OVERVIEW',
  '/research': 'RESEARCH SESSION',
  '/signals':  'SIGNALS & ALERTS',
  '/macro':    'MACRO DASHBOARD',
  '/settings': 'SETTINGS',
};

const findIndicator = (arr, id) => (arr || []).find(i => i.id === id);

export const TopBar = ({ currentPage }) => {
  const [time, setTime] = useState(new Date());
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [isConnected] = useState(true);
  const [indices, setIndices] = useState({ nifty: null, sensex: null });

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const fetchIdx = async () => {
      try {
        const data = await apiGet(API_ENDPOINTS.macro);
        const nifty  = findIndicator(data?.indicators, '^NSEI');
        const sensex = findIndicator(data?.indicators, '^BSESN');
        setIndices({ nifty, sensex });
        setLastRefresh(new Date());
      } catch (e) { /* silent */ }
    };
    fetchIdx();
    const t = setInterval(fetchIdx, 60000);
    return () => clearInterval(t);
  }, []);

  const formatIST = (date) =>
    date.toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    });

  const IndexPill = ({ label, data }) => {
    if (!data) {
      return (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm"
             style={{ backgroundColor: 'rgba(201, 168, 76, 0.08)', border: '1px solid rgba(201, 168, 76, 0.22)' }}>
          <span style={{ color: 'rgba(201, 168, 76, 0.85)', fontSize: 10, letterSpacing: '0.15em' }}>{label}</span>
          <span style={{ color: 'rgba(245, 240, 232, 0.4)', fontSize: 11 }}>—</span>
        </div>
      );
    }
    const isPos = data.changeType === 'positive';
    return (
      <div
        className="flex items-center gap-2 px-2.5 py-1 rounded-sm tabular-nums"
        style={{
          backgroundColor: 'rgba(201, 168, 76, 0.08)',
          border: '1px solid rgba(201, 168, 76, 0.28)',
        }}
      >
        <span style={{ color: '#C9A84C', fontSize: 10, letterSpacing: '0.15em', fontWeight: 600 }}>{label}</span>
        <span style={{ color: '#F5F0E8', fontSize: 11.5, fontWeight: 500 }}>
          {typeof data.raw_value === 'number'
            ? data.raw_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
            : data.value}
        </span>
        <span style={{
          color: isPos ? '#5EBE92' : '#E05252',
          fontSize: 10.5,
          fontWeight: 600,
        }}>
          {isPos ? '▲' : '▼'} {data.change}
        </span>
      </div>
    );
  };

  return (
    <header
      className="h-12 flex items-center justify-between px-5"
      style={{
        backgroundColor: '#0A1628',
        borderBottom: '1px solid rgba(201, 168, 76, 0.3)',
      }}
      data-testid="top-bar"
    >
      {/* Left: Page Title — gold serif */}
      <h1
        className="font-serif-display"
        style={{
          color: '#C9A84C',
          fontSize: 14,
          fontWeight: 700,
          letterSpacing: '0.28em',
        }}
      >
        {pageTitles[currentPage] || 'DASHBOARD'}
      </h1>

      {/* Center: Index pills + IST Clock */}
      <div className="flex items-center gap-3">
        <IndexPill label="NIFTY 50" data={indices.nifty} />
        <IndexPill label="SENSEX"   data={indices.sensex} />
        <div className="flex items-center gap-2 ml-2" data-testid="ist-clock">
          <span style={{ color: '#C9A84C', fontSize: 10, letterSpacing: '0.22em', fontWeight: 700 }}>IST</span>
          <span className="tabular-nums" style={{ color: '#F5F0E8', fontSize: 12, fontWeight: 500 }}>
            {formatIST(time)}
          </span>
        </div>
      </div>

      {/* Right: DB Status + Last Refresh */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5" data-testid="db-status">
          <Database className="w-3.5 h-3.5" style={{ color: 'rgba(201, 168, 76, 0.85)' }} />
          <span
            className="gold-pulse-dot"
            style={{
              width: 7, height: 7, borderRadius: '50%',
              backgroundColor: isConnected ? '#5EBE92' : '#E05252',
            }}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <span
          className="tabular-nums"
          style={{
            color: 'rgba(245, 240, 232, 0.55)',
            fontSize: 10.5,
            letterSpacing: '0.06em',
          }}
          data-testid="last-refresh"
        >
          Last refresh {formatIST(lastRefresh)}
        </span>
      </div>
    </header>
  );
};
