import { useState, useEffect } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { DataTable } from '@/components/ui/DataTable';
import { SignalFeedItem } from '@/components/ui/SignalFeedItem';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { Loader2, TrendingUp, TrendingDown } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, ReferenceLine,
} from 'recharts';
import { cn } from '@/lib/utils';

// ─── column definitions ──────────────────────────────────────────────────────
const topMoversColumns = [
  { header: 'Symbol', accessor: 'symbol',
    render: (row) => (
      <span style={{ color: '#0A1628', fontWeight: 700, letterSpacing: '0.02em' }}>{row.symbol}</span>
    ) },
  { header: 'LTP', accessor: 'ltp',
    render: (row) => (
      <span className="tabular-nums" style={{ color: '#0A1628', fontWeight: 500 }}>
        {typeof row.ltp === 'number' ? row.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : row.ltp}
      </span>
    ) },
  {
    header: 'Change',
    accessor: 'change',
    render: (row) => {
      const changeValue = row.change_percent ?? row.change;
      const num = parseFloat(changeValue);
      const isPositive = num >= 0;
      const color = isPositive ? '#2D6A4F' : '#E05252';
      const arrow = isPositive ? '▲' : '▼';
      if (isNaN(num)) {
        return <span style={{ color: 'rgba(10, 22, 40, 0.5)' }}>{changeValue ?? '—'}</span>;
      }
      return (
        <span className="tabular-nums" style={{ color, fontWeight: 700 }}>
          {arrow} {isPositive ? '+' : ''}{num.toFixed(2)}%
        </span>
      );
    }
  },
  { header: 'Volume', accessor: 'volume',
    render: (row) => (
      <span className="tabular-nums" style={{ color: 'rgba(10, 22, 40, 0.6)' }}>{row.volume}</span>
    ) },
];

// ─── data helpers ────────────────────────────────────────────────────────────
const formatCurrency = (value, currency = 'USD') => {
  if (value == null) return 'N/A';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  if (currency === 'INR') {
    return `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatPercent = (value) => {
  if (value == null) return null;
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
};

const transformCommodities = (commodities = []) =>
  commodities.map((item, idx) => ({
    id: item.symbol || item.id || idx,
    title: item.symbol || item.name || 'Unknown',
    value: formatCurrency(item.price || item.current_price, item.currency === 'INR' ? 'INR' : 'USD'),
    change: formatPercent(item.change_24h ?? item.change_pct ?? item.change_percent) || '—',
    changeType: parseFloat(item.change_24h ?? item.change_pct ?? item.change_percent ?? 0) >= 0 ? 'positive' : 'negative',
    subtitle: item.unit || item.market_cap_cr ? `MCap ₹${item.market_cap_cr}Cr` : '',
  }));

const transformFxRates = (fx = {}) => {
  const rates = [];
  Object.entries(fx).forEach(([pair, data]) => {
    if (data && typeof data === 'object') {
      rates.push({
        id: pair,
        title: pair.toUpperCase(),
        value: typeof data.rate === 'number' ? data.rate.toFixed(4) : data.rate || 'N/A',
        change: formatPercent(data.change_percent || data.change) || '—',
        changeType: parseFloat(data.change_percent || data.change || 0) >= 0 ? 'positive' : 'negative',
        subtitle: data.source || '',
      });
    } else if (typeof data === 'number') {
      rates.push({
        id: pair,
        title: pair.toUpperCase(),
        value: data.toFixed(4),
        change: '—',
        changeType: 'neutral',
        subtitle: '',
      });
    }
  });
  return rates;
};

const transformFiiDii = (fiiDii = []) => {
  if (Array.isArray(fiiDii) && fiiDii.length > 0) {
    const latest = fiiDii[0];
    const fiiNet = latest.fii_net || latest.fii || latest.FII || 0;
    const diiNet = latest.dii_net || latest.dii || latest.DII || 0;
    return {
      fii:  typeof fiiNet === 'number' ? `₹${(fiiNet / 100).toFixed(0)} Cr` : fiiNet,
      dii:  typeof diiNet === 'number' ? `₹${(diiNet / 100).toFixed(0)} Cr` : diiNet,
      date: latest.date || latest.trade_date || '',
      data: fiiDii,
    };
  }
  return { fii: '-', dii: '-', data: [] };
};

const transformFiiDiiChart = (fiiDii = []) => {
  if (!Array.isArray(fiiDii) || fiiDii.length === 0) return [];
  return fiiDii.slice(0, 7).reverse().map((row) => {
    const fii = row.fii_net ?? row.fii ?? row.FII ?? 0;
    const dii = row.dii_net ?? row.dii ?? row.DII ?? 0;
    const date = row.date || row.trade_date || '';
    // shorten date like "2026-04-15" → "Apr 15"
    let short = date;
    try {
      const d = new Date(date);
      if (!isNaN(d)) short = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
    } catch (_) {}
    return {
      date: short,
      FII: typeof fii === 'number' ? +(fii / 100).toFixed(0) : 0,  // to Crores
      DII: typeof dii === 'number' ? +(dii / 100).toFixed(0) : 0,
    };
  });
};

const transformNews = (news = []) =>
  news.map((item, idx) => ({
    id: item.id || idx,
    title: item.title || item.headline || 'No title',
    timestamp: item.published_at || item.timestamp || item.date || 'Recent',
    severity: item.sentiment === 'positive' ? 'positive'
            : item.sentiment === 'negative' ? 'danger'
            : 'info',
    sector: item.category || item.sector || item.source || 'General',
    signalType: item.type || 'News',
  }));

const transformTopMovers = (movers = []) =>
  movers.map((item, idx) => ({
    id: item.symbol || idx,
    symbol: item.symbol || item.ticker || 'N/A',
    ltp: item.ltp || item.price || item.last_price || 'N/A',
    change: item.change_percent || item.change || item.pct_change || 0,
    change_percent: item.change_percent || item.pct_change,
    changeType: parseFloat(item.change_percent || item.change || 0) >= 0 ? 'positive' : 'negative',
    volume: item.volume ? `${(item.volume / 1e6).toFixed(1)}M` : 'N/A',
  }));

// ─── Hero strip ──────────────────────────────────────────────────────────────
const HeroStrip = ({ macroIndicators = [], fx = {} }) => {
  const find = (id) => macroIndicators.find((i) => i.id === id);
  const nifty  = find('^NSEI');
  const sensex = find('^BSESN');
  const usdInr = fx?.USD;

  const Stat = ({ label, value, change, positive }) => (
    <div className="flex items-center gap-2">
      <span style={{ color: 'rgba(245, 240, 232, 0.85)', fontSize: 10.5, letterSpacing: '0.22em', fontWeight: 600 }}>
        {label}
      </span>
      <span className="tabular-nums" style={{ color: '#C9A84C', fontSize: 13, fontWeight: 700 }}>
        {value}
      </span>
      {change != null && (
        <span
          className="tabular-nums"
          style={{
            color: positive ? '#5EBE92' : '#FF7676',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          {positive ? '▲' : '▼'} {change}
        </span>
      )}
    </div>
  );

  const Divider = () => (
    <span style={{ color: 'rgba(201, 168, 76, 0.5)', fontSize: 14, margin: '0 6px' }}>·</span>
  );

  return (
    <div
      className="w-full px-6 py-3 flex items-center gap-4 flex-wrap"
      style={{
        backgroundColor: '#1E3A5F',
        borderBottom: '1px solid rgba(201, 168, 76, 0.3)',
      }}
      data-testid="market-hero-strip"
    >
      <div className="flex items-center gap-2">
        <span
          className="gold-pulse-dot"
          style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: '#C9A84C' }}
        />
        <span style={{ color: '#C9A84C', fontSize: 10.5, letterSpacing: '0.28em', fontWeight: 700 }}>
          NSE
        </span>
        <span style={{ color: 'rgba(245, 240, 232, 0.95)', fontSize: 10.5, letterSpacing: '0.2em', fontWeight: 600 }}>
          OPEN
        </span>
      </div>

      <Divider />

      {nifty && (
        <Stat
          label="NIFTY 50"
          value={typeof nifty.raw_value === 'number' ? nifty.raw_value.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : nifty.value}
          change={nifty.change}
          positive={nifty.changeType === 'positive'}
        />
      )}

      {nifty && sensex && <Divider />}

      {sensex && (
        <Stat
          label="SENSEX"
          value={typeof sensex.raw_value === 'number' ? sensex.raw_value.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : sensex.value}
          change={sensex.change}
          positive={sensex.changeType === 'positive'}
        />
      )}

      {(nifty || sensex) && usdInr && <Divider />}

      {usdInr && (
        <Stat
          label="USD / INR"
          value={typeof usdInr.rate === 'number' ? (1 / usdInr.rate).toFixed(2) : usdInr.rate}
          change={usdInr.change_percent != null ? formatPercent(usdInr.change_percent) : null}
          positive={parseFloat(usdInr.change_percent || 0) >= 0}
        />
      )}

      <div className="ml-auto hidden md:flex items-center gap-2">
        <span style={{ color: 'rgba(245, 240, 232, 0.5)', fontSize: 10, letterSpacing: '0.15em' }}>
          SESSION
        </span>
        <span style={{ color: 'rgba(245, 240, 232, 0.85)', fontSize: 10.5, letterSpacing: '0.08em' }}>
          09:15 IST — 15:30 IST
        </span>
      </div>
    </div>
  );
};

// ─── FII / DII Bar Chart ─────────────────────────────────────────────────────
const FiiDiiBarChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40" style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 12 }}>
        No FII / DII data available
      </div>
    );
  }

  const TooltipBox = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid rgba(201, 168, 76, 0.45)',
        boxShadow: '0 4px 12px rgba(10, 22, 40, 0.12)',
        padding: '8px 10px',
        fontSize: 11.5,
      }}>
        <div style={{ color: '#0A1628', letterSpacing: '0.18em', marginBottom: 4, fontWeight: 700 }}>{label}</div>
        {payload.map((p) => (
          <div key={p.dataKey} className="tabular-nums" style={{ color: '#0A1628' }}>
            <span style={{
              display: 'inline-block', width: 8, height: 8, marginRight: 6,
              backgroundColor: p.color, borderRadius: 1,
            }} />
            {p.dataKey}: ₹{p.value.toLocaleString('en-IN')} Cr
          </div>
        ))}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 8, right: 6, left: 0, bottom: 4 }}>
        <CartesianGrid stroke="rgba(10, 22, 40, 0.06)" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: 'rgba(10, 22, 40, 0.65)', fontSize: 10, letterSpacing: '0.06em' }}
          axisLine={{ stroke: 'rgba(10, 22, 40, 0.2)' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: 'rgba(10, 22, 40, 0.5)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={38}
        />
        <ReferenceLine y={0} stroke="rgba(10, 22, 40, 0.25)" />
        <Tooltip content={<TooltipBox />} cursor={{ fill: 'rgba(201, 168, 76, 0.08)' }} />
        <Legend
          wrapperStyle={{ fontSize: 10, letterSpacing: '0.18em', color: '#0A1628', paddingTop: 4, fontWeight: 700 }}
          iconType="square"
          iconSize={8}
        />
        <Bar dataKey="FII" fill="#0A1628" maxBarSize={22} radius={[1, 1, 0, 0]} />
        <Bar dataKey="DII" fill="#C9A84C" maxBarSize={22} radius={[1, 1, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
};

// ─── Section heading ─────────────────────────────────────────────────────────
const SectionHeading = ({ children, right }) => (
  <div className="flex items-end justify-between mb-3">
    <h2
      className="label-spaced"
      style={{ color: '#0A1628' }}
    >
      {children}
    </h2>
    {right}
  </div>
);

// ─── Main component ─────────────────────────────────────────────────────────
export const MarketOverview = () => {
  const [marketData, setMarketData] = useState(null);
  const [macroData, setMacroData]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        setLoading(true);
        const [market, macro] = await Promise.all([
          apiGet(API_ENDPOINTS.marketOverview),
          apiGet(API_ENDPOINTS.macro).catch(() => null),
        ]);
        setMarketData(market);
        setMacroData(macro);
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
      <div className="page-content flex items-center justify-center" data-testid="market-overview-loading">
        <div className="flex items-center gap-3" style={{ color: 'rgba(10, 22, 40, 0.6)' }}>
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: '#C9A84C' }} />
          <span style={{ letterSpacing: '0.18em', fontSize: 11, fontWeight: 600 }}>LOADING MARKET DATA…</span>
        </div>
      </div>
    );
  }

  if (error && !marketData) {
    return (
      <div className="page-content flex items-center justify-center" data-testid="market-overview-error">
        <div className="text-center">
          <p style={{ color: '#E05252', marginBottom: 8, letterSpacing: '0.18em', fontSize: 12, fontWeight: 700 }}>
            FAILED TO LOAD MARKET DATA
          </p>
          <p style={{ color: 'rgba(10, 22, 40, 0.6)', fontSize: 12 }}>{error}</p>
        </div>
      </div>
    );
  }

  const commodities = transformCommodities([
    ...(marketData?.commodities || []),
    ...(marketData?.crypto || []).slice(0, 4),
  ]);
  const fxRates     = transformFxRates(marketData?.fx || {});
  const fiiDii      = transformFiiDii(marketData?.fii_dii || []);
  const fiiDiiChart = transformFiiDiiChart(marketData?.fii_dii || []);
  const news        = transformNews(marketData?.news || []);
  const topMovers   = transformTopMovers(marketData?.top_movers || []);

  // First 5 FX rates as hero ticker plus cards
  const fxCards = fxRates.slice(0, 5);

  return (
    <div
      className="page-content overflow-y-auto"
      style={{ height: 'calc(100vh - 48px)', backgroundColor: 'var(--bg-primary)' }}
      data-testid="market-overview-page"
    >
      {/* Hero strip */}
      <HeroStrip
        macroIndicators={macroData?.indicators || []}
        fx={marketData?.fx || {}}
      />

      <div className="p-6 space-y-6">

        {/* Row 1: FX Rates */}
        <section data-testid="fx-rates-section">
          <SectionHeading>FX RATES · SPOT</SectionHeading>
          <div className="grid grid-cols-5 gap-3">
            {fxCards.length > 0 ? (
              fxCards.map((item) => <MetricCard key={item.id} {...item} />)
            ) : (
              <p
                className="col-span-5 text-center py-4"
                style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 12 }}
              >
                No FX data available
              </p>
            )}
          </div>
        </section>

        {/* Row 2: Top Movers + FII/DII */}
        <section className="grid grid-cols-3 gap-5" data-testid="movers-fii-section">
          {/* Top Movers */}
          <div
            className="col-span-2 dashboard-card"
          >
            <SectionHeading
              right={
                <span style={{ color: 'rgba(10, 22, 40, 0.45)', fontSize: 10, letterSpacing: '0.18em' }}>
                  NSE · TOP {topMovers.length}
                </span>
              }
            >
              TOP MOVERS
            </SectionHeading>
            {topMovers.length > 0 ? (
              <DataTable columns={topMoversColumns} rows={topMovers} maxHeight={320} />
            ) : (
              <div
                className="flex items-center justify-center h-40"
                style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 12 }}
              >
                No stock data available yet
              </div>
            )}
          </div>

          {/* FII/DII Panel */}
          <div className="dashboard-card">
            <SectionHeading>FII / DII FLOW</SectionHeading>
            <FiiDiiBarChart data={fiiDiiChart} />
            <div className="grid grid-cols-2 gap-3 mt-4">
              <div className="mini-card">
                <p style={{ color: 'rgba(10, 22, 40, 0.55)', fontSize: 9.5, letterSpacing: '0.22em', fontWeight: 700 }}>
                  FII NET
                </p>
                <p
                  className="tabular-nums mt-1"
                  style={{
                    color: fiiDii.fii?.includes('-') ? '#E05252' : '#0A1628',
                    fontSize: 16, fontWeight: 700,
                  }}
                >
                  {fiiDii.fii || '—'}
                </p>
              </div>
              <div className="mini-card">
                <p style={{ color: 'rgba(10, 22, 40, 0.55)', fontSize: 9.5, letterSpacing: '0.22em', fontWeight: 700 }}>
                  DII NET
                </p>
                <p
                  className="tabular-nums mt-1"
                  style={{
                    color: fiiDii.dii?.includes('-') ? '#E05252' : '#2D6A4F',
                    fontSize: 16, fontWeight: 700,
                  }}
                >
                  {fiiDii.dii || '—'}
                </p>
              </div>
            </div>
            {fiiDii.date && (
              <p className="text-center mt-3" style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 10, letterSpacing: '0.1em' }}>
                As of {fiiDii.date}
              </p>
            )}
          </div>
        </section>

        {/* Row 3: Commodities & Crypto */}
        <section data-testid="commodities-section">
          <SectionHeading>COMMODITIES & CRYPTO</SectionHeading>
          <div className="grid grid-cols-4 gap-3">
            {commodities.length > 0 ? (
              commodities.slice(0, 8).map((c) => <MetricCard key={c.id} {...c} />)
            ) : (
              <p
                className="col-span-4 text-center py-4"
                style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 12 }}
              >
                No commodity data available
              </p>
            )}
          </div>
        </section>

        {/* Row 4: News Feed */}
        <section className="dashboard-card" data-testid="news-feed-section">
          <SectionHeading>MARKET NEWS & UPDATES</SectionHeading>
          <div className="space-y-1 max-h-72 overflow-y-auto data-table-wrapper">
            {news.length > 0 ? (
              news.map((item) => <SignalFeedItem key={item.id} {...item} />)
            ) : (
              <p
                className="text-center py-4"
                style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 12 }}
              >
                No news available
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default MarketOverview;
