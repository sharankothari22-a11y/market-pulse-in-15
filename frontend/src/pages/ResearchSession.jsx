import { useState, useEffect, useRef } from 'react';
import { Search, Loader2, Play, Plus, X, TrendingUp } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DataTable } from '@/components/ui/DataTable';
import { apiGet, apiPost, API_ENDPOINTS } from '@/services/api';
import { cn } from '@/lib/utils';

const SCENARIO_KEYS = ['bull', 'base', 'bear'];

const assumptionColumns = [
  { header: 'Assumption', accessor: 'assumption', className: 'font-medium' },
  { header: 'Old', accessor: 'old', className: 'text-[#64748b]' },
  { header: 'New', accessor: 'new' },
  {
    header: 'Impact',
    accessor: 'impact',
    render: (row) => {
      const isPositive = row.impact?.startsWith('+');
      return <span className={isPositive ? 'text-[#16a34a]' : 'text-[#dc2626]'}>{row.impact}</span>;
    }
  },
];

// Simple sparkline using SVG
const PriceChart = ({ ticker }) => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    const fetchPrices = async () => {
      try {
        setLoading(true);
        const data = await apiGet(`/api/prices/${ticker}?days=90`);
        if (data?.data?.length > 0) setChartData(data.data);
      } catch (e) {
        console.error('Price chart error:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchPrices();
  }, [ticker]);

  if (loading) return (
    <div className="h-24 flex items-center justify-center">
      <Loader2 className="w-4 h-4 animate-spin text-[#64748b]" />
    </div>
  );

  if (chartData.length === 0) return (
    <div className="h-24 flex items-center justify-center text-xs text-[#94a3b8]">No price data</div>
  );

  const closes = chartData.map(d => d.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const w = 600, h = 80;
  const pts = closes.map((c, i) => {
    const x = (i / (closes.length - 1)) * w;
    const y = h - ((c - min) / range) * h;
    return `${x},${y}`;
  }).join(' ');

  const firstClose = closes[0];
  const lastClose = closes[closes.length - 1];
  const changePct = ((lastClose - firstClose) / firstClose * 100).toFixed(1);
  const isUp = lastClose >= firstClose;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-[#64748b]">90-day price</span>
        <span className={cn("text-xs font-medium", isUp ? 'text-[#16a34a]' : 'text-[#dc2626]')}>
          ₹{lastClose.toFixed(2)} ({isUp ? '+' : ''}{changePct}%)
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-16" preserveAspectRatio="none">
        <polyline
          points={pts}
          fill="none"
          stroke={isUp ? '#16a34a' : '#dc2626'}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  );
};

export const ResearchSession = ({ onSessionChange }) => {
  const [ticker, setTicker] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [researchData, setResearchData] = useState(null);
  const [dcfData, setDcfData] = useState(null);
  const [dcfLoading, setDcfLoading] = useState(false);
  const [dcfModelVersion, setDcfModelVersion] = useState('analyst');
  const [reportLoading, setReportLoading] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [runningScenarios, setRunningScenarios] = useState(false);
  const [error, setError] = useState(null);

  // Modal state
  const [showNewModal, setShowNewModal] = useState(false);
  const [modalTicker, setModalTicker] = useState('');
  const [modalHypothesis, setModalHypothesis] = useState('');
  const [modalVariant, setModalVariant] = useState('');
  const [modalSector, setModalSector] = useState('auto');

  // Catalyst form
  const [showCatForm, setShowCatForm] = useState(false);
  const [catDesc, setCatDesc] = useState('');
  const [catDate, setCatDate] = useState('');
  const [catType, setCatType] = useState('earnings');
  const [addingCat, setAddingCat] = useState(false);

  // Hypothesis edit
  const [editingHyp, setEditingHyp] = useState(false);
  const [hypInput, setHypInput] = useState('');
  const [editingVariant, setEditingVariant] = useState(false);
  const [variantInput, setVariantInput] = useState('');

  useEffect(() => {
    if (onSessionChange) onSessionChange(sessionId);
  }, [sessionId, onSessionChange]);

  // Load sessions on mount
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await apiGet(API_ENDPOINTS.sessions);
        const list = Array.isArray(data) ? data : [];
        setSessions(list);
        if (list.length > 0 && !sessionId) {
          setSessionId(list[0].session_id);
          setTicker(list[0].ticker || '');
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
        // Normalize scenario field names
        const normalizeScenario = (s) => s ? { ...s, price_per_share: s.per_share ?? s.price_per_share } : null;
        if (data.scenarios) {
          data.scenarios = {
            bull: normalizeScenario(data.scenarios.bull),
            base: normalizeScenario(data.scenarios.base),
            bear: normalizeScenario(data.scenarios.bear),
          };
        }
        setResearchData(data);
        if (data.ticker) setTicker(data.ticker);
        // Auto-load DCF if it already exists on the session
        if (data.dcf_output) {
          setDcfData(data.dcf_output);
        }
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchResearchData();
  }, [sessionId]);

  const refreshSession = async () => {
    if (!sessionId) return;
    const data = await apiGet(API_ENDPOINTS.research(sessionId));
    const normalizeScenario = (s) => s ? { ...s, price_per_share: s.per_share ?? s.price_per_share } : null;
    if (data.scenarios) {
      data.scenarios = {
        bull: normalizeScenario(data.scenarios.bull),
        base: normalizeScenario(data.scenarios.base),
        bear: normalizeScenario(data.scenarios.bear),
      };
    }
    setResearchData(data);
    if (data.dcf_output) setDcfData(data.dcf_output);
  };

  // Create session from modal — one click does everything
  const handleCreateSession = async () => {
    if (!modalTicker.trim()) return;
    try {
      setAnalyzing(true);
      setError(null);
      // Single call: creates session + fetches data + runs DCF all at once
      const result = await apiPost(API_ENDPOINTS.researchNew, {
        ticker: modalTicker.toUpperCase(),
        hypothesis: modalHypothesis,
        variant_view: modalVariant,
        sector: modalSector,
      });
      setShowNewModal(false);
      setModalTicker(''); setModalHypothesis(''); setModalVariant(''); setModalSector('auto');

      setSessionId(result.session_id);
      setTicker(result.ticker);

      // Normalize scenarios field names (backend returns per_share, frontend expects price_per_share)
      const normalizeScenario = (s) => s ? { ...s, price_per_share: s.per_share ?? s.price_per_share } : null;
      const scenarios = {
        bull: normalizeScenario(result.scenarios?.bull),
        base: normalizeScenario(result.scenarios?.base),
        bear: normalizeScenario(result.scenarios?.bear),
      };

      // Build researchData from the analyze response directly — no extra API call needed
      setResearchData({
        session_id: result.session_id,
        ticker: result.ticker,
        sector: result.sector,
        status: result.status,
        hypothesis: result.hypothesis || modalHypothesis || `Analysis for ${result.ticker}`,
        variant_view: result.variant_view || modalVariant || '',
        catalysts: [],
        assumptionChanges: [],
        scenarios,
      });

      // Populate DCF panel from the same response
      if (result.dcf_output) {
        setDcfData(result.dcf_output);
      }

      // Refresh sessions list
      const list = await apiGet(API_ENDPOINTS.sessions);
      setSessions(Array.isArray(list) ? list : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // Quick analyze from search bar (opens modal pre-filled)
  const handleAnalyze = () => {
    if (ticker.trim()) {
      setModalTicker(ticker.toUpperCase());
      setShowNewModal(true);
    }
  };

  const handleRunScenarios = async () => {
    if (!sessionId) return;
    try {
      setRunningScenarios(true);
      setError(null);
      await apiPost(API_ENDPOINTS.researchScenarios(sessionId), {});
      await refreshSession();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningScenarios(false);
    }
  };

  const handleAddCatalyst = async () => {
    if (!catDesc.trim() || !sessionId) return;
    try {
      setAddingCat(true);
      await apiPost(`/api/research/${sessionId}/catalyst`, {
        description: catDesc,
        expected_date: catDate || null,
        catalyst_type: catType,
      });
      setCatDesc(''); setCatDate(''); setCatType('earnings');
      setShowCatForm(false);
      await refreshSession();
    } catch (err) {
      console.error('Failed to add catalyst:', err);
    } finally {
      setAddingCat(false);
    }
  };

  const handleSaveHypothesis = async () => {
    if (!hypInput.trim() || !sessionId) return;
    try {
      await apiPost(`/api/research/${sessionId}/thesis`, {
        thesis: hypInput,
        variant_view: researchData?.variant_view || '',
      });
      setEditingHyp(false);
      await refreshSession();
    } catch (err) {
      console.error('Failed to save hypothesis:', err);
    }
  };

  const handleSaveVariant = async () => {
    if (!variantInput.trim() || !sessionId) return;
    try {
      await apiPost(`/api/research/${sessionId}/thesis`, {
        thesis: researchData?.hypothesis || '',
        variant_view: variantInput,
      });
      setEditingVariant(false);
      await refreshSession();
    } catch (err) {
      console.error('Failed to save variant:', err);
    }
  };

  const runDCF = async (version = dcfModelVersion) => {
    const sid = researchData?.session_id;
    if (!sid) return;
    setDcfLoading(true);
    try {
      await apiPost('/api/research/' + sid + '/dcf?model_version=' + version, {});
      setTimeout(() => refreshDCF(sid), 1000);
    } catch (e) { console.error(e); }
    finally { setDcfLoading(false); }
  };
  const refreshDCF = async (sid) => {
    const sessionId = sid || researchData?.session_id;
    if (!sessionId) return;
    try {
      const data = await apiGet('/api/research/' + sessionId + '/dcf');
      if (data?.status !== 'not_run') setDcfData(data);
    } catch (e) { console.error(e); }
  };
  const downloadReport = async () => {
    const sid = researchData?.session_id;
    if (!sid) return;
    setReportLoading(true);
    try {
      const res = await fetch('/api/research/' + sid + '/report/download');
      const html = await res.text();
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = (researchData?.ticker || 'research') + '_report.html';
      a.click(); URL.revokeObjectURL(url);
    } catch (e) { console.error(e); }
    finally { setReportLoading(false); }
  };
  const getScenarios = () => {
    if (!researchData?.scenarios) return [];
    return SCENARIO_KEYS
      .filter(key => researchData.scenarios[key] != null)
      .map(key => ({
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1),
        ...researchData.scenarios[key],
      }));
  };

  return (
    <div className="page-content p-6 space-y-6 overflow-y-auto bg-[#ffffff]" data-testid="research-session-page">

      {/* New Session Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#0f172a]">New Research Session</h2>
              <button onClick={() => setShowNewModal(false)} className="text-[#64748b] hover:text-[#0f172a]">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">Ticker</label>
                <input
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  placeholder="e.g. RELIANCE, HDFCBANK"
                  value={modalTicker}
                  onChange={e => setModalTicker(e.target.value.toUpperCase())}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">Sector</label>
                <select
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  value={modalSector}
                  onChange={e => setModalSector(e.target.value)}
                >
                  <option value="auto">Auto-detect</option>
                  <option value="petroleum">Petroleum / Energy</option>
                  <option value="banking">Banking / NBFC</option>
                  <option value="it">IT / Tech</option>
                  <option value="pharma">Pharma</option>
                  <option value="fmcg">FMCG</option>
                  <option value="real_estate">Real Estate</option>
                  <option value="auto_sector">Auto</option>
                  <option value="universal">Universal</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">
                  Hypothesis <span className="normal-case font-normal text-[#94a3b8]">— your research question</span>
                </label>
                <textarea
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb] resize-none"
                  rows={2}
                  placeholder="e.g. RELIANCE undervalued — GRM recovery not priced in"
                  value={modalHypothesis}
                  onChange={e => setModalHypothesis(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">
                  Variant View <span className="normal-case font-normal text-[#94a3b8]">— what you see that consensus doesn't</span>
                </label>
                <input
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  placeholder="e.g. Consensus uses $6/bbl GRM; we model $9/bbl"
                  value={modalVariant}
                  onChange={e => setModalVariant(e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setShowNewModal(false)}
                className="px-4 py-2 text-sm text-[#64748b] border border-[#e5e7eb] rounded-lg hover:bg-[#f8fafc]"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSession}
                disabled={!modalTicker.trim() || analyzing}
                className="px-4 py-2 text-sm bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] disabled:opacity-50 flex items-center gap-2"
              >
                {analyzing && <Loader2 className="w-4 h-4 animate-spin" />}
                {analyzing ? 'Analyzing...' : 'Start Analysis'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ticker Input + Sessions Row */}
      <section className="flex items-center gap-3" data-testid="ticker-input-section">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === 'Enter') handleAnalyze(); }}
            placeholder="Enter ticker symbol (e.g., RELIANCE, TCS, IRFC)"
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
        <button
          onClick={() => { setModalTicker(''); setShowNewModal(true); }}
          className="p-2.5 border border-[#e5e7eb] rounded-lg hover:bg-[#f8fafc] text-[#64748b] hover:text-[#0f172a]"
          title="New session"
        >
          <Plus className="w-4 h-4" />
        </button>
      </section>

      {/* Past sessions chips */}
      {sessions.length > 0 && (
        <section className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-[#94a3b8]">Recent:</span>
          {sessions.slice(0, 6).map(s => (
            <button
              key={s.session_id}
              onClick={() => { setSessionId(s.session_id); setTicker(s.ticker || ''); }}
              className={cn(
                "px-3 py-1 text-xs rounded-full border transition-colors",
                s.session_id === sessionId
                  ? "bg-[#2563eb] text-white border-[#2563eb]"
                  : "bg-[#f8fafc] text-[#64748b] border-[#e5e7eb] hover:border-[#2563eb] hover:text-[#2563eb]"
              )}
            >
              {s.ticker}
            </button>
          ))}
        </section>
      )}

      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm">{error}</div>
      )}

      {/* Info Bar */}
      {researchData && (
        <section className="flex items-center gap-4 text-sm" data-testid="info-bar">
          <span className="text-[#0f172a] font-medium">{researchData.ticker}</span>
          <span className="text-[#94a3b8]">|</span>
          <span className="text-[#64748b]">{researchData.sector || 'N/A'}</span>
          <span className="text-[#94a3b8]">|</span>
          <span className="text-[#64748b]">Session: {(researchData.session_id || sessionId || '').slice(-12)}</span>
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
          {/* Price Chart */}
          {researchData.ticker && (
            <section className="dashboard-card">
              <PriceChart ticker={researchData.ticker} />
            </section>
          )}

          {/* Main Grid */}
          <section className="grid grid-cols-2 gap-6" data-testid="research-content">
            {/* Left Column */}
            <div className="space-y-6">

              {/* Hypothesis */}
              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">Hypothesis</h3>
                  <button
                    onClick={() => { setHypInput(researchData.hypothesis || ''); setEditingHyp(!editingHyp); }}
                    className="text-xs text-[#2563eb] hover:underline"
                  >
                    {editingHyp ? 'cancel' : 'edit'}
                  </button>
                </div>
                {editingHyp ? (
                  <div className="space-y-2">
                    <textarea
                      className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb] resize-none"
                      rows={2}
                      value={hypInput}
                      onChange={e => setHypInput(e.target.value)}
                    />
                    <button
                      onClick={handleSaveHypothesis}
                      className="px-3 py-1.5 text-xs bg-[#2563eb] text-white rounded-md hover:bg-[#1d4ed8]"
                    >
                      Save
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-[#0f172a] leading-relaxed">
                    {researchData.hypothesis || <span className="text-[#94a3b8] italic">No hypothesis set — click edit to add one</span>}
                  </p>
                )}
              </div>

              {/* Variant View */}
              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">Variant View</h3>
                  <button
                    onClick={() => { setVariantInput(researchData.variant_view || ''); setEditingVariant(!editingVariant); }}
                    className="text-xs text-[#2563eb] hover:underline"
                  >
                    {editingVariant ? 'cancel' : 'edit'}
                  </button>
                </div>
                {editingVariant ? (
                  <div className="space-y-2">
                    <input
                      className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                      value={variantInput}
                      onChange={e => setVariantInput(e.target.value)}
                      placeholder="What do you see that consensus doesn't?"
                    />
                    <button
                      onClick={handleSaveVariant}
                      className="px-3 py-1.5 text-xs bg-[#2563eb] text-white rounded-md hover:bg-[#1d4ed8]"
                    >
                      Save
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-[#0f172a] leading-relaxed">
                    {researchData.variant_view || <span className="text-[#94a3b8] italic">No variant view set</span>}
                  </p>
                )}
              </div>

              {/* Catalysts */}
              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">Catalysts</h3>
                  <button
                    onClick={() => setShowCatForm(!showCatForm)}
                    className="flex items-center gap-1 text-xs text-[#2563eb] hover:underline"
                  >
                    <Plus className="w-3 h-3" /> Add
                  </button>
                </div>

                {showCatForm && (
                  <div className="mb-3 p-3 bg-[#f8fafc] rounded-lg border border-[#e5e7eb] space-y-2">
                    <input
                      className="w-full border border-[#e5e7eb] rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
                      placeholder="Catalyst description…"
                      value={catDesc}
                      onChange={e => setCatDesc(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <input
                        type="date"
                        className="flex-1 border border-[#e5e7eb] rounded px-2 py-1.5 text-xs focus:outline-none"
                        value={catDate}
                        onChange={e => setCatDate(e.target.value)}
                      />
                      <select
                        className="flex-1 border border-[#e5e7eb] rounded px-2 py-1.5 text-xs focus:outline-none"
                        value={catType}
                        onChange={e => setCatType(e.target.value)}
                      >
                        <option value="earnings">Earnings</option>
                        <option value="regulatory">Regulatory</option>
                        <option value="macro">Macro</option>
                        <option value="corporate">Corporate</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleAddCatalyst}
                        disabled={!catDesc.trim() || addingCat}
                        className="px-3 py-1.5 text-xs bg-[#2563eb] text-white rounded hover:bg-[#1d4ed8] disabled:opacity-50 flex items-center gap-1"
                      >
                        {addingCat && <Loader2 className="w-3 h-3 animate-spin" />}
                        Log
                      </button>
                      <button onClick={() => setShowCatForm(false)} className="px-3 py-1.5 text-xs border border-[#e5e7eb] rounded hover:bg-[#f1f5f9]">
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  {(researchData.catalysts || []).map((cat, idx) => (
                    <div key={idx} className="flex items-start justify-between p-3 bg-[#f1f5f9] rounded-lg">
                      <div>
                        <p className="text-sm text-[#0f172a]">{cat.description || cat.event}</p>
                        <p className="text-xs text-[#64748b] mt-0.5">
                          {cat.type || cat.catalyst_type || 'event'} · {cat.expected_date || cat.timeline || 'TBD'}
                        </p>
                      </div>
                      <StatusBadge variant="info">{cat.type || 'event'}</StatusBadge>
                    </div>
                  ))}
                  {(!researchData.catalysts || researchData.catalysts.length === 0) && (
                    <p className="text-sm text-[#64748b]">No catalysts logged yet</p>
                  )}
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              {/* Scenario Analysis */}
              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">Scenario Analysis</h3>
                  <button
                    onClick={handleRunScenarios}
                    disabled={!sessionId || runningScenarios}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#2563eb] text-white rounded-md hover:bg-[#1d4ed8] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="run-scenarios-btn"
                  >
                    {runningScenarios ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    {runningScenarios ? 'Running...' : 'Run Scenarios'}
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {getScenarios().length > 0 ? (
                    getScenarios().map((scenario) => (
                      <div
                        key={scenario.key}
                        className={cn(
                          "px-4 py-3 rounded-lg border",
                          scenario.key === 'bull' ? 'bg-[#16a34a]/10 border-[#16a34a]' :
                          scenario.key === 'bear' ? 'bg-[#dc2626]/10 border-[#dc2626]' :
                          'bg-[#2563eb]/10 border-[#2563eb]'
                        )}
                        data-testid={`scenario-badge-${scenario.key}`}
                      >
                        <p className={cn("text-xs uppercase tracking-wider font-medium",
                          scenario.key === 'bull' ? 'text-[#16a34a]' :
                          scenario.key === 'bear' ? 'text-[#dc2626]' : 'text-[#2563eb]')}>
                          {scenario.label}
                        </p>
                        <p className={cn("text-lg font-semibold font-outfit mt-1",
                          scenario.key === 'bull' ? 'text-[#16a34a]' :
                          scenario.key === 'bear' ? 'text-[#dc2626]' : 'text-[#2563eb]')}>
                          ₹{typeof scenario.price_per_share === 'number' ? scenario.price_per_share.toFixed(2) : scenario.price_per_share ?? 'N/A'}
                        </p>
                        <p className={cn("text-sm",
                          scenario.key === 'bull' ? 'text-[#16a34a]' :
                          scenario.key === 'bear' ? 'text-[#dc2626]' : 'text-[#2563eb]')}>
                          {typeof scenario.upside_pct === 'number' ? `${scenario.upside_pct >= 0 ? '+' : ''}${scenario.upside_pct.toFixed(1)}%` : 'N/A'}
                        </p>
                        {scenario.rating && (
                          <span className={cn("inline-block mt-2 px-2 py-0.5 text-xs font-medium rounded",
                            scenario.rating === 'BUY' ? 'bg-[#16a34a]/20 text-[#16a34a]' :
                            scenario.rating === 'SELL' ? 'bg-[#dc2626]/20 text-[#dc2626]' :
                            'bg-[#d97706]/20 text-[#d97706]')}>
                            {scenario.rating}
                          </span>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-[#64748b] col-span-3">Click "Run Scenarios" to generate analysis</p>
                  )}
                </div>
              </div>

              {/* DCF Valuation Cards */}
              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">DCF Valuation</h3>
                  <div className="flex items-center gap-2">
                    <select value={dcfModelVersion} onChange={e => setDcfModelVersion(e.target.value)} className="text-xs bg-[#f8fafc] border border-[#e5e7eb] rounded px-2 py-1">
                      <option value="base">Base</option>
                      <option value="analyst">Analyst</option>
                      <option value="data_driven">Data-Driven</option>
                    </select>
                    <button onClick={() => runDCF()} disabled={dcfLoading} className="flex items-center gap-1 bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg">
                      {dcfLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                      {dcfLoading ? 'Running...' : 'Run DCF'}
                    </button>
                    <button onClick={() => refreshDCF()} className="text-xs bg-[#f1f5f9] text-[#64748b] px-2 py-1.5 rounded-lg">↻</button>
                    <button onClick={downloadReport} disabled={reportLoading} className="flex items-center gap-1 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg">
                      {reportLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : '📄'}
                      {reportLoading ? 'Loading...' : 'Report'}
                    </button>
                  </div>
                </div>
                {!dcfData || dcfData.status === 'not_run' ? (
                  <div className="text-center py-4 text-xs text-[#94a3b8]">
                    <p>Click Run DCF → Run notebook → Click ↻ Refresh</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    {['bull','base','bear'].map(label => {
                      const s = dcfData.scenarios?.[label] || {};
                      const cols = {bull:'#16a34a',base:'#2563eb',bear:'#dc2626'};
                      const bgs = {bull:'#f0fdf4',base:'#eff6ff',bear:'#fef2f2'};
                      return (
                        <div key={label} style={{borderColor:cols[label],backgroundColor:bgs[label]}} className="border rounded-lg p-3 text-center">
                          <div style={{color:cols[label]}} className="text-xs font-bold uppercase mb-1">{label}</div>
                          <div className="text-lg font-bold text-[#0f172a]">{s.per_share ? '₹'+Number(s.per_share).toFixed(0) : 'N/A'}</div>
                          <div style={{color:cols[label]}} className="text-xs mt-1">{s.upside_pct != null ? (s.upside_pct > 0 ? '+' : '')+Number(s.upside_pct).toFixed(1)+'%' : ''}</div>
                          <div className="text-xs text-[#64748b] mt-1">{s.rating || ''}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Reverse DCF */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-2">Reverse DCF</h3>
                <p className="text-sm text-[#0f172a] leading-relaxed">
                  {dcfData?.reverse_dcf ? (
                  <div>
                    <p className="text-sm text-[#0f172a]">Market pricing in <span className="font-bold text-[#d97706]">{dcfData.reverse_dcf.implied_growth_rate}% growth</span></p>
                    <p className="text-xs text-[#64748b] mt-1">{dcfData.reverse_dcf.interpretation}</p>
                  </div>
                ) : <p className="text-sm text-[#94a3b8]">Run DCF to see implied market assumptions</p>}
                </p>
              </div>

              {/* Sensitivity Table */}
              <div className="dashboard-card">
                <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider mb-3">Sensitivity Analysis</h3>
                {dcfData?.sensitivity_table?.wacc_vs_growth?.matrix?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead><tr>
                        <th className="text-[#94a3b8] p-1 text-left">WACC</th>
                        {dcfData.sensitivity_table.wacc_vs_growth.cols.map(c => <th key={c} className="text-[#64748b] p-1 text-center">{c}</th>)}
                      </tr></thead>
                      <tbody>
                        {dcfData.sensitivity_table.wacc_vs_growth.rows.map((row, ri) => (
                          <tr key={row}>
                            <td className="text-[#64748b] p-1 font-semibold">{row}</td>
                            {dcfData.sensitivity_table.wacc_vs_growth.matrix[ri].map((val, ci) => {
                              const cp = dcfData.current_price;
                              const up = cp && val ? ((val - cp) / cp * 100) : null;
                              const bg = up == null ? '#f1f5f9' : up > 20 ? '#dcfce7' : up > 0 ? '#fef9c3' : '#fee2e2';
                              const tc = up == null ? '#94a3b8' : up > 20 ? '#16a34a' : up > 0 ? '#d97706' : '#dc2626';
                              return <td key={ci} className="p-1 text-center rounded" style={{backgroundColor:bg,color:tc}}>{val ? '₹'+Math.round(val) : '—'}</td>;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="grid grid-cols-5 gap-1" data-testid="sensitivity-table">
                    {[...Array(25)].map((_, idx) => (
                      <div key={idx} className="aspect-square bg-[#f1f5f9] border border-[#e5e7eb] rounded flex items-center justify-center text-xs text-[#94a3b8]">{idx === 12 ? '●' : ''}</div>
                    ))}
                  </div>
                )}
                <p className="text-xs text-[#94a3b8] mt-2 text-center">WACC vs Terminal Growth</p>
              </div>
            </div>
          </section>

          {/* Assumption Changes */}
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
