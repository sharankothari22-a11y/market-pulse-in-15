import { useState, useEffect } from 'react';
import { CustomTabs } from '@/components/ui/CustomTabs';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { Bell, BellOff, CheckCircle, Loader2, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

const tabs = [
  { value: 'all',      label: 'All' },
  { value: 'high',     label: 'High Priority' },
  { value: 'banking',  label: 'Banking' },
  { value: 'it',       label: 'IT' },
  { value: 'petroleum',label: 'Petroleum' },
  { value: 'pharma',   label: 'Pharma' },
  { value: 'fmcg',     label: 'FMCG' },
];

const filterSignals = (signals, tab) => {
  if (!signals) return [];
  if (tab === 'all') return signals;
  if (tab === 'high') return signals.filter(s =>
    s.severity === 'danger' || s.severity === 'warning' || s.severity === 'negative'
  );
  return signals.filter(s => s.sector?.toLowerCase() === tab);
};

const severityBorder = {
  positive: 'border-l-[#16a34a]',
  negative: 'border-l-[#dc2626]',
  warning:  'border-l-[#d97706]',
  danger:   'border-l-[#dc2626]',
  info:     'border-l-[#2563eb]',
};

const SignalItem = ({ title, timestamp, severity, sector, signalType, price, change_pct }) => (
  <div className={cn("border-l-4 pl-3 py-2.5 flex items-start justify-between gap-4",
    severityBorder[severity] || severityBorder.info)}>
    <div className="flex-1 min-w-0">
      <p className="text-sm text-[#0f172a] leading-snug">{title}</p>
      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span className="text-xs text-[#64748b]">{timestamp}</span>
        {sector && <><span className="text-xs text-[#94a3b8]">•</span><span className="text-xs text-[#64748b]">{sector}</span></>}
        {signalType && <><span className="text-xs text-[#94a3b8]">•</span><span className="text-xs text-[#2563eb]">{signalType}</span></>}
      </div>
    </div>
    {price && (
      <div className="text-right flex-shrink-0">
        <p className="text-sm font-medium text-[#0f172a]">₹{price}</p>
        {change_pct !== undefined && (
          <p className={cn("text-xs font-medium", change_pct >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]')}>
            {change_pct >= 0 ? '+' : ''}{change_pct?.toFixed(2)}%
          </p>
        )}
      </div>
    )}
  </div>
);

export const SignalsAlerts = () => {
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [signalsData, alertsData] = await Promise.all([
        apiGet(API_ENDPOINTS.signals),
        apiGet(API_ENDPOINTS.alerts),
      ]);
      setSignals(signalsData?.signals || signalsData || []);
      setAlerts(alertsData?.alerts || alertsData || []);
      setLastUpdated(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Count by type
  const positiveCount = signals.filter(s => s.severity === 'positive').length;
  const negativeCount = signals.filter(s => s.severity === 'negative' || s.severity === 'danger').length;
  const warningCount  = signals.filter(s => s.severity === 'warning').length;

  if (loading && signals.length === 0) {
    return (
      <div className="page-content p-6 flex items-center justify-center bg-[#ffffff]">
        <div className="flex items-center gap-3 text-[#64748b]">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Scanning market signals...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="signals-alerts-page">

      {/* Summary bar */}
      <section className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 px-4 py-2 bg-[#f8fafc] border border-[#e5e7eb] rounded-lg">
          <Activity className="w-4 h-4 text-[#64748b]" />
          <span className="text-sm text-[#64748b]">{signals.length} signals</span>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-[#16a34a]/5 border border-[#16a34a]/20 rounded-lg">
          <TrendingUp className="w-4 h-4 text-[#16a34a]" />
          <span className="text-sm text-[#16a34a] font-medium">{positiveCount} bullish</span>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-[#dc2626]/5 border border-[#dc2626]/20 rounded-lg">
          <TrendingDown className="w-4 h-4 text-[#dc2626]" />
          <span className="text-sm text-[#dc2626] font-medium">{negativeCount} bearish</span>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-[#d97706]/5 border border-[#d97706]/20 rounded-lg">
          <Bell className="w-4 h-4 text-[#d97706]" />
          <span className="text-sm text-[#d97706] font-medium">{warningCount} warnings</span>
        </div>
        {lastUpdated && (
          <span className="text-xs text-[#94a3b8] ml-auto">Updated {lastUpdated}</span>
        )}
        <button onClick={fetchData} className="text-xs text-[#2563eb] hover:underline">Refresh</button>
      </section>

      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm">{error}</div>
      )}

      {/* Signals Feed */}
      <section className="dashboard-card" data-testid="signals-feed-section">
        <CustomTabs tabs={tabs} defaultTab="all">
          {(activeTab) => {
            const filtered = filterSignals(signals, activeTab);
            return (
              <div className="space-y-1 max-h-[480px] overflow-y-auto">
                {filtered.map((signal, idx) => (
                  <SignalItem key={signal.id || idx} {...signal} />
                ))}
                {filtered.length === 0 && (
                  <div className="text-center py-10 text-[#64748b]">
                    {loading ? 'Scanning...' : 'No signals in this category right now'}
                  </div>
                )}
              </div>
            );
          }}
        </CustomTabs>
      </section>

      {/* Active Alerts */}
      <section data-testid="active-alerts-section">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Active Alerts</h2>
        <div className="grid grid-cols-3 gap-4">
          {alerts.map((alert, idx) => (
            <div key={alert.id || idx} className="dashboard-card flex items-start gap-3">
              <div className={`p-2 rounded-lg ${alert.status === 'triggered' ? 'bg-[#d97706]/10' : 'bg-[#2563eb]/10'}`}>
                {alert.status === 'triggered'
                  ? <Bell className="w-5 h-5 text-[#d97706]" />
                  : <BellOff className="w-5 h-5 text-[#2563eb]" />}
              </div>
              <div className="flex-1">
                <p className="text-sm text-[#0f172a] font-medium">{alert.condition}</p>
                {alert.value && (
                  <p className="text-xs text-[#64748b] mt-0.5">
                    Current: {typeof alert.value === 'number' ? alert.value.toLocaleString('en-IN') : alert.value}
                    {alert.change_pct !== undefined && (
                      <span className={cn("ml-1", alert.change_pct >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]')}>
                        ({alert.change_pct >= 0 ? '+' : ''}{alert.change_pct?.toFixed(2)}%)
                      </span>
                    )}
                  </p>
                )}
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
            <div className="col-span-3 text-center py-8 text-[#64748b]">No active alerts</div>
          )}
        </div>
      </section>

      {/* Quick Actions */}
      <section className="dashboard-card" data-testid="quick-actions">
        <h2 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Quick Actions</h2>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition-colors text-sm font-medium">
            <Bell className="w-4 h-4" /> Create New Alert
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-[#f8fafc] text-[#0f172a] rounded-lg hover:bg-[#f1f5f9] transition-colors text-sm font-medium border border-[#e5e7eb]">
            <CheckCircle className="w-4 h-4" /> Mark All as Read
          </button>
        </div>
      </section>
    </div>
  );
};

export default SignalsAlerts;
