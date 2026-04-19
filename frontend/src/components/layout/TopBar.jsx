import { useState, useEffect } from 'react';
import { apiGet, API_ENDPOINTS } from '@/services/api';

const BEAVER_LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-review-38/artifacts/tqw73ol3_Screenshot%202026-04-16%20at%206.20.25%E2%80%AFPM.png';

const findIndicator = (arr, id) => (arr || []).find(i => i.id === id);

const IndexChip = ({ label, data }) => {
  const val =
    data && typeof data.raw_value === 'number'
      ? data.raw_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
      : data?.value ?? '—';
  const isPos = data?.changeType === 'positive';
  return (
    <div
      className="flex items-center gap-2 px-3 py-1 rounded-md tabular-nums"
      style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}
    >
      <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11, fontWeight: 500, letterSpacing: '0.06em' }}>
        {label}
      </span>
      <span style={{ color: '#FFFFFF', fontSize: 12.5, fontWeight: 600 }}>{val}</span>
      {data?.change && (
        <span style={{ color: isPos ? '#6FD19B' : '#F1867F', fontSize: 11, fontWeight: 600 }}>
          {isPos ? '▲' : '▼'} {data.change}
        </span>
      )}
    </div>
  );
};

export const TopBar = () => {
  const [time, setTime] = useState(new Date());
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [indices, setIndices] = useState({ nifty: null, sensex: null });

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchIdx = async () => {
      try {
        const data = await apiGet(API_ENDPOINTS.macro);
        setIndices({
          nifty: findIndicator(data?.indicators, '^NSEI'),
          sensex: findIndicator(data?.indicators, '^BSESN'),
        });
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
  const formatISTHM = (date) =>
    date.toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit', minute: '2-digit', hour12: false,
    });

  return (
    <header
      className="flex items-center justify-between px-5"
      style={{
        height: 64,
        backgroundColor: 'var(--bi-navy-900)',
        borderBottom: '1px solid var(--bi-navy-700)',
      }}
      data-testid="top-bar"
    >
      {/* Left: logo + wordmark */}
      <div className="flex items-center gap-3">
        <div
          style={{
            width: 36, height: 36, borderRadius: 8, overflow: 'hidden',
            backgroundColor: 'var(--bi-navy-700)',
          }}
        >
          <img src={BEAVER_LOGO_URL} alt="Beaver"
               style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <span style={{
          color: 'var(--bi-text-inverse)',
          fontSize: 14, fontWeight: 600, letterSpacing: '0.08em',
        }}>
          BEAVER INTELLIGENCE
        </span>
      </div>

      {/* Center: index chips */}
      <div className="flex items-center gap-3">
        <IndexChip label="NIFTY 50" data={indices.nifty} />
        <IndexChip label="SENSEX"   data={indices.sensex} />
      </div>

      {/* Right: clock + refresh + pulse */}
      <div className="flex items-center gap-4">
        <span className="tabular-nums"
              style={{ color: 'var(--bi-text-inverse)', fontSize: 12.5, fontWeight: 500 }}>
          IST {formatIST(time)}
        </span>
        <span className="tabular-nums"
              style={{ color: 'rgba(255,255,255,0.6)', fontSize: 11.5 }}
              data-testid="last-refresh">
          Last refresh {formatISTHM(lastRefresh)}
        </span>
        <span
          className="bi-pulse-dot"
          style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#6FD19B' }}
          title="Connected"
        />
      </div>
    </header>
  );
};
