import { useState, useEffect } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { ScenarioBadge } from '@/components/ui/ScenarioBadge';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DataTable } from '@/components/ui/DataTable';
import { apiGet, apiPost, API_ENDPOINTS } from '@/services/api';

const assumptionColumns = [
  { header: 'Assumption', accessor: 'assumption', className: 'font-medium' },
  { header: 'Old', accessor: 'old', className: 'text-[#64748b]' },
  { header: 'New', accessor: 'new' },
  { 
    header: 'Impact',
    accessor: 'impact',
    render: (row) => {
      const isPositive = row.impact?.startsWith('+');
      return (
        <span className={isPositive ? 'text-[#16a34a]' : 'text-[#dc2626]'}>
          {row.impact}
        </span>
      );
    }
  },
];

export const ResearchSession = () => {
  const [ticker, setTicker] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [researchData, setResearchData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  // Fetch existing sessions on mount
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const sessions = await apiGet(API_ENDPOINTS.sessions);
        if (sessions && sessions.length > 0) {
          const latestSession = sessions[0];
          setSessionId(latestSession.session_id);
          setTicker(latestSession.ticker || '');
        }
      } catch (err) {
        console.error('Failed to fetch sessions:', err);
      }
    };
    fetchSessions();
  }, []);

  // Fetch research data when sessionId changes
  useEffect(() => {
    if (!sessionId) return;

    const fetchResearchData = async () => {
      try {
        setLoading(true);
        const data = await apiGet(API_ENDPOINTS.research(sessionId));
        setResearchData(data);
        if (data.ticker) setTicker(data.ticker);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Failed to fetch research data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchResearchData();
  }, [sessionId]);

  const handleAnalyze = async () => {
    if (!ticker.trim()) return;

    try {
      setAnalyzing(true);
      setError(null);
      
      // Create new research session
      const newSession = await apiPost(API_ENDPOINTS.researchNew, { ticker: ticker.toUpperCase() });
      setSessionId(newSession.session_id);
      
      // Run scenarios
      await apiPost(API_ENDPOINTS.researchScenarios(newSession.session_id), {});
      
      // Fetch updated research data
      const data = await apiGet(API_ENDPOINTS.research(newSession.session_id));
      setResearchData(data);
    } catch (err) {
      setError(err.message);
      console.error('Failed to analyze:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAnalyze();
    }
  };

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
            onKeyPress={handleKeyPress}
            placeholder="Enter ticker symbol (e.g., RELIANCE, TCS)"
            className="w-full bg-[#f8fafc] border border-[#e5e7eb] rounded-lg pl-10 pr-4 py-2.5 text-[#0f172a] placeholder:text-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
            data-testid="ticker-input"
          />
        </div>
        <button 
          onClick={handleAnalyze}
          disabled={!ticker.trim() || analyzing}
          className="px-6 py-2.5 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          data-testid="analyze-btn"
        >
          {analyzing && <Loader2 className="w-4 h-4 animate-spin" />}
          {analyzing ? 'Analyzing...' : 'Analyze'}
        </button>
      </section>

      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm">
          {error}
        </div>
      )}

      {/* Info Bar */}
      {researchData && (
        <section className="flex items-center gap-4 text-sm" data-testid="info-bar">
          <span className="text-[#0f172a] font-medium">{researchData.ticker}</span>
          <span className="text-[#94a3b8]">|</span>
          <span className="text-[#64748b]">{researchData.sector || 'N/A'}</span>
          <span className="text-[#94a3b8]">|</span>
          <span className="text-[#64748b]">Session: {researchData.sessionId || sessionId}</span>
          <span className="text-[#94a3b8]">|</span>
          <StatusBadge variant="success">{researchData.status || 'Active'}</StatusBadge>
        </section>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-[#2563eb]" />
          <span className="ml-2 text-[#64748b]">Loading research data...</span>
        </div>
      ) : researchData ? (
        <>
          {/* Main Content Grid */}
          <section className="grid grid-cols-2 gap-6" data-testid="research-content">
            {/* Left Column */}
            <div className="space-y-6">
              {/* Hypothesis */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Hypothesis</h3>
                <p className="text-sm text-[#0f172a] leading-relaxed">{researchData.hypothesis || 'No hypothesis available'}</p>
              </div>

              {/* Variant View */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Variant View</h3>
                <p className="text-sm text-[#0f172a] leading-relaxed">{researchData.variantView || 'No variant view available'}</p>
              </div>

              {/* Catalysts */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Catalysts</h3>
                <div className="space-y-3">
                  {(researchData.catalysts || []).map((catalyst, idx) => (
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
                  {(!researchData.catalysts || researchData.catalysts.length === 0) && (
                    <p className="text-sm text-[#64748b]">No catalysts identified</p>
                  )}
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              {/* Scenario Analysis */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Scenario Analysis</h3>
                <div className="grid grid-cols-3 gap-3">
                  {(researchData.scenarios || []).map((scenario) => (
                    <ScenarioBadge key={scenario.label} {...scenario} />
                  ))}
                  {(!researchData.scenarios || researchData.scenarios.length === 0) && (
                    <p className="text-sm text-[#64748b] col-span-3">Run analysis to see scenarios</p>
                  )}
                </div>
              </div>

              {/* Reverse DCF */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Reverse DCF</h3>
                <p className="text-sm text-[#0f172a] leading-relaxed">{researchData.reverseDCF || 'No DCF analysis available'}</p>
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
            {researchData.assumptionChanges && researchData.assumptionChanges.length > 0 ? (
              <DataTable columns={assumptionColumns} rows={researchData.assumptionChanges} maxHeight={220} />
            ) : (
              <p className="text-sm text-[#64748b]">No assumption changes recorded</p>
            )}
          </section>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Search className="w-12 h-12 text-[#e5e7eb] mb-4" />
          <p className="text-[#64748b]">Enter a ticker symbol and click Analyze to start a research session</p>
        </div>
      )}
    </div>
  );
};

export default ResearchSession;
