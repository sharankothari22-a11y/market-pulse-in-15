import { MetricCard } from '@/components/ui/MetricCard';
import { MiniChart } from '@/components/ui/MiniChart';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { macroData } from '@/data/mockData';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const macroMicroColumns = [
  { header: 'Macro Factor', accessor: 'macro', className: 'font-medium' },
  { header: 'Trigger', accessor: 'trigger' },
  { header: 'Sector', accessor: 'sector' },
  { header: 'Impact', accessor: 'impact', className: 'text-sm' },
];

export const MacroDashboard = () => {
  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto" data-testid="macro-dashboard-page">
      {/* Top: Key Indicators */}
      <section data-testid="macro-indicators-section">
        <h2 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">Key Economic Indicators</h2>
        <div className="grid grid-cols-4 gap-4">
          {macroData.indicators.map((indicator) => (
            <MetricCard key={indicator.id} {...indicator} />
          ))}
        </div>
      </section>

      {/* Charts Grid */}
      <section className="grid grid-cols-2 gap-6" data-testid="macro-charts-section">
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">GDP Growth Trend</h3>
          <MiniChart title="India GDP YoY %" height={200} />
        </div>
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">CPI vs Repo Rate</h3>
          <MiniChart title="Inflation vs Policy Rate" height={200} />
        </div>
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">FII Flows (Monthly)</h3>
          <MiniChart title="FII Net Investment ₹ Cr" height={200} />
        </div>
        <div className="dashboard-card">
          <h3 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">DXY Index</h3>
          <MiniChart title="US Dollar Index" height={200} />
        </div>
      </section>

      {/* Global Events Feed */}
      <section className="dashboard-card" data-testid="global-events-section">
        <h2 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">Global Events</h2>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {macroData.globalEvents.map((event) => (
            <div 
              key={event.id}
              className="flex items-start gap-3 p-3 bg-[#0a0e1a] rounded-lg hover:bg-[#1f2937] transition-colors"
              data-testid={`global-event-${event.id}`}
            >
              <div className={`p-1.5 rounded ${
                event.impact === 'Positive' ? 'bg-[#10b981]/20' : 
                event.impact === 'Negative' ? 'bg-[#ef4444]/20' : 'bg-[#f59e0b]/20'
              }`}>
                {event.impact === 'Positive' ? (
                  <TrendingUp className="w-4 h-4 text-[#10b981]" />
                ) : event.impact === 'Negative' ? (
                  <TrendingDown className="w-4 h-4 text-[#ef4444]" />
                ) : (
                  <Minus className="w-4 h-4 text-[#f59e0b]" />
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm text-[#f9fafb]">{event.event}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-[#9ca3af]">{event.region}</span>
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
        </div>
      </section>

      {/* Macro-Micro Transmission Table */}
      <section className="dashboard-card" data-testid="macro-micro-section">
        <h2 className="text-sm font-medium text-[#9ca3af] uppercase tracking-wider mb-3">Macro-Micro Transmission</h2>
        <DataTable columns={macroMicroColumns} rows={macroData.macroMicro} maxHeight={200} />
      </section>
    </div>
  );
};

export default MacroDashboard;
