import { useState, useEffect } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { MiniChart } from '@/components/ui/MiniChart';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react';

const macroMicroColumns = [
  { header: 'Macro Factor', accessor: 'macro', className: 'font-medium' },
  { header: 'Trigger', accessor: 'trigger' },
  { header: 'Sector', accessor: 'sector' },
  { header: 'Impact', accessor: 'impact', className: 'text-sm' },
];

export const MacroDashboard = () => {
  const [macroData, setMacroData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMacroData = async () => {
      try {
        setLoading(true);
        const data = await apiGet(API_ENDPOINTS.macro);
        setMacroData(data);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Failed to fetch macro data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMacroData();
    // Poll every 60 seconds
    const interval = setInterval(fetchMacroData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !macroData) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]" data-testid="macro-loading">
        <div className="flex items-center gap-3 text-[#64748b]">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading macro data...</span>
        </div>
      </div>
    );
  }

  if (error && !macroData) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]" data-testid="macro-error">
        <div className="text-center">
          <p className="text-[#dc2626] mb-2">Failed to load macro data</p>
          <p className="text-[#64748b] text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const { indicators = [], globalEvents = [], macroMicro = [] } = macroData || {};

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="macro-dashboard-page">
      {/* Top: Key Indicators */}
      <section data-testid="macro-indicators-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Key Economic Indicators</h2>
        <div className="grid grid-cols-4 gap-4">
          {indicators.map((indicator) => (
            <MetricCard key={indicator.id} {...indicator} />
          ))}
        </div>
      </section>

      {/* Charts Grid */}
      <section className="grid grid-cols-2 gap-6" data-testid="macro-charts-section">
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">GDP Growth Trend</h3>
          <MiniChart title="India GDP YoY %" height={200} />
        </div>
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">CPI vs Repo Rate</h3>
          <MiniChart title="Inflation vs Policy Rate" height={200} />
        </div>
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">FII Flows (Monthly)</h3>
          <MiniChart title="FII Net Investment ₹ Cr" height={200} />
        </div>
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">DXY Index</h3>
          <MiniChart title="US Dollar Index" height={200} />
        </div>
      </section>

      {/* Global Events Feed */}
      <section className="dashboard-card" data-testid="global-events-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Global Events</h2>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {globalEvents.map((event, idx) => (
            <div 
              key={event.id || idx}
              className="flex items-start gap-3 p-3 bg-[#f8fafc] rounded-lg hover:bg-[#f1f5f9] transition-colors border border-[#e5e7eb]"
              data-testid={`global-event-${event.id || idx}`}
            >
              <div className={`p-1.5 rounded ${
                event.impact === 'Positive' ? 'bg-[#16a34a]/10' : 
                event.impact === 'Negative' ? 'bg-[#dc2626]/10' : 'bg-[#d97706]/10'
              }`}>
                {event.impact === 'Positive' ? (
                  <TrendingUp className="w-4 h-4 text-[#16a34a]" />
                ) : event.impact === 'Negative' ? (
                  <TrendingDown className="w-4 h-4 text-[#dc2626]" />
                ) : (
                  <Minus className="w-4 h-4 text-[#d97706]" />
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm text-[#0f172a]">{event.event}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-[#64748b]">{event.region}</span>
                  <StatusBadge variant={
                    event.impact === 'Positive' ? 'success' : 
                    event.impact === 'Negative' ? 'danger' : 'warning'
                  }>
                    {event.impact}
                  </StatusBadge>
                </div>
              </div>
            </div>
          ))}
          {globalEvents.length === 0 && (
            <div className="text-center py-8 text-[#64748b]">
              No global events available
            </div>
          )}
        </div>
      </section>

      {/* Macro-Micro Transmission Table */}
      <section className="dashboard-card" data-testid="macro-micro-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Macro-Micro Transmission</h2>
        {macroMicro.length > 0 ? (
          <DataTable columns={macroMicroColumns} rows={macroMicro} maxHeight={200} />
        ) : (
          <div className="text-center py-8 text-[#64748b]">
            No macro-micro transmission data available
          </div>
        )}
      </section>
    </div>
  );
};

export default MacroDashboard;
