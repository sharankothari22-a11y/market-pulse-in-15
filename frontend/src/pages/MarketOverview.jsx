import { useState, useEffect } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { MiniChart } from '@/components/ui/MiniChart';
import { DataTable } from '@/components/ui/DataTable';
import { SignalFeedItem } from '@/components/ui/SignalFeedItem';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { Loader2 } from 'lucide-react';

const topMoversColumns = [
  { header: 'Symbol', accessor: 'symbol', className: 'font-medium' },
  { header: 'LTP', accessor: 'ltp' },
  { 
    header: 'Change', 
    accessor: 'change',
    render: (row) => {
      const changeValue = row.change_percent || row.change;
      const isPositive = parseFloat(changeValue) >= 0;
      return (
        <span className={isPositive ? 'text-[#16a34a]' : 'text-[#dc2626]'}>
          {typeof changeValue === 'number' ? `${changeValue >= 0 ? '+' : ''}${changeValue.toFixed(2)}%` : changeValue}
        </span>
      );
    }
  },
  { header: 'Volume', accessor: 'volume', className: 'text-[#64748b]' },
];

// Helper to format currency values
const formatCurrency = (value, currency = 'USD') => {
  if (value == null) return 'N/A';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  
  if (currency === 'INR') {
    return `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

// Helper to format percentage
const formatPercent = (value) => {
  if (value == null) return 'N/A';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
};

// Transform commodities from backend format
const transformCommodities = (commodities = []) => {
  return commodities.map((item, idx) => ({
    id: item.symbol || item.id || idx,
    title: item.symbol || item.name || 'Unknown',
    value: formatCurrency(item.price || item.current_price, 'USD'),
    change: formatPercent(item.change_24h || item.change_percent),
    changeType: parseFloat(item.change_24h || item.change_percent || 0) >= 0 ? 'positive' : 'negative',
    subtitle: item.market_cap ? `MCap: $${(item.market_cap / 1e9).toFixed(1)}B` : '',
  }));
};

// Transform FX rates from backend format
const transformFxRates = (fx = {}) => {
  const rates = [];
  Object.entries(fx).forEach(([pair, data]) => {
    if (data && typeof data === 'object') {
      rates.push({
        id: pair,
        title: pair.toUpperCase(),
        value: typeof data.rate === 'number' ? data.rate.toFixed(4) : data.rate || 'N/A',
        change: formatPercent(data.change_percent || data.change),
        changeType: parseFloat(data.change_percent || data.change || 0) >= 0 ? 'positive' : 'negative',
        subtitle: data.source || '',
      });
    } else if (typeof data === 'number') {
      rates.push({
        id: pair,
        title: pair.toUpperCase(),
        value: data.toFixed(4),
        change: 'N/A',
        changeType: 'neutral',
        subtitle: '',
      });
    }
  });
  return rates;
};

// Transform FII/DII data
const transformFiiDii = (fiiDii = []) => {
  if (Array.isArray(fiiDii) && fiiDii.length > 0) {
    // Get the latest entry
    const latest = fiiDii[0];
    const fiiNet = latest.fii_net || latest.fii || latest.FII || 0;
    const diiNet = latest.dii_net || latest.dii || latest.DII || 0;
    return {
      fii: typeof fiiNet === 'number' ? `₹${(fiiNet / 100).toFixed(0)} Cr` : fiiNet,
      dii: typeof diiNet === 'number' ? `₹${(diiNet / 100).toFixed(0)} Cr` : diiNet,
      date: latest.date || latest.trade_date || '',
      data: fiiDii,
    };
  }
  return { fii: '-', dii: '-', data: [] };
};

// Transform news articles
const transformNews = (news = []) => {
  return news.map((item, idx) => ({
    id: item.id || idx,
    title: item.title || item.headline || 'No title',
    timestamp: item.published_at || item.timestamp || item.date || 'Recent',
    severity: item.sentiment === 'positive' ? 'positive' : 
              item.sentiment === 'negative' ? 'danger' : 'info',
    sector: item.category || item.sector || item.source || 'General',
    signalType: item.type || 'News',
  }));
};

// Transform top movers
const transformTopMovers = (movers = []) => {
  return movers.map((item, idx) => ({
    id: item.symbol || idx,
    symbol: item.symbol || item.ticker || 'N/A',
    ltp: item.ltp || item.price || item.last_price || 'N/A',
    change: item.change_percent || item.change || item.pct_change || 0,
    change_percent: item.change_percent || item.pct_change,
    changeType: parseFloat(item.change_percent || item.change || 0) >= 0 ? 'positive' : 'negative',
    volume: item.volume ? `${(item.volume / 1e6).toFixed(1)}M` : 'N/A',
  }));
};

export const MarketOverview = () => {
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMarketData = async () => {
      try {
        setLoading(true);
        const data = await apiGet(API_ENDPOINTS.marketOverview);
        console.log('Market data received:', data); // Debug log
        setMarketData(data);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Failed to fetch market data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMarketData();
    // Poll every 30 seconds
    const interval = setInterval(fetchMarketData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !marketData) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]" data-testid="market-overview-loading">
        <div className="flex items-center gap-3 text-[#64748b]">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading market data...</span>
        </div>
      </div>
    );
  }

  if (error && !marketData) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]" data-testid="market-overview-error">
        <div className="text-center">
          <p className="text-[#dc2626] mb-2">Failed to load market data</p>
          <p className="text-[#64748b] text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // Transform backend data to UI format
  const commodities = transformCommodities(marketData?.commodities || []);
  const fxRates = transformFxRates(marketData?.fx || {});
  const fiiDii = transformFiiDii(marketData?.fii_dii || []);
  const news = transformNews(marketData?.news || []);
  const topMovers = transformTopMovers(marketData?.top_movers || []);

  // Combine FX rates as "indices" for now (since we don't have NSE data)
  const indices = fxRates.length > 0 ? fxRates.slice(0, 5) : [];

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="market-overview-page">
      {/* Row 1: FX Rates / Market Indices */}
      <section data-testid="market-indices-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">
          {fxRates.length > 0 ? 'FX Rates' : 'Market Indices'}
        </h2>
        <div className="grid grid-cols-5 gap-4">
          {indices.length > 0 ? (
            indices.map((item) => (
              <MetricCard key={item.id} {...item} />
            ))
          ) : (
            <p className="col-span-5 text-[#64748b] text-sm">No market data available</p>
          )}
        </div>
      </section>

      {/* Row 2: Top Movers + FII/DII */}
      <section className="grid grid-cols-3 gap-6" data-testid="movers-fii-section">
        {/* Top Movers Table */}
        <div className="col-span-2 dashboard-card">
          <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Top Movers</h2>
          {topMovers.length > 0 ? (
            <DataTable columns={topMoversColumns} rows={topMovers} maxHeight={280} />
          ) : (
            <div className="flex items-center justify-center h-40 text-[#64748b] text-sm">
              No stock data available yet
            </div>
          )}
        </div>

        {/* FII/DII Panel */}
        <div className="dashboard-card space-y-4">
          <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">FII/DII Flow</h2>
          <MiniChart title="FII vs DII Weekly" height={160} />
          <div className="grid grid-cols-2 gap-3">
            <div className="mini-card">
              <p className="text-xs text-[#64748b]">FII Net</p>
              <p className={`text-lg font-semibold ${fiiDii.fii?.includes('-') ? 'text-[#dc2626]' : 'text-[#16a34a]'}`}>
                {fiiDii.fii || '-'}
              </p>
            </div>
            <div className="mini-card">
              <p className="text-xs text-[#64748b]">DII Net</p>
              <p className={`text-lg font-semibold ${fiiDii.dii?.includes('-') ? 'text-[#dc2626]' : 'text-[#16a34a]'}`}>
                {fiiDii.dii || '-'}
              </p>
            </div>
          </div>
          {fiiDii.date && (
            <p className="text-xs text-[#94a3b8] text-center">As of {fiiDii.date}</p>
          )}
        </div>
      </section>

      {/* Row 3: Commodities & Crypto */}
      <section data-testid="commodities-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Commodities & Crypto</h2>
        <div className="grid grid-cols-4 gap-4">
          {commodities.length > 0 ? (
            commodities.map((commodity) => (
              <MetricCard key={commodity.id} {...commodity} />
            ))
          ) : (
            <p className="col-span-4 text-[#64748b] text-sm">No commodity data available</p>
          )}
        </div>
      </section>

      {/* Row 4: News Feed */}
      <section className="dashboard-card" data-testid="news-feed-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Market News & Updates</h2>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {news.length > 0 ? (
            news.map((item) => (
              <SignalFeedItem key={item.id} {...item} />
            ))
          ) : (
            <p className="text-[#64748b] text-sm py-4 text-center">No news available</p>
          )}
        </div>
      </section>
    </div>
  );
};

export default MarketOverview;
