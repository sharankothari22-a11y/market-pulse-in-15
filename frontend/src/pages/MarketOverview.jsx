import { useState, useEffect, useRef } from 'react';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { Loader2, Search, BarChart2 } from 'lucide-react';
import { validateTicker } from '@/lib/ticker';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, ReferenceLine,
} from 'recharts';

// ─── helpers ────────────────────────────────────────────────────────────────
const formatPercent = (value) => {
  if (value == null) return null;
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
};

const COMMODITY_LABELS = {
  'GC=F': { name: 'Gold',              venue: 'COMEX' },
  'SI=F': { name: 'Silver',            venue: 'COMEX' },
  'CL=F': { name: 'Crude oil · WTI',   venue: 'NYMEX' },
  'BZ=F': { name: 'Crude oil · Brent', venue: 'ICE'   },
};

const transformCommodities = (commodities = []) =>
  commodities.map((item, idx) => {
    const symbol = item.symbol || item.name || 'UNKNOWN';
    const known = COMMODITY_LABELS[symbol];
    const currency = item.currency === 'INR' ? '₹' : '$';
    const price = parseFloat(item.price ?? item.current_price);
    const pct = parseFloat(item.change_24h ?? item.change_pct ?? item.change_percent);
    return {
      id: symbol || idx,
      name: known?.name || symbol,
      venue: known?.venue || '',
      symbol,
      value: isNaN(price) ? 'N/A'
        : `${currency}${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      change: isNaN(pct) ? null : `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`,
      positive: !isNaN(pct) && pct >= 0,
    };
  });

const transformFxRates = (fx = {}) => {
  const rates = [];
  Object.entries(fx).forEach(([pair, data]) => {
    if (data && typeof data === 'object') {
      const pct = parseFloat(data.change_percent ?? data.change);
      rates.push({
        id: pair,
        label: pair.toUpperCase(),
        value: typeof data.rate === 'number' ? data.rate.toFixed(4) : (data.rate || 'N/A'),
        changeNum: isNaN(pct) ? null : pct,
      });
    } else if (typeof data === 'number') {
      rates.push({ id: pair, label: pair.toUpperCase(), value: data.toFixed(4), changeNum: null });
    }
  });
  return rates;
};

const transformFiiDii = (fiiDii = []) => {
  if (Array.isArray(fiiDii) && fiiDii.length > 0) {
    const latest = fiiDii[0];
    const fiiRaw = latest.fii_net ?? latest.fii ?? latest.FII;
    const diiRaw = latest.dii_net ?? latest.dii ?? latest.DII;
    return {
      fiiCr: typeof fiiRaw === 'number' ? fiiRaw / 100 : null,
      diiCr: typeof diiRaw === 'number' ? diiRaw / 100 : null,
      date: latest.date || latest.trade_date || '',
    };
  }
  return { fiiCr: null, diiCr: null, date: '' };
};

const transformFiiDiiChart = (fiiDii = []) => {
  if (!Array.isArray(fiiDii) || fiiDii.length === 0) return [];
  return fiiDii.slice(0, 7).reverse().map((row) => {
    const fii = row.fii_net ?? row.fii ?? row.FII ?? 0;
    const dii = row.dii_net ?? row.dii ?? row.DII ?? 0;
    const date = row.date || row.trade_date || '';
    let short = date;
    try {
      const d = new Date(date);
      if (!isNaN(d)) short = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
    } catch (_) {}
    return {
      date: short,
      FII: typeof fii === 'number' ? +(fii / 100).toFixed(0) : 0,
      DII: typeof dii === 'number' ? +(dii / 100).toFixed(0) : 0,
    };
  });
};

const transformTopMovers = (movers = []) =>
  movers.map((item, idx) => {
    const pct = parseFloat(item.change_percent ?? item.change ?? item.pct_change ?? 0);
    const ltp = parseFloat(item.ltp ?? item.price ?? item.last_price);
    return {
      id: item.symbol || idx,
      symbol: item.symbol || item.ticker || 'N/A',
      ltp: isNaN(ltp) ? (item.ltp ?? 'N/A')
           : ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 }),
      pct: isNaN(pct) ? null : pct,
      volume: item.volume ? `${(item.volume / 1e6).toFixed(1)}M` : '—',
    };
  });

// ─── section heading ────────────────────────────────────────────────────────
const SectionHeading = ({ children, right }) => (
  <div className="flex items-end justify-between mb-3">
    <h2 style={{
      color: 'var(--bi-text-secondary)',
      fontSize: 14, fontWeight: 500,
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
    }}>
      {children}
    </h2>
    {right}
  </div>
);

// ─── Hero: ticker input ─────────────────────────────────────────────────────
const TickerHero = ({ onAnalyze }) => {
  const [value, setValue] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const errorTimerRef = useRef(null);
  const suggestions = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'BHARTIARTL'];

  const flashError = (msg) => {
    setErrorMsg(msg);
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    errorTimerRef.current = setTimeout(() => setErrorMsg(''), 4000);
  };

  const submit = (t) => {
    const raw = t ?? value;
    const { ok, value: cleaned, error } = validateTicker(raw);
    if (!ok) { flashError(error); return; }
    setErrorMsg('');
    setAnalyzing(true);
    try { onAnalyze?.(cleaned); } finally {
      setTimeout(() => setAnalyzing(false), 600);
    }
  };

  return (
    <section
      className="w-full flex flex-col items-center text-center"
      style={{ padding: '48px 24px' }}
      data-testid="home-ticker-hero"
    >
      <h1 className="font-serif-display" style={{
        fontSize: 32, fontWeight: 500, color: 'var(--bi-text-primary)',
        lineHeight: 1.2, margin: 0,
      }}>
        Equity research. On demand.
      </h1>
      <div style={{ marginTop: 12, maxWidth: 560 }}>
        <span style={{
          display: 'block',
          fontSize: 16, lineHeight: 1.5, color: '#0F3D2E',
        }}>
          Type any Indian stock.
        </span>
        <span style={{
          display: 'block',
          marginTop: 6,
          fontSize: 14, letterSpacing: '0.02em',
          color: '#0F3D2E',
        }}>
          DCF valuation · Scoring · SWOT · Porter's analysis
        </span>
      </div>

      <div className="flex items-stretch gap-2" style={{ marginTop: 24 }}>
        <div className="relative" style={{ width: 480 }}>
          <Search
            size={18}
            style={{
              position: 'absolute', left: 14, top: '50%',
              transform: 'translateY(-50%)', color: 'var(--bi-text-tertiary)',
            }}
          />
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder="Enter a ticker (RELIANCE, TCS, HDFCBANK...)"
            style={{
              width: '100%', height: 56,
              paddingLeft: 42, paddingRight: 16,
              borderRadius: 8,
              border: '1px solid var(--bi-border-subtle)',
              backgroundColor: 'var(--bi-bg-card)',
              color: 'var(--bi-text-primary)',
              fontSize: 15,
            }}
            data-testid="home-ticker-input"
          />
        </div>
        <button
          onClick={() => submit()}
          disabled={!value.trim() || analyzing}
          style={{
            height: 56, padding: '0 24px',
            borderRadius: 8,
            backgroundColor: '#0F3D2E',
            color: 'var(--bi-text-inverse)',
            fontSize: 16, fontWeight: 600,
            opacity: value.trim() && !analyzing ? 1 : 0.5,
            cursor: analyzing ? 'not-allowed' : 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 8,
          }}
          data-testid="home-analyze-btn"
        >
          {analyzing && <Loader2 size={16} className="animate-spin" />}
          {analyzing ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      <div
        aria-live="polite"
        style={{
          minHeight: 18, marginTop: 8,
          fontSize: 13, color: '#DC2626',
          opacity: errorMsg ? 1 : 0,
          transition: 'opacity 400ms ease-out',
        }}
        data-testid="home-ticker-error"
      >
        {errorMsg || ' '}
      </div>

      <div className="flex items-center justify-center flex-wrap gap-2" style={{ marginTop: 16 }}>
        <span style={{ color: 'var(--bi-text-tertiary)', fontSize: 13 }}>Try:</span>
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => submit(s)}
            style={{
              padding: '4px 12px', borderRadius: 6,
              backgroundColor: 'var(--bi-bg-subtle)',
              color: 'var(--bi-text-primary)',
              fontSize: 13, fontWeight: 500,
              border: '1px solid var(--bi-border-subtle)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bi-navy-100)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'var(--bi-bg-subtle)'; }}
            data-testid={`home-suggest-${s}`}
          >
            {s}
          </button>
        ))}
      </div>
    </section>
  );
};

// ─── Status strip ───────────────────────────────────────────────────────────
const StatusStrip = ({ lastRefresh }) => {
  const time = lastRefresh?.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });
  return (
    <div
      className="flex items-center justify-between"
      style={{
        height: 32,
        padding: '0 16px',
        backgroundColor: 'var(--bi-bg-subtle)',
        borderRadius: 8,
      }}
      data-testid="status-strip"
    >
      <div className="flex items-center gap-2">
        <span className="bi-pulse-dot"
              style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: 'var(--bi-success-fg)' }} />
        <span style={{ fontSize: 12, color: 'var(--bi-text-secondary)' }}>
          NSE open <span style={{ color: 'var(--bi-text-tertiary)' }}>·</span> 09:15 – 15:30 IST
        </span>
      </div>
      {time && (
        <span style={{ fontSize: 12, color: 'var(--bi-text-tertiary)' }} className="tabular-nums">
          Last refresh {time}
        </span>
      )}
    </div>
  );
};

// ─── FX card (compact) ──────────────────────────────────────────────────────
const FxCard = ({ label, value, changeNum }) => {
  const hasChange = changeNum != null && changeNum !== 0;
  const pos = (changeNum ?? 0) >= 0;
  return (
    <div style={{
      backgroundColor: 'var(--bi-bg-card)',
      border: '1px solid var(--bi-border-subtle)',
      borderRadius: 12,
      padding: '16px 18px',
      boxShadow: 'var(--bi-shadow-card)',
    }}>
      <p style={{
        color: 'var(--bi-text-tertiary)',
        fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
        letterSpacing: '0.06em', margin: 0, marginBottom: 6,
      }}>
        {label}
      </p>
      <p className="tabular-nums" style={{
        color: 'var(--bi-text-primary)', fontSize: 20, fontWeight: 600,
        margin: 0, lineHeight: 1.1,
      }}>
        {value}
      </p>
      <div style={{ marginTop: 6, fontSize: 12 }}>
        {hasChange ? (
          <span className="tabular-nums" style={{
            color: pos ? 'var(--bi-success-fg)' : 'var(--bi-danger-fg)', fontWeight: 600,
          }}>
            {pos ? '▲' : '▼'} {`${pos ? '+' : ''}${changeNum.toFixed(2)}%`}
          </span>
        ) : (
          <span style={{ color: 'var(--bi-text-tertiary)' }}>—</span>
        )}
      </div>
    </div>
  );
};

// ─── Commodity card ─────────────────────────────────────────────────────────
const CommodityCard = ({ name, venue, symbol, value, change, positive }) => (
  <div style={{
    backgroundColor: 'var(--bi-bg-card)',
    border: '1px solid var(--bi-border-subtle)',
    borderRadius: 12,
    padding: '16px 18px',
    boxShadow: 'var(--bi-shadow-card)',
  }}>
    <p style={{ color: 'var(--bi-text-primary)', fontSize: 16, fontWeight: 500, margin: 0 }}>
      {name}
    </p>
    <p style={{
      color: 'var(--bi-text-tertiary)',
      fontSize: 11, fontWeight: 500, textTransform: 'uppercase',
      letterSpacing: '0.04em', margin: '2px 0 10px',
    }}>
      {venue}{venue && ' · '}{symbol}
    </p>
    <p className="tabular-nums" style={{
      color: 'var(--bi-text-primary)', fontSize: 20, fontWeight: 600,
      margin: 0, lineHeight: 1.1,
    }}>
      {value}
    </p>
    <div style={{ marginTop: 6, fontSize: 12 }}>
      {change ? (
        <span className="tabular-nums" style={{
          color: positive ? 'var(--bi-success-fg)' : 'var(--bi-danger-fg)', fontWeight: 600,
        }}>
          {positive ? '▲' : '▼'} {change}
        </span>
      ) : (
        <span style={{ color: 'var(--bi-text-tertiary)' }}>—</span>
      )}
    </div>
  </div>
);

// ─── FII/DII chart ──────────────────────────────────────────────────────────
const FiiDiiBarChart = ({ data }) => {
  const hasRealData = data && data.length > 0 && data.some((d) => d.FII !== 0 || d.DII !== 0);
  if (!hasRealData) {
    return (
      <div className="flex flex-col items-center justify-center text-center"
           style={{ height: 200, padding: 16, gap: 8 }}>
        <BarChart2 size={36} style={{ color: 'var(--bi-text-tertiary)' }} />
        <p style={{ color: 'var(--bi-text-secondary)', fontSize: 14, margin: 0 }}>
          No flow data today
        </p>
        <p style={{ color: 'var(--bi-text-tertiary)', fontSize: 12, margin: 0 }}>
          Institutional flows update after market close
        </p>
      </div>
    );
  }

  const TooltipBox = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{
        backgroundColor: 'var(--bi-bg-card)',
        border: '1px solid var(--bi-border-subtle)',
        boxShadow: 'var(--bi-shadow-card)',
        padding: '8px 10px', fontSize: 12, borderRadius: 6,
      }}>
        <div style={{ color: 'var(--bi-text-primary)', marginBottom: 4, fontWeight: 600 }}>{label}</div>
        {payload.map((p) => (
          <div key={p.dataKey} className="tabular-nums" style={{ color: 'var(--bi-text-primary)' }}>
            <span style={{
              display: 'inline-block', width: 8, height: 8, marginRight: 6,
              backgroundColor: p.color, borderRadius: 2,
            }} />
            {p.dataKey}: ₹{p.value.toLocaleString('en-IN')} Cr
          </div>
        ))}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 6, left: 0, bottom: 4 }}>
        <CartesianGrid stroke="var(--bi-border-subtle)" vertical={false} />
        <XAxis dataKey="date"
               tick={{ fill: 'var(--bi-text-tertiary)', fontSize: 11 }}
               axisLine={{ stroke: 'var(--bi-border-subtle)' }} tickLine={false} />
        <YAxis tick={{ fill: 'var(--bi-text-tertiary)', fontSize: 11 }}
               axisLine={false} tickLine={false} width={40} />
        <ReferenceLine y={0} stroke="var(--bi-border-strong)" />
        <Tooltip content={<TooltipBox />} cursor={{ fill: 'rgba(27,58,107,0.05)' }} />
        <Legend wrapperStyle={{ fontSize: 11, color: 'var(--bi-text-secondary)', paddingTop: 4 }}
                iconType="square" iconSize={8} />
        <Bar dataKey="FII" fill="var(--bi-navy-700)" maxBarSize={22} radius={[2, 2, 0, 0]} />
        <Bar dataKey="DII" fill="var(--bi-tile-ochre-fg)" maxBarSize={22} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
};

// ─── FII/DII net tile ───────────────────────────────────────────────────────
const FiiDiiNetTile = ({ label, valueCr }) => {
  const isZeroOrMissing = valueCr == null || valueCr === 0;
  if (isZeroOrMissing) {
    return (
      <div style={{ padding: '10px 12px', borderRadius: 8, backgroundColor: 'var(--bi-bg-subtle)' }}>
        <p style={{
          color: 'var(--bi-text-tertiary)', fontSize: 11, fontWeight: 500,
          textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0,
        }}>{label}</p>
        <p style={{ color: 'var(--bi-text-tertiary)', fontSize: 14, margin: '4px 0 0' }}>
          Not yet reported
        </p>
      </div>
    );
  }
  const pos = valueCr >= 0;
  return (
    <div style={{ padding: '10px 12px', borderRadius: 8, backgroundColor: 'var(--bi-bg-subtle)' }}>
      <p style={{
        color: 'var(--bi-text-tertiary)', fontSize: 11, fontWeight: 500,
        textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0,
      }}>{label}</p>
      <p className="tabular-nums" style={{
        color: pos ? 'var(--bi-success-fg)' : 'var(--bi-danger-fg)',
        fontSize: 16, fontWeight: 600, margin: '4px 0 0',
      }}>
        ₹{Math.round(valueCr).toLocaleString('en-IN')} Cr
      </p>
    </div>
  );
};

// ─── Top Movers table ───────────────────────────────────────────────────────
const TopMoversTable = ({ rows }) => {
  if (!rows.length) {
    return (
      <div className="text-center" style={{ padding: 24, color: 'var(--bi-text-tertiary)', fontSize: 13 }}>
        No stock data available yet
      </div>
    );
  }
  return (
    <div style={{ overflow: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {['Symbol', 'LTP', 'Change', 'Volume'].map((h, i) => (
              <th key={h}
                  style={{
                    textAlign: i === 0 ? 'left' : 'right',
                    padding: '8px 12px',
                    fontSize: 11, fontWeight: 500,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--bi-text-secondary)',
                    borderBottom: '1px solid var(--bi-border-subtle)',
                  }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const pos = (r.pct ?? 0) >= 0;
            const rowBg = idx % 2 === 0 ? 'var(--bi-bg-card)' : 'var(--bi-bg-subtle)';
            return (
              <tr key={r.id}
                  style={{ backgroundColor: rowBg, height: 44, transition: 'background-color 0.15s' }}
                  onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bi-navy-100)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = rowBg; }}
              >
                <td style={{
                  padding: '0 12px',
                  fontSize: 13, fontWeight: 600,
                  color: 'var(--bi-navy-900)',
                }}>
                  {r.symbol}
                </td>
                <td className="tabular-nums"
                    style={{ padding: '0 12px', textAlign: 'right',
                             fontSize: 13, color: 'var(--bi-text-primary)' }}>
                  {r.ltp}
                </td>
                <td style={{ padding: '0 12px', textAlign: 'right' }}>
                  {r.pct == null ? (
                    <span style={{ color: 'var(--bi-text-tertiary)' }}>—</span>
                  ) : (
                    <span className="tabular-nums"
                          style={{
                            display: 'inline-block',
                            padding: '2px 8px', borderRadius: 4,
                            backgroundColor: pos ? 'rgba(15,122,62,0.08)' : 'rgba(199,55,47,0.08)',
                            color: pos ? 'var(--bi-success-fg)' : 'var(--bi-danger-fg)',
                            fontSize: 12, fontWeight: 600,
                          }}>
                      {pos ? '▲' : '▼'} {pos ? '+' : ''}{r.pct.toFixed(2)}%
                    </span>
                  )}
                </td>
                <td className="tabular-nums"
                    style={{ padding: '0 12px', textAlign: 'right',
                             fontSize: 13, color: 'var(--bi-text-secondary)' }}>
                  {r.volume}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// ─── main ───────────────────────────────────────────────────────────────────
export const MarketOverview = ({ onAnalyzeTicker }) => {
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        setLoading(true);
        const market = await apiGet(API_ENDPOINTS.marketOverview);
        setMarketData(market);
        setLastRefresh(new Date());
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Failed to fetch market data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !marketData) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 400 }}
           data-testid="market-overview-loading">
        <div className="flex items-center gap-3" style={{ color: 'var(--bi-text-secondary)' }}>
          <Loader2 className="w-5 h-5 animate-spin" />
          <span style={{ fontSize: 13 }}>Loading market data…</span>
        </div>
      </div>
    );
  }

  if (error && !marketData) {
    return (
      <div className="text-center" style={{ padding: 48 }} data-testid="market-overview-error">
        <p style={{ color: 'var(--bi-danger-fg)', marginBottom: 8, fontSize: 14, fontWeight: 600 }}>
          Failed to load market data
        </p>
        <p style={{ color: 'var(--bi-text-secondary)', fontSize: 13 }}>{error}</p>
      </div>
    );
  }

  const commodities = transformCommodities([
    ...(marketData?.commodities || []),
  ]).slice(0, 4);
  const fxRates     = transformFxRates(marketData?.fx || {}).slice(0, 5);
  const fiiDii      = transformFiiDii(marketData?.fii_dii || []);
  const fiiDiiChart = transformFiiDiiChart(marketData?.fii_dii || []);
  const topMovers   = transformTopMovers(marketData?.top_movers || []).slice(0, 10);

  return (
    <div data-testid="market-overview-page">
      <TickerHero onAnalyze={onAnalyzeTicker} />

      <div style={{ paddingTop: 16 }} className="flex flex-col" >
        <StatusStrip lastRefresh={lastRefresh} />

        <div style={{ height: 24 }} />

        {/* FX rates */}
        <section data-testid="fx-rates-section">
          <SectionHeading>FX rates</SectionHeading>
          <div className="grid grid-cols-5 gap-3">
            {fxRates.length > 0 ? (
              fxRates.map((r) => <FxCard key={r.id} {...r} />)
            ) : (
              <p className="col-span-5 text-center"
                 style={{ color: 'var(--bi-text-tertiary)', fontSize: 13, padding: 12 }}>
                No FX data available
              </p>
            )}
          </div>
        </section>

        <div style={{ height: 24 }} />

        {/* Top Movers + FII/DII */}
        <section className="grid grid-cols-3 gap-5" data-testid="movers-fii-section">
          <div className="col-span-2" style={{
            backgroundColor: 'var(--bi-bg-card)',
            border: '1px solid var(--bi-border-subtle)',
            borderRadius: 12,
            boxShadow: 'var(--bi-shadow-card)',
            padding: 24,
          }}>
            <SectionHeading
              right={
                <span style={{
                  padding: '3px 10px', borderRadius: 999,
                  backgroundColor: 'var(--bi-bg-subtle)',
                  color: 'var(--bi-text-secondary)',
                  fontSize: 11, fontWeight: 500,
                }}>
                  NSE · Top {topMovers.length}
                </span>
              }
            >
              Top movers
            </SectionHeading>
            <TopMoversTable rows={topMovers} />
          </div>

          <div style={{
            backgroundColor: 'var(--bi-bg-card)',
            border: '1px solid var(--bi-border-subtle)',
            borderRadius: 12,
            boxShadow: 'var(--bi-shadow-card)',
            padding: 20,
          }}>
            <SectionHeading>FII / DII flow</SectionHeading>
            <FiiDiiBarChart data={fiiDiiChart} />
            <div className="grid grid-cols-2 gap-3" style={{ marginTop: 12 }}>
              <FiiDiiNetTile label="FII net" valueCr={fiiDii.fiiCr} />
              <FiiDiiNetTile label="DII net" valueCr={fiiDii.diiCr} />
            </div>
            {fiiDii.date && (
              <p className="text-center" style={{
                color: 'var(--bi-text-tertiary)', fontSize: 11, margin: '12px 0 0',
              }}>
                As of {fiiDii.date}
              </p>
            )}
          </div>
        </section>

        <div style={{ height: 24 }} />

        {/* Commodities */}
        <section data-testid="commodities-section">
          <SectionHeading>Commodities</SectionHeading>
          <div className="grid grid-cols-4 gap-3">
            {commodities.length > 0 ? (
              commodities.map((c) => <CommodityCard key={c.id} {...c} />)
            ) : (
              <p className="col-span-4 text-center"
                 style={{ color: 'var(--bi-text-tertiary)', fontSize: 13, padding: 12 }}>
                No commodity data available
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default MarketOverview;
