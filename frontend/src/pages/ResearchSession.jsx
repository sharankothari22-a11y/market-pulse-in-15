import { useState } from 'react';
import { Search } from 'lucide-react';
import { ScenarioBadge } from '@/components/ui/ScenarioBadge';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DataTable } from '@/components/ui/DataTable';
import { researchData } from '@/data/mockData';

const assumptionColumns = [
  { header: 'Assumption', accessor: 'assumption', className: 'font-medium' },
  { header: 'Old', accessor: 'old', className: 'text-[#64748b]' },
  { header: 'New', accessor: 'new' },
  { 
    header: 'Impact',
    accessor: 'impact',
    render: (row) => {
      const isPositive = row.impact.startsWith('+');
      return (
        <span className={isPositive ? 'text-[#16a34a]' : 'text-[#dc2626]'}>
          {row.impact}
        </span>
      );
    }
  },
];

export const ResearchSession = () => {
  const [ticker, setTicker] = useState(researchData.ticker);

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="research-session-page">
      {/* Ticker Input */}
      <section className="flex items-center gap-4" data-testid="ticker-input-section">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Enter ticker symbol"
            className="w-full bg-[#f8fafc] border border-[#e5e7eb] rounded-lg pl-10 pr-4 py-2.5 text-[#0f172a] placeholder:text-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
            data-testid="ticker-input"
          />
        </div>
        <button 
          className="px-6 py-2.5 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition-colors font-medium"
          data-testid="analyze-btn"
        >
          Analyze
        </button>
      </section>

      {/* Info Bar */}
      <section className="flex items-center gap-4 text-sm" data-testid="info-bar">
        <span className="text-[#0f172a] font-medium">{researchData.ticker}</span>
        <span className="text-[#94a3b8]">|</span>
        <span className="text-[#64748b]">{researchData.sector}</span>
        <span className="text-[#94a3b8]">|</span>
        <span className="text-[#64748b]">Session: {researchData.sessionId}</span>
        <span className="text-[#94a3b8]">|</span>
        <StatusBadge variant="success">{researchData.status}</StatusBadge>
      </section>

      {/* Main Content Grid */}
      <section className="grid grid-cols-2 gap-6" data-testid="research-content">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Hypothesis */}
          <div className="dashboard-card">
            <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Hypothesis</h3>
            <p className="text-sm text-[#0f172a] leading-relaxed">{researchData.hypothesis}</p>
          </div>

          {/* Variant View */}
          <div className="dashboard-card">
            <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Variant View</h3>
            <p className="text-sm text-[#0f172a] leading-relaxed">{researchData.variantView}</p>
          </div>

          {/* Catalysts */}
          <div className="dashboard-card">
            <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Catalysts</h3>
            <div className="space-y-3">
              {researchData.catalysts.map((catalyst, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-[#f1f5f9] rounded-lg">
                  <div>
                    <p className="text-sm text-[#0f172a]">{catalyst.event}</p>
                    <p className="text-xs text-[#64748b] mt-1">{catalyst.timeline}</p>
                  </div>
                  <StatusBadge variant={catalyst.impact === 'High' ? 'warning' : 'info'}>
                    {catalyst.impact}
                  </StatusBadge>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Scenario Analysis */}
          <div className="dashboard-card">
            <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Scenario Analysis</h3>
            <div className="grid grid-cols-3 gap-3">
              {researchData.scenarios.map((scenario) => (
                <ScenarioBadge key={scenario.label} {...scenario} />
              ))}
            </div>
          </div>

          {/* Reverse DCF */}
          <div className="dashboard-card">
            <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Reverse DCF</h3>
            <p className="text-sm text-[#0f172a] leading-relaxed">{researchData.reverseDCF}</p>
          </div>

          {/* Sensitivity Table Placeholder */}
          <div className="dashboard-card">
            <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Sensitivity Analysis</h3>
            <div className="grid grid-cols-5 gap-1" data-testid="sensitivity-table">
              {[...Array(25)].map((_, idx) => (
                <div 
                  key={idx}
                  className="aspect-square bg-[#f1f5f9] border border-[#e5e7eb] rounded flex items-center justify-center text-xs text-[#94a3b8]"
                >
                  {idx === 12 ? '●' : ''}
                </div>
              ))}
            </div>
            <p className="text-xs text-[#94a3b8] mt-2 text-center">WACC vs Terminal Growth</p>
          </div>
        </div>
      </section>

      {/* Assumption Changes Table */}
      <section className="dashboard-card" data-testid="assumption-changes-section">
        <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Assumption Changes</h3>
        <DataTable columns={assumptionColumns} rows={researchData.assumptionChanges} maxHeight={220} />
      </section>
    </div>
  );
};

export default ResearchSession;
