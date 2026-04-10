import { MetricCard } from '@/components/ui/MetricCard';
import { MiniChart } from '@/components/ui/MiniChart';
import { DataTable } from '@/components/ui/DataTable';
import { SignalFeedItem } from '@/components/ui/SignalFeedItem';
import { marketIndices, topMovers, commodities, fiiDiiData, newsSignals } from '@/data/mockData';

const topMoversColumns = [
  { header: 'Symbol', accessor: 'symbol', className: 'font-medium' },
  { header: 'LTP', accessor: 'ltp' },
  { 
    header: 'Change', 
    accessor: 'change',
    render: (row) => (
      <span className={row.changeType === 'positive' ? 'text-[#16a34a]' : 'text-[#dc2626]'}>
        {row.change}
      </span>
    )
  },
  { header: 'Volume', accessor: 'volume', className: 'text-[#64748b]' },
];

export const MarketOverview = () => {
  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="market-overview-page">
      {/* Row 1: Market Indices */}
      <section data-testid="market-indices-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Market Indices</h2>
        <div className="grid grid-cols-5 gap-4">
          {marketIndices.map((index) => (
            <MetricCard key={index.id} {...index} />
          ))}
        </div>
      </section>

      {/* Row 2: Top Movers + FII/DII */}
      <section className="grid grid-cols-3 gap-6" data-testid="movers-fii-section">
        {/* Top Movers Table */}
        <div className="col-span-2 dashboard-card">
          <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Top Movers</h2>
          <DataTable columns={topMoversColumns} rows={topMovers} maxHeight={280} />
        </div>

        {/* FII/DII Panel */}
        <div className="dashboard-card space-y-4">
          <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">FII/DII Flow</h2>
          <MiniChart title="FII vs DII Weekly" height={160} />
          <div className="grid grid-cols-2 gap-3">
            <div className="mini-card">
              <p className="text-xs text-[#64748b]">FII Net</p>
              <p className="text-lg font-semibold text-[#dc2626]">{fiiDiiData.summary.fii}</p>
            </div>
            <div className="mini-card">
              <p className="text-xs text-[#64748b]">DII Net</p>
              <p className="text-lg font-semibold text-[#16a34a]">{fiiDiiData.summary.dii}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Row 3: Commodities */}
      <section data-testid="commodities-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Commodities & Crypto</h2>
        <div className="grid grid-cols-4 gap-4">
          {commodities.map((commodity) => (
            <MetricCard key={commodity.id} {...commodity} />
          ))}
        </div>
      </section>

      {/* Row 4: News Feed */}
      <section className="dashboard-card" data-testid="news-feed-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Market News & Updates</h2>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {newsSignals.map((signal) => (
            <SignalFeedItem key={signal.id} {...signal} />
          ))}
        </div>
      </section>
    </div>
  );
};

export default MarketOverview;
