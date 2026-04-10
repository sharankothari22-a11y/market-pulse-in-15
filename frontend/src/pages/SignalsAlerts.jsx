import { CustomTabs } from '@/components/ui/CustomTabs';
import { SignalFeedItem } from '@/components/ui/SignalFeedItem';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { signalsAlerts, activeAlerts } from '@/data/mockData';
import { Bell, BellOff, CheckCircle } from 'lucide-react';

const tabs = [
  { value: 'all', label: 'All' },
  { value: 'high', label: 'High Priority' },
  { value: 'petroleum', label: 'Petroleum' },
  { value: 'banking', label: 'Banking' },
  { value: 'fmcg', label: 'FMCG' },
  { value: 'it', label: 'IT' },
  { value: 'pharma', label: 'Pharma' },
];

const filterSignals = (signals, tab) => {
  if (tab === 'all') return signals;
  if (tab === 'high') return signals.filter(s => s.severity === 'danger' || s.severity === 'warning');
  return signals.filter(s => s.sector.toLowerCase() === tab);
};

export const SignalsAlerts = () => {
  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="signals-alerts-page">
      {/* Signals Feed with Tabs */}
      <section className="dashboard-card" data-testid="signals-feed-section">
        <CustomTabs tabs={tabs} defaultTab="all">
          {(activeTab) => (
            <div className="space-y-3 max-h-[420px] overflow-y-auto">
              {filterSignals(signalsAlerts, activeTab).map((signal) => (
                <SignalFeedItem key={signal.id} {...signal} />
              ))}
              {filterSignals(signalsAlerts, activeTab).length === 0 && (
                <div className="text-center py-8 text-[#64748b]">
                  No signals in this category
                </div>
              )}
            </div>
          )}
        </CustomTabs>
      </section>

      {/* Active Alerts */}
      <section data-testid="active-alerts-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Active Alerts</h2>
        <div className="grid grid-cols-3 gap-4">
          {activeAlerts.map((alert) => (
            <div 
              key={alert.id}
              className="dashboard-card flex items-start gap-3"
              data-testid={`alert-card-${alert.id}`}
            >
              <div className={`p-2 rounded-lg ${alert.status === 'triggered' ? 'bg-[#d97706]/10' : 'bg-[#2563eb]/10'}`}>
                {alert.status === 'triggered' ? (
                  <Bell className="w-5 h-5 text-[#d97706]" />
                ) : (
                  <BellOff className="w-5 h-5 text-[#2563eb]" />
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm text-[#0f172a] font-medium">{alert.condition}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs text-[#64748b]">{alert.type}</span>
                  <StatusBadge variant={alert.status === 'triggered' ? 'warning' : 'info'}>
                    {alert.status}
                  </StatusBadge>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Quick Actions */}
      <section className="dashboard-card" data-testid="quick-actions">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Quick Actions</h2>
        <div className="flex gap-3">
          <button 
            className="flex items-center gap-2 px-4 py-2 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition-colors text-sm font-medium"
            data-testid="create-alert-btn"
          >
            <Bell className="w-4 h-4" />
            Create New Alert
          </button>
          <button 
            className="flex items-center gap-2 px-4 py-2 bg-[#f8fafc] text-[#0f172a] rounded-lg hover:bg-[#f1f5f9] transition-colors text-sm font-medium border border-[#e5e7eb]"
            data-testid="mark-read-btn"
          >
            <CheckCircle className="w-4 h-4" />
            Mark All as Read
          </button>
        </div>
      </section>
    </div>
  );
};

export default SignalsAlerts;
