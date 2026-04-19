import { useState, useEffect, useRef } from 'react';
import { Search, Loader2, Play, Plus, X, TrendingUp } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DataTable } from '@/components/ui/DataTable';
import { apiGet, apiPost, API_ENDPOINTS } from '@/services/api';
import { cn } from '@/lib/utils';

const SCENARIO_KEYS = ['bull', 'base', 'bear'];

// Guard: reject invalid session IDs that have caused 404s in the past
const isValidSessionId = (id) =>
  !!id && typeof id === 'string' && id !== 'undefined' && id !== 'null' && id.length > 2;

// Unwrap backend list responses — supports both shapes: [..] and {sessions: [..]}
const unwrapList = (raw, key) => {
  if (Array.isArray(raw)) return raw;
  if (raw && Array.isArray(raw[key])) return raw[key];
  return [];
};

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
const PriceChart = ({ ticker, livePrice }) => {
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

  // Fallback: if no chart data but we have a live price, show the price card
  if (!loading && chartData.length === 0 && livePrice != null) {
    return (
      <div className="h-24 flex flex-col items-center justify-center">
        <span className="text-xs text-[#64748b] uppercase tracking-wider">Current Price</span>
        <span className="text-2xl font-bold text-[#0f172a] mt-1">
          ₹{typeof livePrice === 'number' ? livePrice.toFixed(2) : livePrice}
        </span>
      </div>
    );
  }

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

export const ResearchSession = ({ onSessionChange, pendingTicker }) => {
  const [ticker, setTicker] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [researchData, setResearchData] = useState(null);
  const [dcfData, setDcfData] = useState(null);
  const [dcfLoading, setDcfLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [xlsmState, setXlsmState] = useState('idle'); // idle | running | error
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [runningScenarios, setRunningScenarios] = useState(false);
  const [error, setError] = useState(null);

  // Auto-trigger analyze when a ticker is routed in from another page
  useEffect(() => {
    if (pendingTicker?.ticker) {
      handleAnalyze(pendingTicker.ticker);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingTicker?.nonce]);

  // Modal state (optional — Analyze button now works without opening modal)
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
        const list = unwrapList(data, 'sessions');
        setSessions(list);
      } catch (err) {
        console.error('Failed to fetch sessions:', err);
      }
    };
    fetchSessions();
  }, []);

  // Fetch research data when sessionId changes — GUARDED against invalid IDs
  useEffect(() => {
    if (!isValidSessionId(sessionId)) return;
    const fetchResearchData = async () => {
      try {
        setLoading(true);
        const data = await apiGet(API_ENDPOINTS.research(sessionId));
        // If backend returned a not-found skeleton, don't overwrite current state
        if (data && data.status === 'not_found') {
          console.warn('Session not found:', sessionId);
          setError(null);
          return;
        }
        setResearchData(data);
        if (data.ticker && data.ticker !== 'UNKNOWN') setTicker(data.ticker);
        if (data.dcf_output && data.dcf_output.status === 'complete') {
          setDcfData(data.dcf_output);
        } else if (data.dcf) {
          // Our hardened backend's analyze endpoint returns .dcf directly
          setDcfData({
            status: 'complete',
            current_price: data.dcf.current_price,
            scenarios: {
              base: { per_share: data.dcf.fair_value, upside_pct: data.dcf.upside_pct, rating: data.dcf.upside_pct > 15 ? 'BUY' : data.dcf.upside_pct < -15 ? 'SELL' : 'HOLD' }
            },
          });
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
    if (!isValidSessionId(sessionId)) return;
    const data = await apiGet(API_ENDPOINTS.research(sessionId));
    setResearchData(data);
    if (data.dcf_output && data.dcf_output.status === 'complete') {
      setDcfData(data.dcf_output);
    }
  };

  // Primary Analyze action — one click, no modal, calls /api/research/analyze directly
  const handleAnalyze = async (overrideTicker) => {
    const t = (overrideTicker ?? ticker).trim().toUpperCase();
    if (!t) return;
    if (overrideTicker) setTicker(t);
    try {
      setAnalyzing(true);
      setError(null);
      const result = await apiPost(API_ENDPOINTS.researchAnalyze, { ticker: t });
      // Guard: if no session_id came back, show error instead of breaking
      if (!result || !result.session_id) {
        setError('Backend did not return a session ID');
        return;
      }
      // Use the response directly as researchData (it has all fields)
      setResearchData(result);
      setSessionId(result.session_id);
      if (result.dcf) {
        setDcfData({
          status: 'complete',
          current_price: result.dcf.current_price,
          scenarios: {
            base: {
              per_share: result.dcf.fair_value,
              upside_pct: result.dcf.upside_pct,
              rating: result.dcf.upside_pct > 15 ? 'BUY' : result.dcf.upside_pct < -15 ? 'SELL' : 'HOLD'
            }
          },
        });
      }
      // Refresh session list
      try {
        const list = await apiGet(API_ENDPOINTS.sessions);
        setSessions(unwrapList(list, 'sessions'));
      } catch (_) {}
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // Full-form creation via modal (for users who want to add hypothesis etc.)
  const handleCreateSession = async () => {
    if (!modalTicker.trim()) return;
    try {
      setAnalyzing(true);
      setError(null);
      const result = await apiPost(API_ENDPOINTS.researchAnalyze, {
        ticker: modalTicker.toUpperCase(),
        hypothesis: modalHypothesis,
        variant_view: modalVariant,
        sector: modalSector,
      });
      setShowNewModal(false);
      setModalTicker(''); setModalHypothesis(''); setModalVariant(''); setModalSector('auto');
      if (!result || !result.session_id) {
        setError('Backend did not return a session ID');
        return;
      }
      setResearchData(result);
      setSessionId(result.session_id);
      setTicker(result.ticker || '');
      if (result.dcf) {
        setDcfData({
          status: 'complete',
          current_price: result.dcf.current_price,
          scenarios: {
            base: { per_share: result.dcf.fair_value, upside_pct: result.dcf.upside_pct, rating: 'HOLD' }
          },
        });
      }
      const list = await apiGet(API_ENDPOINTS.sessions);
      setSessions(unwrapList(list, 'sessions'));
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRunScenarios = async () => {
    if (!isValidSessionId(sessionId)) return;
    try {
      setRunningScenarios(true);
      setError(null);
      await apiPost(`/api/research/${sessionId}/dcf`, {});
      const data = await apiGet(API_ENDPOINTS.research(sessionId));
      setResearchData(data);
      if (data.dcf_output && data.dcf_output.status === 'complete') {
        setDcfData(data.dcf_output);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningScenarios(false);
    }
  };

  const handleAddCatalyst = async () => {
    if (!catDesc.trim() || !isValidSessionId(sessionId)) return;
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
    if (!hypInput.trim() || !isValidSessionId(sessionId)) return;
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
    if (!variantInput.trim() || !isValidSessionId(sessionId)) return;
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

  const runDCF = async () => {
    const sid = researchData?.session_id || sessionId;
    if (!isValidSessionId(sid)) return;
    setDcfLoading(true);
    try {
      await apiPost(`/api/research/${sid}/dcf`, {});
      const data = await apiGet(API_ENDPOINTS.research(sid));
      setResearchData(data);
      if (data.dcf_output && data.dcf_output.status === 'complete') {
        setDcfData(data.dcf_output);
      }
    } catch (e) { console.error('DCF error:', e); }
    finally { setDcfLoading(false); }
  };

  const refreshDCF = async () => {
    const sid = researchData?.session_id || sessionId;
    if (!isValidSessionId(sid)) return;
    try {
      const data = await apiGet(API_ENDPOINTS.research(sid));
      if (data.dcf_output && data.dcf_output.status === 'complete') {
        setDcfData(data.dcf_output);
      }
    } catch (e) { console.error(e); }
  };

  const downloadDcfExcel = async () => {
    const sid = researchData?.session_id || sessionId;
    const tk = researchData?.ticker || ticker;
    if (!isValidSessionId(sid) || !tk) return;

    const triggerDownload = (url) => {
      const a = document.createElement('a');
      a.href = url;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
    };

    setXlsmState('running');
    try {
      const initial = await apiGet(`/api/research/${sid}/dcf/status`);
      if (initial.status === 'complete' && initial.download_url) {
        triggerDownload(initial.download_url);
        setXlsmState('idle');
        return;
      }

      if (initial.status !== 'running') {
        await apiPost(`/api/research/${sid}/dcf/run`, { ticker: tk });
      }

      const deadline = Date.now() + 10 * 60 * 1000;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 3000));
        const s = await apiGet(`/api/research/${sid}/dcf/status`);
        if (s.status === 'complete' && s.download_url) {
          triggerDownload(s.download_url);
          setXlsmState('idle');
          return;
        }
        if (s.status === 'error' || s.status === 'failed') {
          throw new Error(s.error || 'DCF run failed');
        }
      }
      throw new Error('Timed out waiting for DCF');
    } catch (e) {
      console.error('DCF xlsm download error:', e);
      setXlsmState('error');
    }
  };

  const downloadReport = async () => {
    const sid = researchData?.session_id;
    if (!isValidSessionId(sid)) return;
    setReportLoading(true);
    try {
      const res = await fetch(`/api/research/${sid}/report/download`);
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
    const src = (dcfData?.scenarios && Object.keys(dcfData.scenarios).length > 0)
      ? dcfData.scenarios
      : researchData?.scenarios;
    if (!src) return [];
    return SCENARIO_KEYS
      .filter(key => src[key] != null)
      .map(key => ({
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1),
        ...src[key],
        price_per_share: src[key]?.per_share ?? src[key]?.price_per_share,
      }));
  };

  // Pick the best available price from the response (tries every field name)
  const livePrice = researchData?.price ?? researchData?.ltp ?? researchData?.last_price
    ?? researchData?.current_price ?? researchData?.dcf?.current_price
    ?? researchData?.price_data?.price;
  const liveChangePct = researchData?.change_percent ?? researchData?.change_pct
    ?? researchData?.price_data?.change_pct;

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
                  Hypothesis
                </label>
                <textarea
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb] resize-none"
                  rows={2}
                  value={modalHypothesis}
                  onChange={e => setModalHypothesis(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">
                  Variant View
                </label>
                <input
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
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
          onClick={() => { setModalTicker(ticker); setShowNewModal(true); }}
          className="p-2.5 border border-[#e5e7eb] rounded-lg hover:bg-[#f8fafc] text-[#64748b] hover:text-[#0f172a]"
          title="New session with full form"
        >
          <Plus className="w-4 h-4" />
        </button>
      </section>

      {/* Past sessions chips — deduplicated */}
      {sessions.length > 0 && (() => {
        const seen = new Set();
        const unique = sessions.filter(s => {
          if (!s.ticker || seen.has(s.ticker)) return false;
          seen.add(s.ticker);
          return true;
        });
        return (
          <section className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-[#94a3b8]">Recent:</span>
            {unique.slice(0, 8).map(s => (
              <button
                key={s.session_id || s._id}
                onClick={() => { setSessionId(s.session_id); setTicker(s.ticker || ''); }}
                className={cn(
                  "px-3 py-1 text-xs rounded-full border transition-colors",
                  (s.session_id || s._id) === sessionId
                    ? "bg-[#2563eb] text-white border-[#2563eb]"
                    : "bg-[#f8fafc] text-[#64748b] border-[#e5e7eb] hover:border-[#2563eb] hover:text-[#2563eb]"
                )}
              >
                {s.ticker}
              </button>
            ))}
          </section>
        );
      })()}

      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm">{error}</div>
      )}

      {/* Info Bar */}
      {researchData && researchData.status !== 'not_found' && (
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
      ) : researchData && researchData.status !== 'not_found' ? (
        <>
          {/* Price Chart or current-price card */}
          {researchData.ticker && (
            <section className="dashboard-card">
              <PriceChart ticker={researchData.ticker} livePrice={livePrice} />
              {livePrice != null && liveChangePct != null && (
                <div className="mt-2 text-xs flex items-center gap-2">
                  <span className={cn("font-medium", liveChangePct >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]')}>
                    {liveChangePct >= 0 ? '▲' : '▼'} {liveChangePct.toFixed(2)}%
                  </span>
                  <span className="text-[#94a3b8]">vs prev close</span>
                </div>
              )}
            </section>
          )}

          {/* Main Grid */}
          <section className="grid grid-cols-2 gap-6" data-testid="research-content">
            {/* Left Column */}
            <div className="space-y-6">
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
                    >Save</button>
                  </div>
                ) : (
                  <p className="text-sm text-[#0f172a] leading-relaxed">
                    {researchData.hypothesis || <span className="text-[#94a3b8] italic">No hypothesis set</span>}
                  </p>
                )}
              </div>

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
                    />
                    <button
                      onClick={handleSaveVariant}
                      className="px-3 py-1.5 text-xs bg-[#2563eb] text-white rounded-md hover:bg-[#1d4ed8]"
                    >Save</button>
                  </div>
                ) : (
                  <p className="text-sm text-[#0f172a] leading-relaxed">
                    {researchData.variant_view || <span className="text-[#94a3b8] italic">No variant view set</span>}
                  </p>
                )}
              </div>

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
                        {addingCat && <Loader2 className="w-3 h-3 animate-spin" />} Log
                      </button>
                      <button onClick={() => setShowCatForm(false)} className="px-3 py-1.5 text-xs border border-[#e5e7eb] rounded hover:bg-[#f1f5f9]">Cancel</button>
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
              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">Scenario Analysis</h3>
                  <button
                    onClick={handleRunScenarios}
                    disabled={!isValidSessionId(sessionId) || runningScenarios}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#2563eb] text-white rounded-md hover:bg-[#1d4ed8] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {runningScenarios ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    {runningScenarios ? 'Running...' : 'Run Scenarios'}
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {getScenarios().length > 0 ? (
                    getScenarios().map((scenario) => (
                      <div key={scenario.key} className={cn("px-4 py-3 rounded-lg border",
                        scenario.key === 'bull' ? 'bg-[#16a34a]/10 border-[#16a34a]' :
                        scenario.key === 'bear' ? 'bg-[#dc2626]/10 border-[#dc2626]' :
                        'bg-[#2563eb]/10 border-[#2563eb]')}>
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
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-[#64748b] col-span-3">Click "Run Scenarios" to generate analysis</p>
                  )}
                </div>
              </div>

              <div className="dashboard-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-[#64748b] uppercase tracking-wider">DCF Valuation</h3>
                  <div className="flex items-center gap-2">
                    <button onClick={runDCF} disabled={dcfLoading} className="flex items-center gap-1 bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg">
                      {dcfLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                      {dcfLoading ? 'Running...' : 'Run DCF'}
                    </button>
                    <button
  onClick={async () => {
    const sid = researchData?.session_id;
    if (!sid) return;
    window.open(`/api/research/${sid}/report/xlsx`, '_blank');
  }}
  className="flex items-center gap-1 bg-[#16a34a] hover:bg-[#15803d] text-white text-xs px-3 py-1.5 rounded-lg"
>
  📊 Excel
</button>
                    <button
                      onClick={downloadDcfExcel}
                      disabled={xlsmState === 'running'}
                      className="flex items-center gap-1 bg-[#0f766e] hover:bg-[#115e59] disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg"
                    >
                      {xlsmState === 'running' ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                      {xlsmState === 'running'
                        ? 'Generating…'
                        : xlsmState === 'error'
                        ? 'Failed — Retry'
                        : 'Download DCF Excel'}
                    </button>
                    <button onClick={refreshDCF} className="text-xs bg-[#f1f5f9] text-[#64748b] px-2 py-1.5 rounded-lg">↻</button>
                    <button onClick={downloadReport} disabled={reportLoading} className="flex items-center gap-1 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg">
                      {reportLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : '📄'}
                      {reportLoading ? 'Loading...' : 'Report'}
                    </button>
                  </div>
                </div>
                {!dcfData || dcfData.status === 'not_run' ? (
                  <div className="text-center py-4 text-xs text-[#94a3b8]">
                    <p>Click <b>Run DCF</b> to generate valuation</p>
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
            </div>
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
