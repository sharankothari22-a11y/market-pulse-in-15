import { useState, useEffect } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { TrendingUp, TrendingDown, Minus, Loader2, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

const macroMicroColumns = [
  { header: 'Macro Factor', accessor: 'macro',   className: 'font-medium' },
  { header: 'Trigger',      accessor: 'trigger' },
  { header: 'Sector',       accessor: 'sector' },
  { header: 'Impact',       accessor: 'impact',  className: 'text-sm' },
];

// Split indicators into indices vs macro
const INDEX_IDS = ['^NSEI', '^BSESN', '^GSPC', '^DJI', '^IXIC', '^VIX'];

export const MacroDashboard = () => {
  const [macroData, setMacroData] = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchMacroData = async () => {
    try {
      setLoading(true);
      const data = await apiGet(API_ENDPOINTS.macro);
      setMacroData(data);
      setLastUpdated(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMacroData();
    const interval = setInterval(fetchMacroData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !macroData) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]">
        <div className="flex items-center gap-3 text-[#64748b]">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading macro data...</span>
        </div>
      </div>
    );
  }

  if (error && !macroData) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]">
        <div className="text-center">
          <p className="text-[#dc2626] mb-2">Failed to load macro data</p>
          <p className="text-[#64748b] text-sm">{error}</p>
          <button onClick={fetchMacroData} className="mt-3 text-sm text-[#2563eb] hover:underline">Retry</button>
        </div>
      </div>
    );
  }

  const { indicators = [], globalEvents = [], macroMicro = [] } = macroData || {};

  // Split into live indices and other macro indicators
  const liveIndices   = indicators.filter(i => INDEX_IDS.includes(i.id));
  const macroIndicators = indicators.filter(i => !INDEX_IDS.includes(i.id));

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="macro-dashboard-page">

      {/* Live Market Indices */}
      <section data-testid="live-indices-section">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">Live Market Indices</h2>
          <div className="flex items-center gap-2">
            {lastUpdated && <span className="text-xs text-[#94a3b8]">Updated {lastUpdated}</span>}
            <button onClick={fetchMacroData} className="text-[#64748b] hover:text-[#2563eb]">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {liveIndices.length > 0 ? liveIndices.map((ind) => (
            <div key={ind.id} className="dashboard-card">
              <p className="text-xs text-[#64748b] uppercase tracking-wider mb-1">{ind.title}</p>
              <p className="text-2xl font-semibold text-[#0f172a]">
                {typeof ind.raw_value === 'number'
                  ? ind.raw_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
                  : ind.value}
              </p>
              <div className="flex items-center gap-1.5 mt-1">
                {ind.changeType === 'positive'
                  ? <TrendingUp className="w-3.5 h-3.5 text-[#16a34a]" />
                  : <TrendingDown className="w-3.5 h-3.5 text-[#dc2626]" />}
                <span className={cn("text-sm font-medium",
                  ind.changeType === 'positive' ? 'text-[#16a34a]' : 'text-[#dc2626]')}>
                  {ind.change}
                </span>
                <span className="text-xs text-[#64748b]">{ind.subtitle}</span>
              </div>
            </div>
          )) : (
            // Fallback skeleton while loading
            [...Array(6)].map((_, i) => (
              <div key={i} className="dashboard-card animate-pulse">
                <div className="h-3 bg-[#f1f5f9] rounded w-16 mb-2"></div>
                <div className="h-7 bg-[#f1f5f9] rounded w-24 mb-2"></div>
                <div className="h-3 bg-[#f1f5f9] rounded w-12"></div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Macro Indicators (FRED data if available) */}
      {macroIndicators.length > 0 && (
        <section data-testid="macro-indicators-section">
          <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Economic Indicators</h2>
          <div className="grid grid-cols-4 gap-4">
            {macroIndicators.map((indicator) => (
              <MetricCard key={indicator.id} {...indicator} />
            ))}
          </div>
        </section>
      )}

      {/* Global Events */}
      <section className="dashboard-card" data-testid="global-events-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Global Events</h2>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {globalEvents.map((event, idx) => (
            <div
              key={event.id || idx}
              className="flex items-start gap-3 p-3 bg-[#f8fafc] rounded-lg hover:bg-[#f1f5f9] transition-colors border border-[#e5e7eb]"
            >
              <div className={cn("p-1.5 rounded flex-shrink-0",
                event.impact === 'Positive' ? 'bg-[#16a34a]/10' :
                event.impact === 'Negative' ? 'bg-[#dc2626]/10' : 'bg-[#d97706]/10')}>
                {event.impact === 'Positive'
                  ? <TrendingUp className="w-4 h-4 text-[#16a34a]" />
                  : event.impact === 'Negative'
                  ? <TrendingDown className="w-4 h-4 text-[#dc2626]" />
                  : <Minus className="w-4 h-4 text-[#d97706]" />}
              </div>
              <div className="flex-1">
                <p className="text-sm text-[#0f172a]">{event.event}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-[#64748b]">{event.region}</span>
                  <StatusBadge variant={
                    event.impact === 'Positive' ? 'success' :
                    event.impact === 'Negative' ? 'danger' : 'warning'}>
                    {event.impact}
                  </StatusBadge>
                </div>
              </div>
            </div>
          ))}
          {globalEvents.length === 0 && (
            <div className="text-center py-8 text-[#64748b]">No global events</div>
          )}
        </div>
      </section>

      {/* Macro-Micro Transmission */}
      <section className="dashboard-card" data-testid="macro-micro-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Macro-Micro Transmission</h2>
        {macroMicro.length > 0
          ? <DataTable columns={macroMicroColumns} rows={macroMicro} maxHeight={200} />
          : (
            <div className="text-center py-10">
              <div className="inline-flex flex-col items-center gap-2">
                <span style={{ fontSize: 28 }}>📡</span>
                <p className="text-sm font-medium text-[#0f172a]">Coming Soon</p>
                <p className="text-xs text-[#64748b]">Live correlation engine — launching Q3 2026</p>
                <p className="text-xs text-[#94a3b8] mt-1">Will map macro factors (FX, rates, oil) to sector-level impact in real time</p>
              </div>
            </div>
          )}
      </section>
    </div>
  );
};

export default MacroDashboard;
