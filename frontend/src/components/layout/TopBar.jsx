import { useState, useEffect } from 'react';
import { apiGet, API_ENDPOINTS } from '@/services/api';

const BEAVER_LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-review-38/artifacts/tqw73ol3_Screenshot%202026-04-16%20at%206.20.25%E2%80%AFPM.png';

const IndexChip = ({ label, value, changePct }) => {
  const val =
    typeof value === 'number'
      ? value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
      : '—';
  const hasChange = typeof changePct === 'number';
  const isPos = hasChange && changePct >= 0;
  return (
    <div
      className="flex items-center gap-2 px-3 py-1 rounded-md tabular-nums"
      style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}
    >
      <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11, fontWeight: 500, letterSpacing: '0.06em' }}>
        {label}
      </span>
      <span style={{ color: '#FFFFFF', fontSize: 12.5, fontWeight: 600 }}>{val}</span>
      {hasChange && (
        <span style={{ color: isPos ? '#6FD19B' : '#F1867F', fontSize: 11, fontWeight: 600 }}>
          {isPos ? '▲' : '▼'} {Math.abs(changePct).toFixed(2)}%
        </span>
      )}
    </div>
  );
};

export const TopBar = ({ currentPage, onNavigate }) => {
  const [time, setTime] = useState(new Date());
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [indices, setIndices] = useState({
    niftyValue: null, niftyChangePct: null,
    sensexValue: null, sensexChangePct: null,
  });

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchIdx = async () => {
      try {
        const data = await apiGet(API_ENDPOINTS.marketOverview);
        if (cancelled) return;
        const nifty = data?.nifty || data?.nifty50 || data?.NIFTY50 || {};
        const sensex = data?.sensex || data?.SENSEX || {};
        setIndices({
          niftyValue: data?.nifty_value ?? nifty.value ?? null,
          niftyChangePct: data?.nifty_change_percent ?? nifty.change_percent ?? null,
          sensexValue: data?.sensex_value ?? sensex.value ?? null,
          sensexChangePct: data?.sensex_change_percent ?? sensex.change_percent ?? null,
        });
        setLastRefresh(new Date());
      } catch (e) { /* silent */ }
    };
    fetchIdx();
    const t = setInterval(fetchIdx, 60000);
    return () => { cancelled = true; clearInterval(t); };
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
        backgroundColor: '#0F3D2E',
        borderBottom: '1px solid #0F3D2E',
      }}
      data-testid="top-bar"
    >
      {/* Left: logo + wordmark + nav */}
      <div className="flex items-center gap-5">
        <button
          onClick={() => onNavigate?.('/')}
          className="flex items-center gap-3"
          style={{ background: 'transparent', cursor: 'pointer' }}
          data-testid="topbar-home"
        >
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
        </button>
        <nav className="flex items-center gap-4" style={{ marginLeft: 8 }}>
          {[
            { label: 'MARKET', path: '/' },
            { label: 'RESEARCH', path: '/research' },
          ].map((item) => {
            const active = currentPage === item.path;
            return (
              <button
                key={item.path}
                onClick={() => onNavigate?.(item.path)}
                style={{
                  background: 'transparent',
                  color: active ? '#FFFFFF' : 'rgba(255,255,255,0.65)',
                  fontSize: 13, fontWeight: 500, letterSpacing: '0.08em',
                  padding: '4px 2px',
                  borderBottom: active ? '2px solid #FFFFFF' : '2px solid transparent',
                  cursor: 'pointer',
                }}
                data-testid={`topbar-nav-${item.label.toLowerCase()}`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Center: index chips */}
      <div className="flex items-center gap-3">
        <IndexChip label="NIFTY 50" value={indices.niftyValue} changePct={indices.niftyChangePct} />
        <IndexChip label="SENSEX"   value={indices.sensexValue} changePct={indices.sensexChangePct} />
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
