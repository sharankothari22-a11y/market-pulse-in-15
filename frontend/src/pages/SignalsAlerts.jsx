import { useState, useEffect } from 'react';
import { CustomTabs } from '@/components/ui/CustomTabs';
import { SignalFeedItem } from '@/components/ui/SignalFeedItem';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { Bell, BellOff, CheckCircle, Loader2 } from 'lucide-react';

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
  if (!signals) return [];
  if (tab === 'all') return signals;
  if (tab === 'high') return signals.filter(s => s.severity === 'danger' || s.severity === 'warning');
  return signals.filter(s => s.sector?.toLowerCase() === tab);
};

export const SignalsAlerts = () => {
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [signalsData, alertsData] = await Promise.all([
          apiGet(API_ENDPOINTS.signals),
          apiGet(API_ENDPOINTS.alerts)
        ]);
        setSignals(signalsData?.signals || signalsData || []);
        setAlerts(alertsData?.alerts || alertsData || []);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Failed to fetch signals/alerts:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Poll every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading && signals.length === 0) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]" data-testid="signals-loading">
        <div className="flex items-center gap-3 text-[#64748b]">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading signals & alerts...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="signals-alerts-page">
      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm">
          {error}
        </div>
      )}

      {/* Signals Feed with Tabs */}
      <section className="dashboard-card" data-testid="signals-feed-section">
        <CustomTabs tabs={tabs} defaultTab="all">
          {(activeTab) => (
            <div className="space-y-3 max-h-[420px] overflow-y-auto">
              {filterSignals(signals, activeTab).map((signal, idx) => (
                <SignalFeedItem key={signal.id || idx} {...signal} />
              ))}
              {filterSignals(signals, activeTab).length === 0 && (
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
          {alerts.map((alert, idx) => (
            <div 
              key={alert.id || idx}
              className="dashboard-card flex items-start gap-3"
              data-testid={`alert-card-${alert.id || idx}`}
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
          {alerts.length === 0 && (
            <div className="col-span-3 text-center py-8 text-[#64748b]">
              No active alerts
            </div>
          )}
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
