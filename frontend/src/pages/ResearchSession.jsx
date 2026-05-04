import { useState, useEffect, useRef, useMemo } from 'react';
import { validateTicker } from '@/lib/ticker';
import {
  Search, Loader2, Plus, X, AlertTriangle, CheckCircle2,
} from 'lucide-react';
import { apiGet, apiPost, API_ENDPOINTS } from '@/services/api';
import { cn } from '@/lib/utils';
import SWOTPanel from '@/components/research/SWOTPanel';
import PorterPanel from '@/components/research/PorterPanel';
import SectorCallout from '@/components/research/SectorCallout';
import CommandCenterLoader from '@/components/research/CommandCenterLoader'
import WarRoomReport from '@/components/research/WarRoomReport';

const SCENARIO_KEYS = ['bull', 'base', 'bear'];

const isValidSessionId = (id) =>
  !!id && typeof id === 'string' && id !== 'undefined' && id !== 'null' && id.length > 2;

const unwrapList = (raw, key) => {
  if (Array.isArray(raw)) return raw;
  if (raw && Array.isArray(raw[key])) return raw[key];
  return [];
};

// ─── formatting helpers ────────────────────────────────────────────────────
const CURRENCY_SYMBOLS = { INR: '₹', USD: '$', GBP: '£', EUR: '€', JPY: '¥', HKD: 'HK$', AUD: 'A$' };

const getCurrencySymbol = (currency) =>
  CURRENCY_SYMBOLS[currency] || currency || '₹';

const fmtCurrency = (n, sym) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return sym + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
};
const fmtCurrency2 = (n, sym) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return sym + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const fmtLargeCurrency = (n, sym) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  if (v >= 1e12) return `${sym}${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9)  return `${sym}${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6)  return `${sym}${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3)  return `${sym}${(v / 1e3).toFixed(1)}K`;
  return `${sym}${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
};

// Legacy INR wrappers — used where currency is not yet threaded through
const fmtInr = (n) => fmtCurrency(n, '₹');
const fmtInr2 = (n) => fmtCurrency2(n, '₹');
const fmtLargeInr = (n) => fmtLargeCurrency(n, '₹');

const fmtPct = (n, digits = 1) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  return `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`;
};
const fmtPctPlain = (n, digits = 1) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return `${Number(n).toFixed(digits)}%`;
};

const normalizeRating = (r) => {
  if (!r) return null;
  const s = String(r).toLowerCase();
  if (s.includes('buy')) return 'Buy';
  if (s.includes('sell')) return 'Sell';
  if (s.includes('avoid')) return 'Avoid';
  if (s.includes('hold')) return 'Hold';
  return String(r).charAt(0).toUpperCase() + String(r).slice(1).toLowerCase();
};
const ratingStyle = (rating) => {
  const map = {
    Buy:   { bg: 'rgba(15,122,62,0.10)',  fg: '#0F7A3E' },
    Hold:  { bg: 'rgba(107,122,147,0.12)', fg: '#4B5A75' },
    Sell:  { bg: 'rgba(199,55,47,0.10)',  fg: '#C7372F' },
    Avoid: { bg: 'rgba(199,55,47,0.10)',  fg: '#C7372F' },
  };
  return map[rating] || map.Hold;
};

// ─── shared panel shell ────────────────────────────────────────────────────
const panelStyle = {
  backgroundColor: 'var(--bi-bg-card, #FFFFFF)',
  border: '1px solid var(--bi-border-subtle, #E2E7EF)',
  borderRadius: 10,
  padding: 14,
  boxShadow: 'var(--bi-shadow-card, 0 1px 2px rgba(15,37,64,0.04))',
};
const titleStyle = {
  fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
  textTransform: 'uppercase', color: 'var(--bi-text-secondary, #4B5A75)',
};
const emptyStyle = {
  fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)',
  textAlign: 'center', padding: '24px 0',
};
const dividerStyle = {
  height: 1, background: 'var(--bi-border-subtle, #E2E7EF)', margin: '10px 0',
};
const Panel = ({ title, children, className, testId, minH }) => (
  <div className={className} style={{ ...panelStyle, minHeight: minH }} data-testid={testId}>
    {title && <div style={{ ...titleStyle, marginBottom: 10 }}>{title}</div>}
    {children}
  </div>
);

// ─── Panel 1 — Company header ──────────────────────────────────────────────
const CompanyHeader = ({
  researchData, livePrice, liveChangePct,
  onDownloadExcel, xlsmState, onDownloadPdf, reportLoading,
  sessionId,
}) => {
  const ticker = researchData?.ticker || '—';
  const name = researchData?.long_name || researchData?.name || researchData?.company_name || '';
  const sector = researchData?.sector || '—';
  const sid = (researchData?.session_id || '').slice(-12);
  const status = researchData?.status || 'Active';
  const sym = getCurrencySymbol(researchData?.currency);
  const priceMissing = livePrice == null || livePrice === 0;
  const changeMissing = liveChangePct == null || liveChangePct === 0;
  const changeColor = 'var(--bi-navy-700, #1B3A6B)';
  const nowIst = new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  });

  return (
    <div style={panelStyle} data-testid="panel-company-header">
      <div className="flex items-center justify-between gap-6" style={{ flexWrap: 'wrap' }}>
        {/* Left — identity */}
        <div style={{ minWidth: 220 }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--bi-text-primary, #0F2540)',
                        letterSpacing: '-0.01em', lineHeight: 1.1 }}>
            {ticker}
          </div>
          {name && (
            <div style={{ fontSize: 14, color: 'var(--bi-text-secondary, #4B5A75)', marginTop: 2 }}>
              {name}
            </div>
          )}
          <div style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)', marginTop: 4,
                        display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span>{sector}</span>
            <span>·</span>
            <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
              {sid || '—'}
            </span>
            <span style={{
              display: 'inline-block', padding: '1px 8px', borderRadius: 999,
              fontSize: 11, fontWeight: 600,
              backgroundColor: 'rgba(15,122,62,0.10)', color: '#0F7A3E',
            }}>
              {String(status).toUpperCase()}
            </span>
          </div>
        </div>

        {/* Middle — price */}
        <div style={{ textAlign: 'right', minWidth: 160 }}>
          <div style={{ fontSize: 28, fontWeight: 600, color: 'var(--bi-text-primary, #0F2540)',
                        fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}>
            {priceMissing ? '—' : fmtCurrency2(livePrice, sym)}
          </div>
          <div style={{ fontSize: 13, color: changeColor, marginTop: 2, fontVariantNumeric: 'tabular-nums' }}>
            {changeMissing ? '—' :
              `${liveChangePct >= 0 ? '▲' : '▼'} ${Math.abs(liveChangePct).toFixed(2)}%`}
          </div>
          <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', marginTop: 4 }}>
            As of {nowIst} IST
          </div>
        </div>

        {/* Right — actions */}
        <div className="flex items-center" style={{ gap: 8 }}>
          <button
            onClick={onDownloadExcel}
            disabled={xlsmState === 'running'}
            className="flex items-center gap-1.5 disabled:opacity-50"
            style={{
              height: 36, padding: '0 16px', borderRadius: 6,
              backgroundColor: '#0F3D2E',
              color: '#ffffff', fontSize: 13, fontWeight: 500,
              border: '1px solid #0F3D2E',
            }}
            data-testid="header-download-excel"
          >
            {xlsmState === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
            {xlsmState === 'running' ? 'Generating…'
              : xlsmState === 'error' ? 'Retry Excel'
              : 'Download Excel'}
          </button>
          <button
            onClick={onDownloadPdf}
            disabled={reportLoading}
            className="flex items-center gap-1.5 disabled:opacity-50"
            style={{
              height: 36, padding: '0 16px', borderRadius: 6,
              backgroundColor: '#0F3D2E',
              color: '#ffffff', fontSize: 13, fontWeight: 500,
              border: '1px solid #0F3D2E',
            }}
            data-testid="header-download-pdf"
          >
            {reportLoading && <Loader2 className="w-3 h-3 animate-spin" />}
            {reportLoading ? 'Loading…' : 'Download Report'}
          </button>
          <button
            onClick={() => { window.location.href = `/api/research/${sessionId}/report/markdown`; }}
            className="flex items-center gap-1.5"
            style={{
              height: 36, padding: '0 16px', borderRadius: 6,
              backgroundColor: '#0F3D2E',
              color: '#ffffff', fontSize: 13, fontWeight: 500,
              border: '1px solid #0F3D2E',
            }}
            data-testid="header-download-md"
          >
            Download MD
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Panel 2 — Valuation (base scenario hero, bull/bear secondary) ─────────
const CONF_STYLE = {
  high:   { bg: '#D1FAE5', fg: '#065F46', label: 'H' },
  medium: { bg: '#FEF3C7', fg: '#92400E', label: 'M' },
  low:    { bg: '#FEE2E2', fg: '#991B1B', label: 'L' },
};

const ConfChip = ({ level }) => {
  const s = CONF_STYLE[level?.toLowerCase()] || null;
  if (!s) return null;
  return (
    <span style={{
      display: 'inline-block', padding: '0px 5px', borderRadius: 999,
      fontSize: 9, fontWeight: 700, lineHeight: '16px',
      backgroundColor: s.bg, color: s.fg, marginLeft: 3, verticalAlign: 'middle',
    }}>{s.label}</span>
  );
};

const ValuationPanel = ({ scenarios, assumptionConfidence, sym = '₹' }) => {
  const [driversOpen, setDriversOpen] = useState(false);
  const byKey = Object.fromEntries(scenarios.map((s) => [s.key, s]));
  const base = byKey.base;
  const bull = byKey.bull;
  const bear = byKey.bear;
  const baseRating = base ? normalizeRating(base.rating) : null;
  const rs = baseRating ? ratingStyle(baseRating) : null;
  const upsideColor = base?.upside_pct == null
    ? 'var(--bi-text-tertiary, #8593AB)'
    : base.upside_pct >= 0 ? 'var(--bi-success-fg, #0F7A3E)' : 'var(--bi-danger-fg, #C7372F)';

  return (
    <Panel title="Valuation" testId="panel-valuation">
      {!base ? (
        <div style={emptyStyle}>Not yet computed</div>
      ) : (
        <>
          <div style={{ fontSize: 22, fontWeight: 600, color: 'var(--bi-text-primary, #0F2540)',
                        fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}>
            {fmtCurrency(base.price_per_share, sym)}
          </div>
          <div style={{ fontSize: 13, color: upsideColor, marginTop: 2, fontVariantNumeric: 'tabular-nums' }}>
            {fmtPct(base.upside_pct)} <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}>vs current</span>
          </div>
          {baseRating && (
            <div style={{ marginTop: 8 }}>
              <span style={{
                display: 'inline-block', padding: '2px 8px', borderRadius: 999,
                fontSize: 11, fontWeight: 600,
                backgroundColor: rs.bg, color: rs.fg,
              }}>
                {baseRating}
              </span>
            </div>
          )}
          {base.key_assumption && (
            <div style={{ fontSize: 12, color: 'var(--bi-text-secondary, #4B5A75)', marginTop: 8, lineHeight: 1.6 }}>
              {assumptionConfidence && Object.keys(assumptionConfidence).length > 0 ? (
                <span>
                  {base.revenue_growth != null && (
                    <span>{fmtPctPlain(base.revenue_growth)} growth<ConfChip level={assumptionConfidence.revenue_growth} /></span>
                  )}
                  {base.ebitda_margin != null && (
                    <span> · {fmtPctPlain(base.ebitda_margin)} margin<ConfChip level={assumptionConfidence.ebitda_margin} /></span>
                  )}
                  {base.wacc != null && (
                    <span> · {fmtPctPlain(base.wacc)} WACC<ConfChip level={assumptionConfidence.wacc} /></span>
                  )}
                </span>
              ) : (
                <span title={base.key_assumption} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
                  {base.key_assumption}
                </span>
              )}
            </div>
          )}
          <div style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)', marginTop: 10, lineHeight: 1.5, fontStyle: 'italic' }}>
            Single-stage Gordon Growth DCF. May underestimate fair value for premium-quality names with structural moats (e.g., AAPL, MSFT). Multi-stage model in next release.
          </div>
        </>
      )}
      <div style={dividerStyle} />
      <button onClick={() => setDriversOpen(o => !o)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                       width: '100%', textAlign: 'left' }}>
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)',
                      display: 'flex', gap: 10, fontVariantNumeric: 'tabular-nums',
                      alignItems: 'center' }}>
          <span style={{ color: '#0F7A3E', fontWeight: 500 }}>▲ Bull: {bull?.price_per_share != null ? fmtCurrency(bull.price_per_share, sym) : '—'}</span>
          <span>·</span>
          <span style={{ color: '#C7372F', fontWeight: 500 }}>▼ Bear: {bear?.price_per_share != null ? fmtCurrency(bear.price_per_share, sym) : '—'}</span>
          <span style={{ marginLeft: 'auto', fontSize: 10 }}>{driversOpen ? '▲' : '▼'}</span>
        </div>
      </button>
      {driversOpen && base && (bull || bear) && (
        <div style={{ marginTop: 8, fontSize: 11, lineHeight: 1.7 }}>
          {[{ sc: bull, label: 'Bull', color: '#0F7A3E' }, { sc: bear, label: 'Bear', color: '#C7372F' }]
            .filter(({ sc }) => sc)
            .map(({ sc, label, color }) => (
              <div key={label} style={{ marginBottom: 6 }}>
                <div style={{ fontWeight: 600, color }}>{label} case assumptions:</div>
                {sc.revenue_growth != null && base.revenue_growth != null && (
                  <div style={{ color: 'var(--bi-text-secondary, #4B5A75)' }}>
                    Growth: <strong>{fmtPctPlain(sc.revenue_growth)}</strong>
                    <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> vs base {fmtPctPlain(base.revenue_growth)}</span>
                  </div>
                )}
                {sc.ebitda_margin != null && base.ebitda_margin != null && (
                  <div style={{ color: 'var(--bi-text-secondary, #4B5A75)' }}>
                    Margin: <strong>{fmtPctPlain(sc.ebitda_margin)}</strong>
                    <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> vs base {fmtPctPlain(base.ebitda_margin)}</span>
                  </div>
                )}
                {sc.wacc != null && base.wacc != null && (
                  <div style={{ color: 'var(--bi-text-secondary, #4B5A75)' }}>
                    WACC: <strong>{fmtPctPlain(sc.wacc)}</strong>
                    <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> vs base {fmtPctPlain(base.wacc)}</span>
                  </div>
                )}
                {sc.terminal_growth != null && base.terminal_growth != null && (
                  <div style={{ color: 'var(--bi-text-secondary, #4B5A75)' }}>
                    TG: <strong>{fmtPctPlain(sc.terminal_growth)}</strong>
                    <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> vs base {fmtPctPlain(base.terminal_growth)}</span>
                  </div>
                )}
              </div>
            ))}
        </div>
      )}
    </Panel>
  );
};

// ─── Panel 3 — Market-implied (reverse DCF) ────────────────────────────────
const ReverseDcfPanel = ({ researchData, sym = '₹' }) => {
  const rd = researchData?.reverse_dcf
    || researchData?.scenarios?.reverse_dcf
    || null;
  const rows = [
    { label: 'Implied growth', value: rd?.implied_growth_rate != null ? fmtPctPlain(rd.implied_growth_rate) : null },
    { label: 'Implied WACC',   value: rd?.implied_wacc != null ? fmtPctPlain(rd.implied_wacc) : null },
    { label: 'Market cap',     value: rd?.market_cap != null ? fmtLargeCurrency(rd.market_cap, sym) : null },
  ];
  const hasAny = rows.some((r) => r.value != null) || rd?.interpretation;

  return (
    <Panel title="Market-implied" testId="panel-reverse-dcf">
      {!hasAny ? (
        <div style={emptyStyle}>Not yet computed</div>
      ) : (
        <>
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between"
                 style={{ padding: '3px 0' }}>
              <span style={{ fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)' }}>
                {r.label}
              </span>
              <span style={{ fontSize: 13, fontWeight: 500,
                             color: 'var(--bi-text-primary, #0F2540)',
                             fontVariantNumeric: 'tabular-nums' }}>
                {r.value ?? '—'}
              </span>
            </div>
          ))}
          {rd?.interpretation && (
            <>
              <div style={dividerStyle} />
              <div style={{
                fontSize: 12, fontStyle: 'italic',
                color: 'var(--bi-text-secondary, #4B5A75)', lineHeight: 1.45,
                display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}>
                {rd.interpretation}
              </div>
            </>
          )}
        </>
      )}
    </Panel>
  );
};

// ─── Panel 4 — Composite score ─────────────────────────────────────────────
const SCORE_DIMS = [
  { key: 'financial_strength',       label: 'Financial Strength',    weight: 25 },
  { key: 'growth_quality',           label: 'Growth Quality',         weight: 25 },
  { key: 'valuation_attractiveness', label: 'Valuation',              weight: 25 },
  { key: 'risk_score',               label: 'Risk',                   weight: 15 },
  { key: 'market_positioning',       label: 'Market Position',        weight: 10 },
  { key: 'business_quality',         label: 'Business Quality',       weight:  0, isGrade: true },
];

const pickDimensionScores = (scoring) => {
  if (!scoring) return [];
  const src = scoring.dimensions || scoring.scores || scoring.pillars || scoring;
  const gradeMap = { A: 90, B: 70, C: 50, D: 30 };
  const out = [];
  for (const dim of SCORE_DIMS) {
    const v = src?.[dim.key] ?? scoring?.[dim.key];
    if (dim.isGrade && typeof v === 'string' && gradeMap[v.toUpperCase()] != null) {
      out.push({ ...dim, score: gradeMap[v.toUpperCase()], grade: v.toUpperCase() });
      continue;
    }
    const num = typeof v === 'number' ? v
      : typeof v === 'object' && v != null ? (v.score ?? v.value ?? v.pct) : null;
    if (typeof num === 'number' && !Number.isNaN(num)) {
      out.push({ ...dim, score: Math.max(0, Math.min(100, num)) });
    }
  }
  return out;
};

const dimBarColor = (score) => {
  if (score >= 80) return '#0F7A3E';
  if (score >= 60) return '#B45309';
  return '#C7372F';
};

const ScorePanel = ({ researchData }) => {
  const scoring = researchData?.scoring || null;
  const composite = scoring?.composite_score ?? scoring?.composite ?? scoring?.score ?? null;
  const recommendation = normalizeRating(scoring?.recommendation ?? scoring?.rating);
  const dims = pickDimensionScores(scoring);

  if (!scoring || (composite == null && dims.length === 0)) {
    return (
      <Panel title="Score" testId="panel-score">
        <div style={emptyStyle}>Composite scoring in the next release</div>
      </Panel>
    );
  }

  const rs = recommendation ? ratingStyle(recommendation) : null;

  return (
    <Panel title="Score" testId="panel-score">
      <div className="flex items-center gap-3" style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
          <span style={{ fontSize: 24, fontWeight: 600, color: 'var(--bi-text-primary, #0F2540)',
                         fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
            {composite != null ? Math.round(Number(composite)) : '—'}
          </span>
          <span style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)' }}>/100</span>
        </div>
        {recommendation && (
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 999,
            fontSize: 11, fontWeight: 600,
            backgroundColor: rs.bg, color: rs.fg,
          }}>
            {recommendation}
          </span>
        )}
      </div>

      {dims.length === 0 ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>
          Dimension breakdown unavailable
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
          {dims.map((d) => (
            <div key={d.key} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)',
                             width: 96, flexShrink: 0 }}>
                {d.label}
              </span>
              {d.weight > 0 && (
                <span style={{ fontSize: 10, fontWeight: 600, padding: '1px 5px', borderRadius: 999,
                               backgroundColor: 'var(--bi-bg-subtle, #EEF1F6)',
                               color: 'var(--bi-text-tertiary, #8593AB)', flexShrink: 0 }}>
                  {d.weight}%
                </span>
              )}
              <div style={{ flex: 1, height: 5, borderRadius: 3,
                            backgroundColor: 'var(--bi-bg-subtle, #EEF1F6)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${d.score}%`,
                              backgroundColor: dimBarColor(d.score),
                              borderRadius: 3, transition: 'width 0.4s ease' }} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 600, color: dimBarColor(d.score),
                             width: 42, textAlign: 'right', flexShrink: 0,
                             fontVariantNumeric: 'tabular-nums' }}>
                {d.grade ? `Grade ${d.grade}` : `${Math.round(d.score)}/100`}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
};

// ─── Panel 5 — Sensitivity heatmap ─────────────────────────────────────────
const SensitivityPanel = ({ researchData, currentPrice }) => {
  const sens = researchData?.sensitivity || researchData?.scenarios?.sensitivity || null;
  const wacc = sens?.wacc_grid || sens?.wacc_range;
  const growth = sens?.growth_grid || sens?.terminal_growth_range;
  const matrix = sens?.matrix || sens?.grid;
  const metric = sens?.metric || 'equity_value';
  const isPctMetric = metric === 'upside_pct';
  const valid = Array.isArray(wacc) && Array.isArray(growth) && Array.isArray(matrix)
    && matrix.length === growth.length
    && matrix.every((r) => Array.isArray(r) && r.length === wacc.length);

  if (!valid) {
    return (
      <Panel title="Sensitivity · Fair value" testId="panel-sensitivity">
        <div style={emptyStyle}>Sensitivity analysis in the next release</div>
      </Panel>
    );
  }

  // Flat min/max for color ramp.
  const flat = matrix.flat().filter((v) => typeof v === 'number' && !Number.isNaN(v));
  const minV = Math.min(...flat);
  const maxV = Math.max(...flat);
  const cp = typeof currentPrice === 'number' ? currentPrice : null;

  const cellBg = (v) => {
    if (typeof v !== 'number' || Number.isNaN(v)) return 'transparent';
    if (isPctMetric) {
      // grid values are already upside % vs current price
      const t = Math.min(1, Math.abs(v) / 35); // saturate at ±35%
      if (v >= 0) return `rgba(15,122,62,${0.05 + t * 0.22})`;
      return `rgba(199,55,47,${0.05 + t * 0.22})`;
    }
    if (cp != null) {
      const diff = v - cp;
      const pct = cp > 0 ? diff / cp : 0;
      const t = Math.min(1, Math.abs(pct) / 0.35);
      if (diff >= 0) return `rgba(15,122,62,${0.05 + t * 0.22})`;
      return `rgba(199,55,47,${0.05 + t * 0.22})`;
    }
    const t = (v - minV) / Math.max(1e-9, maxV - minV);
    return `rgba(27,58,107,${0.05 + t * 0.25})`;
  };

  const fmtCell = (v) => {
    if (typeof v !== 'number' || Number.isNaN(v)) return '—';
    if (isPctMetric) {
      return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
    }
    return Math.round(v).toLocaleString('en-IN');
  };

  // base cell = center (or middle if even length)
  const ri = Math.floor(growth.length / 2);
  const ci = Math.floor(wacc.length / 2);

  const fmtHeaderPct = (v) => {
    const n = Number(v);
    if (Number.isNaN(n)) return String(v);
    const scaled = Math.abs(n) < 1 ? n * 100 : n;
    return `${scaled.toFixed(1)}%`;
  };

  return (
    <Panel title="Sensitivity · Fair value" testId="panel-sensitivity">
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'separate', borderSpacing: 2, fontSize: 11,
                         fontVariantNumeric: 'tabular-nums' }}>
          <thead>
            <tr>
              <th style={{ width: 48, padding: 4, fontSize: 10,
                           color: 'var(--bi-text-tertiary, #8593AB)', fontWeight: 500, textAlign: 'left' }}>
                g ＼ WACC
              </th>
              {wacc.map((w, j) => (
                <th key={j} style={{ padding: 4, fontSize: 10, fontWeight: 500,
                                     color: 'var(--bi-text-secondary, #4B5A75)',
                                     width: 50, textAlign: 'center' }}>
                  {fmtHeaderPct(w)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {growth.map((g, i) => (
              <tr key={i}>
                <td style={{ padding: 4, fontSize: 10, color: 'var(--bi-text-secondary, #4B5A75)',
                             fontWeight: 500, textAlign: 'right' }}>
                  {fmtHeaderPct(g)}
                </td>
                {wacc.map((_, j) => {
                  const v = matrix[i][j];
                  const isBase = i === ri && j === ci;
                  return (
                    <td key={j} style={{
                      width: 50, height: 32, textAlign: 'center',
                      backgroundColor: cellBg(v),
                      border: isBase
                        ? '2px solid var(--bi-navy-700, #1B3A6B)'
                        : '1px solid var(--bi-border-subtle, #E2E7EF)',
                      borderRadius: 3,
                      color: 'var(--bi-text-primary, #0F2540)',
                      fontSize: 10.5,
                    }}>
                      {fmtCell(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
};

// ─── Panel 6 — Forecast table ──────────────────────────────────────────────
const ForecastPanel = ({ researchData, dcfData, sym = '₹' }) => {
  const forecast = dcfData?.forecast
    || researchData?.dcf_summary?.forecast
    || researchData?.dcf_output?.forecast
    || researchData?.forecast
    || null;

  if (!Array.isArray(forecast) || forecast.length === 0) {
    return (
      <Panel title="Forecast · 5 years" testId="panel-forecast">
        <div style={emptyStyle}>5-year forecast in the next release</div>
      </Panel>
    );
  }

  const rows = forecast.slice(0, 5);
  const cell = { padding: '6px 8px', fontSize: 11, fontVariantNumeric: 'tabular-nums' };
  const head = { ...cell, fontSize: 10, fontWeight: 500,
                 color: 'var(--bi-text-tertiary, #8593AB)',
                 textTransform: 'uppercase', letterSpacing: '0.06em', textAlign: 'right' };

  return (
    <Panel title="Forecast · 5 years" testId="panel-forecast">
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ ...head, textAlign: 'left' }}>Year</th>
            <th style={head}>Revenue</th>
            <th style={head}>FCFF</th>
            <th style={head}>Growth</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ backgroundColor: i % 2 ? 'var(--bi-bg-subtle, #EEF1F6)' : 'transparent' }}>
              <td style={{ ...cell, color: 'var(--bi-text-secondary, #4B5A75)' }}>
                {r.year ?? (i + 1)}
              </td>
              <td style={{ ...cell, textAlign: 'right', color: 'var(--bi-text-primary, #0F2540)' }}>
                {r.revenue != null ? Number(r.revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '—'}
              </td>
              <td style={{ ...cell, textAlign: 'right', color: 'var(--bi-text-primary, #0F2540)' }}>
                {r.fcff != null ? Number(r.fcff).toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '—'}
              </td>
              <td style={{ ...cell, textAlign: 'right', color: 'var(--bi-text-secondary, #4B5A75)' }}>
                {r.revenue_growth != null ? fmtPctPlain(r.revenue_growth) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ fontSize: 10, color: 'var(--bi-text-tertiary, #8593AB)', marginTop: 6 }}>
        All figures {sym} {(dcfData?.meta?.units || researchData?.dcf_summary?.meta?.units || '').toLowerCase() === 'millions' ? 'mn' : 'cr'}
      </div>
    </Panel>
  );
};

// ─── Panel 7 — Assumption history ──────────────────────────────────────────
const HistoryPanel = ({ researchData }) => {
  const history = researchData?.assumption_history || [];
  const items = [...history].reverse().slice(0, 5);
  const count = history.length;

  return (
    <Panel title={`Changes · ${count}`} testId="panel-history">
      {items.length === 0 ? (
        <div style={emptyStyle}>No changes this session</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map((h, i) => (
            <div key={i} className="flex items-start justify-between gap-2">
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--bi-text-primary, #0F2540)' }}>
                  {h.metric}
                  <span style={{ fontWeight: 400, color: 'var(--bi-text-secondary, #4B5A75)', fontSize: 11 }}>
                    {' '}— {h.old_value == null ? '—' : String(h.old_value)} → {h.new_value == null ? '—' : String(h.new_value)}
                  </span>
                </div>
                {h.reason && (
                  <div style={{
                    fontSize: 11, fontStyle: 'italic', color: 'var(--bi-text-tertiary, #8593AB)',
                    marginTop: 2,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }} title={h.reason}>
                    {h.reason}
                  </div>
                )}
              </div>
              <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', flexShrink: 0 }}>
                {h.timestamp ? new Date(h.timestamp).toLocaleDateString('en-IN',
                  { month: 'short', day: 'numeric' }) : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
};

// ─── Panel 8 — Guardrail breaches ──────────────────────────────────────────
const RiskFlagsPanel = ({ researchData }) => {
  const breaches = researchData?.guardrail_breaches || [];
  const shown = breaches.slice(0, 4);
  const remaining = breaches.length - shown.length;

  return (
    <Panel title="Risk flags" testId="panel-risk-flags">
      {breaches.length === 0 ? (
        <div style={{ ...emptyStyle, display: 'flex', alignItems: 'center',
                       justifyContent: 'center', gap: 6 }}>
          <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--bi-success-fg, #0F7A3E)' }} />
          <span>All checks passed</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {shown.map((b, i) => {
            const sev = String(b.severity || 'warn').toLowerCase();
            const severe = sev === 'error' || sev === 'severe' || sev === 'critical';
            const sevBg = severe ? 'rgba(199,55,47,0.10)' : 'rgba(217,119,6,0.12)';
            const sevFg = severe ? '#C7372F' : '#B45309';
            const range = (b.lower_bound != null || b.upper_bound != null)
              ? `typical ${b.lower_bound ?? '—'} to ${b.upper_bound ?? '—'}`
              : null;
            return (
              <div key={i} className="flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5" style={{
                  color: severe ? 'var(--bi-danger-fg, #C7372F)' : '#B45309',
                  marginTop: 2, flexShrink: 0,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="flex items-baseline justify-between gap-2">
                    <span style={{ fontSize: 12, fontWeight: 500,
                                   color: 'var(--bi-text-primary, #0F2540)' }}>
                      {b.metric}
                      <span style={{ fontWeight: 400,
                                     color: 'var(--bi-text-secondary, #4B5A75)' }}>
                        {': '}{b.value == null ? '—' : String(b.value)}
                      </span>
                    </span>
                    <span style={{
                      fontSize: 10, fontWeight: 600,
                      padding: '1px 6px', borderRadius: 999,
                      backgroundColor: sevBg, color: sevFg,
                      textTransform: 'uppercase', letterSpacing: '0.04em',
                      flexShrink: 0,
                    }}>
                      {sev}
                    </span>
                  </div>
                  {range && (
                    <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)',
                                  marginTop: 1 }}>
                      {range}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {remaining > 0 && (
            <div style={{ fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)' }}>
              Show all {breaches.length}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Main page
// ═══════════════════════════════════════════════════════════════════════════
// ─── Audit Trail panel ─────────────────────────────────────────────────────
const AuditPanel = ({ sessionId }) => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !isValidSessionId(sessionId) || data) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/audit`)
      .then(setData)
      .catch(() => setData({ sources: [], audit_log: [] }))
      .finally(() => setLoading(false));
  }, [open, sessionId, data]);

  return (
    <Panel title={
      <button onClick={() => setOpen(o => !o)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', cursor: 'pointer', color: 'inherit' }}>
        Audit Trail · Data Provenance
        <span style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)' }}>{open ? '▲' : '▼'}</span>
      </button>
    } testId="panel-audit">
      {!open ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Click to expand</div>
      ) : loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : !data ? (
        <div style={emptyStyle}>Audit data not available for this session</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--bi-text-secondary, #4B5A75)', marginBottom: 6 }}>Sources used</div>
            {(data.sources || []).length === 0
              ? <div style={emptyStyle}>No source data</div>
              : (data.sources || []).map((s, i) => (
                <div key={i} style={{ fontSize: 11, fontFamily: 'monospace', padding: '3px 0',
                                       borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)',
                                       color: 'var(--bi-text-primary, #0F2540)' }}>
                  <span style={{ fontWeight: 600 }}>{s.api_name}</span>
                  {s.endpoint && <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> · {s.endpoint}</span>}
                  {s.fetched_at && <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> · {new Date(s.fetched_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</span>}
                  {s.status && <span style={{ marginLeft: 6, color: s.status === 'ok' ? '#0F7A3E' : '#C7372F' }}>● {s.status}</span>}
                </div>
              ))}
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--bi-text-secondary, #4B5A75)', marginBottom: 6 }}>Change log</div>
            {(data.audit_log || []).length === 0
              ? <div style={emptyStyle}>No changes recorded</div>
              : (data.audit_log || []).map((e, i) => (
                <div key={i} style={{ fontSize: 11, fontFamily: 'monospace', padding: '3px 0',
                                       borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)',
                                       color: 'var(--bi-text-primary, #0F2540)' }}>
                  {e.timestamp && <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}>{new Date(e.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} · </span>}
                  <span style={{ fontWeight: 600 }}>{e.event}</span>
                  {e.fields_changed?.length > 0 && <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> [{e.fields_changed.join(', ')}]</span>}
                </div>
              ))}
          </div>
        </div>
      )}
    </Panel>
  );
};

// ─── Sources Tracker panel ─────────────────────────────────────────────────
const SOURCE_TYPE = (name = '') => {
  const n = name.toLowerCase();
  if (n.includes('calc') || n.includes('dcf') || n.includes('model')) return 'Calc';
  if (n.includes('scrape') || n.includes('selenium') || n.includes('nse') || n.includes('bse')) return 'Scrape';
  return 'API';
};
const TYPE_STYLE = {
  API:    { bg: 'rgba(14,100,234,0.08)', fg: '#0E64EA' },
  Scrape: { bg: 'rgba(245,158,11,0.10)', fg: '#B45309' },
  Calc:   { bg: 'rgba(75,90,117,0.10)',  fg: '#4B5A75' },
};

const SourcesPanel = ({ sessionId }) => {
  const [open, setOpen] = useState(false);
  const [sources, setSources] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !isValidSessionId(sessionId) || sources) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/audit`)
      .then(d => setSources(d.sources || []))
      .catch(() => setSources([]))
      .finally(() => setLoading(false));
  }, [open, sessionId, sources]);

  return (
    <Panel title={
      <button onClick={() => setOpen(o => !o)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', cursor: 'pointer', color: 'inherit' }}>
        Data Sources
        <span style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)' }}>{open ? '▲' : '▼'}</span>
      </button>
    } testId="panel-sources">
      {!open ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Click to expand</div>
      ) : loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : !sources || sources.length === 0 ? (
        <div style={emptyStyle}>No source data recorded for this session</div>
      ) : (
        <div>
          {sources.map((s, i) => {
            const typ = SOURCE_TYPE(s.api_name);
            const ts = TYPE_STYLE[typ];
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0',
                                     borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)', flexWrap: 'wrap' }}>
                <span style={{ display: 'inline-block', padding: '1px 7px', borderRadius: 999,
                               fontSize: 10, fontWeight: 600, backgroundColor: ts.bg, color: ts.fg, minWidth: 40, textAlign: 'center' }}>
                  {typ}
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--bi-text-primary, #0F2540)' }}>
                  {s.api_name}
                </span>
                {s.endpoint && s.endpoint !== s.api_name && (
                  <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', fontFamily: 'monospace' }}>
                    {s.endpoint}
                  </span>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>
                  {s.fetched_at ? new Date(s.fetched_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) : ''}
                </span>
                <span style={{ fontSize: 11, fontWeight: 600,
                               color: s.status === 'ok' || s.status === 'success' ? '#0F7A3E' : '#C7372F' }}>
                  ● {s.status || 'ok'}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
};

// ─── Guardrail Log panel ────────────────────────────────────────────────────
const GUARDRAIL_CHIP = {
  pass:  { bg: '#D1FAE5', fg: '#065F46', label: 'PASS' },
  warn:  { bg: '#FEF3C7', fg: '#92400E', label: 'WARN' },
  fail:  { bg: '#FEE2E2', fg: '#991B1B', label: 'FAIL' },
  breach:{ bg: '#FEE2E2', fg: '#991B1B', label: 'BREACH' },
};
const guardrailChipStyle = (status) => {
  const s = GUARDRAIL_CHIP[status?.toLowerCase()] || GUARDRAIL_CHIP.warn;
  return { display: 'inline-block', padding: '1px 7px', borderRadius: 999,
           fontSize: 10, fontWeight: 700, backgroundColor: s.bg, color: s.fg };
};

const GuardrailPanel = ({ sessionId }) => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !isValidSessionId(sessionId) || data) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/guardrails`)
      .then(setData)
      .catch(() => setData({ guardrails: [], all_passed: true }))
      .finally(() => setLoading(false));
  }, [open, sessionId, data]);

  return (
    <Panel title={
      <button onClick={() => setOpen(o => !o)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', cursor: 'pointer', color: 'inherit' }}>
        Guardrail Log
        <span style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)' }}>{open ? '▲' : '▼'}</span>
      </button>
    } testId="panel-guardrail">
      {!open ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Click to expand</div>
      ) : loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : !data?.engine_ran ? (
        <div style={emptyStyle}>No signals reached the guardrail engine this session</div>
      ) : data?.all_passed ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
          <span style={guardrailChipStyle('pass')}>PASS</span>
          <span style={{ color: 'var(--bi-text-secondary, #4B5A75)' }}>All assumption guardrails passed — no breaches recorded.</span>
        </div>
      ) : (
        <div>
          {(data?.guardrails || []).map((g, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '5px 0',
                                   borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)' }}>
              <span style={guardrailChipStyle(g.status || 'breach')}>{(GUARDRAIL_CHIP[g.status?.toLowerCase()] || GUARDRAIL_CHIP.breach).label}</span>
              <div style={{ fontSize: 11, color: 'var(--bi-text-primary, #0F2540)' }}>
                <span style={{ fontWeight: 600 }}>{g.metric || g.field || '—'}</span>
                {g.reason && <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> · {g.reason}</span>}
                {g.proposed != null && g.capped != null && (
                  <span style={{ color: 'var(--bi-text-tertiary, #8593AB)' }}> (capped {g.proposed} → {g.capped})</span>
                )}
              </div>
              {g.timestamp && (
                <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--bi-text-tertiary, #8593AB)', whiteSpace: 'nowrap' }}>
                  {new Date(g.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
};

// ─── Assumption History timeline ────────────────────────────────────────────
const KEY_LABELS = {
  revenue_growth: 'Revenue growth', ebitda_margin: 'EBITDA margin', wacc: 'WACC',
  terminal_growth_rate: 'Terminal growth', capex_pct_revenue: 'CapEx %',
  current_price_inr: 'Current price', beta: 'Beta', tax_rate: 'Tax rate',
};

const AssumptionHistoryPanel = ({ sessionId }) => {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !isValidSessionId(sessionId) || history) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/assumption_history`)
      .then(d => setHistory({ items: d.history || [], engine_ran: d.engine_ran === true }))
      .catch(() => setHistory({ items: [], engine_ran: false }))
      .finally(() => setLoading(false));
  }, [open, sessionId, history]);

  return (
    <Panel title={
      <button onClick={() => setOpen(o => !o)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', cursor: 'pointer', color: 'inherit' }}>
        Assumption History
        <span style={{ fontSize: 12, color: 'var(--bi-text-tertiary, #8593AB)' }}>{open ? '▲' : '▼'}</span>
      </button>
    } testId="panel-assumption-history">
      {!open ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Click to expand</div>
      ) : loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : !history?.engine_ran ? (
        <div style={emptyStyle}>No signal-driven assumption changes this session</div>
      ) : !history?.items || history.items.length === 0 ? (
        <div style={emptyStyle}>Guardrails ran — all changes within bounds, none applied</div>
      ) : (
        <div style={{ position: 'relative', paddingLeft: 18 }}>
          <div style={{ position: 'absolute', left: 6, top: 6, bottom: 6,
                        width: 2, backgroundColor: 'var(--bi-border-subtle, #E3E8EF)', borderRadius: 1 }} />
          {(history?.items || []).map((entry, i) => {
            const ts = entry.timestamp || entry.assumptions?._initialized_at || '';
            const evt = entry.event || 'update';
            const delta = entry.delta || {};
            const keys = Object.keys(delta).filter(k => !k.startsWith('_'));
            return (
              <div key={i} style={{ position: 'relative', marginBottom: 12 }}>
                <div style={{ position: 'absolute', left: -15, top: 4, width: 8, height: 8,
                              borderRadius: '50%', backgroundColor: evt === 'initialized' ? '#0E64EA' : '#0F7A3E',
                              border: '2px solid white' }} />
                <div style={{ fontSize: 10, color: 'var(--bi-text-tertiary, #8593AB)', marginBottom: 2 }}>
                  {ts ? new Date(ts).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) : '—'}
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--bi-text-primary, #0F2540)',
                              textTransform: 'capitalize' }}>
                  {evt.replace(/_/g, ' ')}
                </div>
                {keys.length > 0 && (
                  <div style={{ marginTop: 3 }}>
                    {keys.map(k => {
                      const d = delta[k];
                      return (
                        <div key={k} style={{ fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)' }}>
                          {KEY_LABELS[k] || k}: <span style={{ color: '#C7372F' }}>{d?.old ?? '—'}</span>
                          {' → '}<span style={{ color: '#0F7A3E', fontWeight: 500 }}>{d?.new ?? d}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
};

// ─── F&O Analytics — Coming Soon ───────────────────────────────────────────
const FnoPulseStrip = () => (
  <Panel title={
    <span style={{ color: 'var(--bi-text-tertiary, #8593AB)', display: 'flex', alignItems: 'center', gap: 8 }}>
      F&O Analytics
      <span style={{ fontSize: 10, fontWeight: 600, padding: '1px 7px', borderRadius: 999,
                     backgroundColor: 'var(--bi-border-subtle, #E3E8EF)', color: 'var(--bi-text-tertiary, #8593AB)' }}>
        Q3 2026
      </span>
    </span>
  } testId="panel-fno-pulse">
    <div style={{ color: 'var(--bi-text-tertiary, #8593AB)', fontSize: 12 }}>
      <div style={{ fontWeight: 500, marginBottom: 4 }}>Live derivatives data from licensed feed integration in progress.</div>
      <div style={{ fontSize: 11 }}>Will include: PCR · OI · Max Pain · IV Skew · Strike-wise OI</div>
    </div>
  </Panel>
);

// ─── Financial Charts panel (Feature 14) ───────────────────────────────────
const FinancialChartsPanel = ({ sessionId }) => {
  const [charts, setCharts] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isValidSessionId(sessionId)) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/charts`)
      .then(r => setCharts(r.charts || []))
      .catch(() => setCharts([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <Panel title="Financial Charts" testId="panel-financial-charts">
      {loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading charts…</div>
      ) : !charts || charts.length === 0 ? (
        <div style={emptyStyle}>Charts will be available after analysis completes</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {charts.map((c, i) => (
            <div key={i} style={{
              background: 'var(--bi-surface-raised, #F7F9FC)',
              borderRadius: 8,
              border: '1px solid var(--bi-border-subtle, #E3E8EF)',
              overflow: 'hidden',
            }}>
              <img
                src={`data:image/png;base64,${c.image_base64}`}
                alt={c.name}
                style={{ width: '100%', display: 'block' }}
              />
              <div style={{ padding: '4px 8px 6px', fontSize: 11, fontWeight: 600,
                            color: 'var(--bi-text-secondary, #4B5A75)', textAlign: 'center' }}>
                {c.name}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
};

// ─── Peer Comparison panel (Feature 15) ────────────────────────────────────
const PeerComparisonPanel = ({ sessionId }) => {
  const [peers, setPeers] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isValidSessionId(sessionId)) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/peers`)
      .then(r => setPeers(Array.isArray(r) ? r : []))
      .catch(() => setPeers([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const fmtNum = (v, suffix = '') => v != null ? `${v}${suffix}` : '—';

  const calcAvg = (key) => {
    if (!peers || peers.length < 2) return null;
    const vals = peers.slice(1).map(p => p[key]).filter(v => v != null);
    if (!vals.length) return null;
    return +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);
  };

  const calcPremDisc = (key) => {
    if (!peers || peers.length < 2) return null;
    const sub = peers[0]?.[key];
    const avg = calcAvg(key);
    if (sub == null || avg == null || avg === 0) return null;
    return +(((sub - avg) / avg) * 100).toFixed(1);
  };

  return (
    <Panel title="Peer Comparison" testId="panel-peer-comparison">
      {loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : !peers || peers.length === 0 ? (
        <div style={emptyStyle}>Peer data updating</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--bi-border-subtle, #E3E8EF)' }}>
              {['Company', 'P/E', 'EV/EBITDA', 'ROE (%)'].map((h, i) => (
                <th key={h} style={{ textAlign: i === 0 ? 'left' : 'right', padding: '4px 8px',
                                     fontWeight: 600, fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {peers.map((p, i) => (
              <tr key={i} style={{
                borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)',
                background: i === 0 ? 'rgba(99,102,241,0.05)' : 'transparent',
              }}>
                <td style={{ padding: '5px 8px', fontWeight: i === 0 ? 700 : 400,
                             color: 'var(--bi-text-primary, #0F2540)' }}>
                  {p.name || p.ticker}
                  {i === 0 && <span style={{ marginLeft: 6, fontSize: 10, color: '#6366f1' }}>★</span>}
                </td>
                <td style={{ padding: '5px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                             color: 'var(--bi-text-primary, #0F2540)' }}>{fmtNum(p.pe_fy25e, 'x')}</td>
                <td style={{ padding: '5px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                             color: 'var(--bi-text-primary, #0F2540)' }}>{fmtNum(p.ev_ebitda, 'x')}</td>
                <td style={{ padding: '5px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                             color: 'var(--bi-text-primary, #0F2540)' }}>{fmtNum(p.roe, '%')}</td>
              </tr>
            ))}
            {peers.length > 1 && (
              <>
                <tr style={{ borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)',
                             background: 'rgba(75,90,117,0.04)' }}>
                  <td style={{ padding: '5px 8px', fontWeight: 600, fontSize: 11,
                               color: 'var(--bi-text-secondary, #4B5A75)' }}>Peer Average</td>
                  {['pe_fy25e','ev_ebitda','roe'].map(k => (
                    <td key={k} style={{ padding: '5px 8px', textAlign: 'right', fontSize: 11,
                                        color: 'var(--bi-text-secondary, #4B5A75)', fontVariantNumeric: 'tabular-nums' }}>
                      {fmtNum(calcAvg(k), k === 'roe' ? '%' : 'x')}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td style={{ padding: '5px 8px', fontWeight: 600, fontSize: 11,
                               color: 'var(--bi-text-secondary, #4B5A75)' }}>Premium/(Discount)</td>
                  {['pe_fy25e','ev_ebitda','roe'].map(k => {
                    const pd = calcPremDisc(k);
                    return (
                      <td key={k} style={{ padding: '5px 8px', textAlign: 'right', fontSize: 11,
                                          fontVariantNumeric: 'tabular-nums',
                                          color: pd == null ? 'var(--bi-text-tertiary)' : pd > 0 ? '#0F7A3E' : '#C7372F' }}>
                        {pd != null ? `${pd > 0 ? '+' : ''}${pd}%` : '—'}
                      </td>
                    );
                  })}
                </tr>
              </>
            )}
          </tbody>
        </table>
      )}
    </Panel>
  );
};

// ─── Factor Scores panel (Feature 16) ──────────────────────────────────────
const FactorScoresPanel = ({ sessionId, scoring }) => {
  const [factors, setFactors] = useState(null);
  const [loading, setLoading] = useState(false);

  // Derive 4-bucket factor scores from the scoring object passed via props
  const derivedFactors = useMemo(() => {
    if (!scoring) return null;
    const fs  = parseFloat(scoring.financial_strength      ?? 50) || 50;
    const gq  = parseFloat(scoring.growth_quality          ?? 50) || 50;
    const va  = parseFloat(scoring.valuation_attractiveness?? 50) || 50;
    const risk= parseFloat(scoring.risk_score              ?? 50) || 50;
    const mp  = parseFloat(scoring.market_positioning      ?? 50) || 50;
    return {
      momentum: Math.round(Math.min(100, Math.max(0, gq  * 0.6 + mp * 0.4))),
      value:    Math.round(Math.min(100, Math.max(0, va))),
      quality:  Math.round(Math.min(100, Math.max(0, fs  * 0.6 + mp * 0.4))),
      macro:    Math.round(Math.min(100, Math.max(0, 100 - risk))),
    };
  }, [scoring]);

  useEffect(() => {
    // Skip network fetch if we already have live scores from the analyze response
    if (derivedFactors) return;
    if (!isValidSessionId(sessionId)) return;
    setLoading(true);
    apiGet(`/api/research/${sessionId}/factors`)
      .then(r => setFactors(r.factors || null))
      .catch(() => setFactors(null))
      .finally(() => setLoading(false));
  }, [sessionId, derivedFactors]);

  const barColor = (v) => {
    if (v == null) return '#64748b';
    if (v >= 65) return '#10b981';
    if (v >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const FACTOR_LABELS = [
    { key: 'momentum', label: 'Momentum' },
    { key: 'value',    label: 'Value' },
    { key: 'quality',  label: 'Quality' },
    { key: 'macro',    label: 'Macro' },
  ];

  const displayFactors = derivedFactors || factors;

  return (
    <Panel title="Factor Scores" testId="panel-factor-scores">
      {loading && !displayFactors ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : !displayFactors ? (
        <div style={emptyStyle}>Factor analysis pending</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {FACTOR_LABELS.map(({ key, label }) => {
            const v = displayFactors[key];
            const color = barColor(v);
            return (
              <div key={key}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: 11 }}>
                  <span style={{ fontWeight: 600, color: 'var(--bi-text-secondary, #4B5A75)' }}>{label}</span>
                  <span style={{ fontWeight: 700, color }}>{v != null ? Math.round(v) : '—'}</span>
                </div>
                <div style={{ height: 8, background: 'var(--bi-surface-raised, #F0F3FA)', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${v || 0}%`, borderRadius: 4,
                    background: color, transition: 'width 0.4s ease',
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
};

// ─── Insider Trades panel ───────────────────────────────────────────────────
const InsiderTradesPanel = ({ ticker, sym = '₹' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [serviceUnavailable, setServiceUnavailable] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setServiceUnavailable(false);
    apiGet(`/api/insider-trades?ticker=${encodeURIComponent(ticker)}&limit=20`)
      .then(r => {
        if (r?.status === 'unavailable') {
          setServiceUnavailable(true);
          setData([]);
        } else {
          setData(r.trades || []);
        }
      })
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [ticker]);

  const actionStyle = (action) => ({
    display: 'inline-block', padding: '1px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
    backgroundColor: action === 'BUY' ? 'rgba(15,122,62,0.10)' : 'rgba(199,55,47,0.10)',
    color: action === 'BUY' ? '#0F7A3E' : '#C7372F',
  });

  const fmtVal = (v) => fmtLargeCurrency(v, sym);

  return (
    <Panel title="Insider Activity · Last 90 days" testId="panel-insider-trades">
      {loading ? (
        <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)' }}>Loading…</div>
      ) : serviceUnavailable ? (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 12px',
                      background: 'rgba(217,119,6,0.08)', border: '1px solid rgba(217,119,6,0.25)',
                      borderRadius: 6 }} data-testid="insider-trades-unavailable-banner">
          <AlertTriangle style={{ width: 14, height: 14, color: '#d97706', flexShrink: 0, marginTop: 1 }} />
          <div>
            <p style={{ fontSize: 11, fontWeight: 600, color: '#92400e', margin: 0 }}>Database offline — insider trades unavailable</p>
            <p style={{ fontSize: 11, color: '#b45309', margin: '2px 0 0' }}>Data will resume when the database reconnects.</p>
          </div>
        </div>
      ) : !data || data.length === 0 ? (
        <div style={emptyStyle}>No insider trades in last 90 days</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)' }}>
              {['Date', 'Person', 'Action', 'Qty', 'Value'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 600,
                                     fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--bi-border-subtle, #E3E8EF)' }}>
                <td style={{ padding: '5px 8px', color: 'var(--bi-text-tertiary, #8593AB)', whiteSpace: 'nowrap' }}>{row.date || '—'}</td>
                <td style={{ padding: '5px 8px', color: 'var(--bi-text-primary, #0F2540)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.person || '—'}</td>
                <td style={{ padding: '5px 8px' }}><span style={actionStyle(row.action)}>{row.action || '—'}</span></td>
                <td style={{ padding: '5px 8px', fontVariantNumeric: 'tabular-nums', color: 'var(--bi-text-primary, #0F2540)' }}>{row.quantity ? Number(row.quantity).toLocaleString('en-IN') : '—'}</td>
                <td style={{ padding: '5px 8px', fontVariantNumeric: 'tabular-nums', color: 'var(--bi-text-primary, #0F2540)' }}>{fmtVal(row.value_inr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
};

export const ResearchSession = ({ onSessionChange, pendingTicker }) => {
  const [ticker, setTicker] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [researchData, setResearchData] = useState(null);
  const [dcfData, setDcfData] = useState(null);
  const [swotData, setSwotData] = useState(null);
  const [swotLoading, setSwotLoading] = useState(false);
  const [porterData, setPorterData] = useState(null);
  const [porterLoading, setPorterLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [xlsmState, setXlsmState] = useState('idle');
  const [sessions, setSessions] = useState([]);
  const [recentTickers, setRecentTickers] = useState([
    { ticker: 'ITC', session_id: null },
    { ticker: 'ONGC', session_id: null },
    { ticker: 'COALINDIA', session_id: null },
    { ticker: 'JPM', session_id: null },
  ]); // [{ticker, session_id}] — only successful analyses
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [showLoader, setShowLoader] = useState(false);
  const loaderTimerRef = useRef(null);
  const [error, setError] = useState(null);
  const [tickerError, setTickerError] = useState('');
  const tickerErrorTimerRef = useRef(null);

  const flashTickerError = (msg) => {
    setTickerError(msg);
    if (tickerErrorTimerRef.current) clearTimeout(tickerErrorTimerRef.current);
    tickerErrorTimerRef.current = setTimeout(() => setTickerError(''), 4000);
  };

  // New-session modal (optional; Analyze works without it)
  const [showNewModal, setShowNewModal] = useState(false);
  const [modalTicker, setModalTicker] = useState('');
  const [modalHypothesis, setModalHypothesis] = useState('');
  const [modalVariant, setModalVariant] = useState('');
  const [modalSector, setModalSector] = useState('auto');

  useEffect(() => {
    if (analyzing) {
      loaderTimerRef.current = setTimeout(() => setShowLoader(true), 300);
    } else {
      if (loaderTimerRef.current) clearTimeout(loaderTimerRef.current);
      setShowLoader(false);
    }
    return () => { if (loaderTimerRef.current) clearTimeout(loaderTimerRef.current); };
  }, [analyzing]);

  useEffect(() => {
    if (onSessionChange) onSessionChange(sessionId);
  }, [sessionId, onSessionChange]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await apiGet(API_ENDPOINTS.sessions);
        setSessions(unwrapList(data, 'sessions'));
      } catch (err) { console.error('Failed to fetch sessions:', err); }
    };
    fetchSessions();
  }, []);

  useEffect(() => {
    if (!isValidSessionId(sessionId)) return;
    const fetchResearchData = async () => {
      try {
        setLoading(true);
        const data = await apiGet(API_ENDPOINTS.research(sessionId));
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
          setDcfData({
            status: 'complete',
            current_price: data.dcf.current_price,
            scenarios: {
              base: {
                per_share: data.dcf.fair_value,
                upside_pct: data.dcf.upside_pct,
                rating: data.dcf.upside_pct > 15 ? 'BUY'
                      : data.dcf.upside_pct < -15 ? 'SELL' : 'HOLD',
              },
            },
          });
        }
        setError(null);
      } catch (err) { setError(err.message); }
      finally { setLoading(false); }
    };
    fetchResearchData();
  }, [sessionId]);

  useEffect(() => {
    if (!isValidSessionId(sessionId)) return;
    const fetchSwot = async () => {
      setSwotLoading(true);
      try {
        const data = await apiGet(API_ENDPOINTS.researchSwot(sessionId));
        setSwotData(data);
      } catch (err) {
        setSwotData({ strengths: [], weaknesses: [], opportunities: [], threats: [], error: err.message });
      } finally { setSwotLoading(false); }
    };
    fetchSwot();
  }, [sessionId]);

  useEffect(() => {
    if (!isValidSessionId(sessionId)) return;
    const fetchPorter = async () => {
      setPorterLoading(true);
      try {
        const data = await apiGet(API_ENDPOINTS.researchPorter(sessionId));
        setPorterData(data);
      } catch (err) {
        setPorterData({ forces: [], error: err.message });
      } finally { setPorterLoading(false); }
    };
    fetchPorter();
  }, [sessionId]);

  const handleAnalyze = async (overrideTicker) => {
    const raw = typeof overrideTicker === 'string' ? overrideTicker : ticker;
    const { ok, value: t, error: vErr } = validateTicker(raw);
    if (!ok) { flashTickerError(vErr); return; }
    setTickerError('');
    if (overrideTicker) setTicker(t);
    // Clear stale session immediately so the old card never lingers during a new request
    setResearchData(null);
    setSessionId(null);
    setDcfData(null);
    setSwotData(null);
    setPorterData(null);
    try {
      setAnalyzing(true);
      setError(null);
      const result = await apiPost(API_ENDPOINTS.researchAnalyze, { ticker: t });
      if (!result || !result.session_id) {
        setError('Backend did not return a session ID');
        return;
      }
      setResearchData(result);
      setSessionId(result.session_id);
      // Only record to Recent after a confirmed successful 200 response
      setRecentTickers(prev => {
        const filtered = prev.filter(r => r.ticker !== t);
        return [...filtered, { ticker: t, session_id: result.session_id }].slice(-6);
      });
      if (result.dcf) {
        setDcfData({
          status: 'complete',
          current_price: result.dcf.current_price,
          scenarios: {
            base: {
              per_share: result.dcf.fair_value,
              upside_pct: result.dcf.upside_pct,
              rating: result.dcf.upside_pct > 15 ? 'BUY'
                    : result.dcf.upside_pct < -15 ? 'SELL' : 'HOLD',
            },
          },
        });
      }
      try {
        const list = await apiGet(API_ENDPOINTS.sessions);
        setSessions(unwrapList(list, 'sessions'));
      } catch (_) {}
    } catch (err) {
      setError(err.message);
      flashTickerError(err.message || 'Analyze failed — please try again');
    }
    finally { setAnalyzing(false); }
  };

  // Auto-trigger analyze when a ticker is routed in from another page
  useEffect(() => {
    if (pendingTicker?.ticker) handleAnalyze(pendingTicker.ticker);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingTicker?.nonce]);

  const handleCreateSession = async () => {
    if (!modalTicker.trim()) return;
    const t = modalTicker.toUpperCase().trim();
    setResearchData(null);
    setSessionId(null);
    setDcfData(null);
    setSwotData(null);
    setPorterData(null);
    try {
      setAnalyzing(true);
      setError(null);
      const result = await apiPost(API_ENDPOINTS.researchAnalyze, {
        ticker: t,
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
      setRecentTickers(prev => {
        const filtered = prev.filter(r => r.ticker !== (result.ticker || t));
        return [...filtered, { ticker: result.ticker || t, session_id: result.session_id }].slice(-6);
      });
      const list = await apiGet(API_ENDPOINTS.sessions);
      setSessions(unwrapList(list, 'sessions'));
    } catch (err) { setError(err.message); }
    finally { setAnalyzing(false); }
  };

  const downloadDcfExcel = async () => {
    const sid = researchData?.session_id || sessionId;
    const tk = researchData?.ticker || ticker;
    if (!isValidSessionId(sid) || !tk) return;
    const triggerDownload = (url) => {
      const a = document.createElement('a');
      a.href = url; a.rel = 'noopener';
      document.body.appendChild(a); a.click(); a.remove();
    };
    setXlsmState('running');
    try {
      const initial = await apiGet(`/api/research/${sid}/dcf/status`);
      if (initial.status === 'complete' && initial.download_url) {
        triggerDownload(initial.download_url); setXlsmState('idle'); return;
      }
      if (initial.status !== 'running') {
        await apiPost(`/api/research/${sid}/dcf/run`, { ticker: tk });
      }
      const deadline = Date.now() + 10 * 60 * 1000;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 3000));
        const s = await apiGet(`/api/research/${sid}/dcf/status`);
        if (s.status === 'complete' && s.download_url) {
          triggerDownload(s.download_url); setXlsmState('idle'); return;
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
      a.href = url;
      a.download = `BEAVER_${researchData?.ticker || 'research'}_research_report.html`;
      a.click(); URL.revokeObjectURL(url);
    } catch (e) { console.error(e); }
    finally { setReportLoading(false); }
  };

  const getScenarios = () => {
    const dcfSrc = dcfData?.scenarios || {};
    const rsSrc = researchData?.scenarios || {};
    const out = [];
    for (const key of SCENARIO_KEYS) {
      const merged = { ...(rsSrc[key] || {}), ...(dcfSrc[key] || {}) };
      const price = merged.per_share ?? merged.price_per_share;
      if (Object.keys(merged).length === 0 && price == null) continue;
      out.push({
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1),
        ...merged,
        price_per_share: price,
      });
    }
    return out;
  };

  const livePrice = researchData?.price ?? researchData?.ltp ?? researchData?.last_price
    ?? researchData?.current_price ?? researchData?.dcf?.current_price
    ?? researchData?.price_data?.price;
  const liveChangePct = researchData?.change_percent ?? researchData?.change_pct
    ?? researchData?.price_data?.change_pct;

  const scenarios = getScenarios();
  const hasSession = researchData && researchData.status !== 'not_found';
  const sym = getCurrencySymbol(researchData?.currency);

  return (
    <div className="page-content overflow-y-auto" style={{ padding: 24, backgroundColor: '#F3EEE0' }}
         data-testid="research-session-page">

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
                  onChange={(e) => setModalTicker(e.target.value.toUpperCase())}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">Sector</label>
                <select
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  value={modalSector}
                  onChange={(e) => setModalSector(e.target.value)}
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
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">Hypothesis</label>
                <textarea
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb] resize-none"
                  rows={2}
                  value={modalHypothesis}
                  onChange={(e) => setModalHypothesis(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[#64748b] uppercase tracking-wide block mb-1">Variant View</label>
                <input
                  className="w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  value={modalVariant}
                  onChange={(e) => setModalVariant(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setShowNewModal(false)}
                className="px-4 py-2 text-sm text-[#64748b] border border-[#e5e7eb] rounded-lg hover:bg-[#f8fafc]"
              >Cancel</button>
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

      {/* Ticker input */}
      <section className="mb-4" data-testid="ticker-input-section">
      <div className="flex items-center gap-3">
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
          onClick={() => handleAnalyze()}
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
      </div>
      <div
        aria-live="polite"
        style={{
          minHeight: 18, marginTop: 6,
          fontSize: 13, color: '#DC2626',
          opacity: tickerError ? 1 : 0,
          transition: 'opacity 400ms ease-out',
        }}
        data-testid="ticker-input-error"
      >
        {tickerError || ' '}
      </div>
      </section>

      {recentTickers.length > 0 && (
        <section className="flex items-center gap-2 flex-wrap mb-4">
          <span className="text-xs text-[#94a3b8]">Recent:</span>
          {[...recentTickers].reverse().map((r) => (
            <button
              key={r.session_id || r.ticker}
              onClick={() => { setSessionId(r.session_id); setTicker(r.ticker); }}
              className={cn(
                'px-3 py-1 text-xs rounded-full border transition-colors',
                r.session_id === sessionId
                  ? 'bg-[#0F3D2E] text-white border-[#0F3D2E]'
                  : 'bg-[#f8fafc] text-[#64748b] border-[#e5e7eb] hover:border-[#0F3D2E] hover:text-[#0F3D2E]'
              )}
            >{r.ticker}</button>
          ))}
        </section>
      )}

      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm mb-4">
          {error}
        </div>
      )}

      {showLoader ? (
        <CommandCenterLoader ticker={ticker} />
      ) : loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-[#2563eb]" />
          <span className="ml-2 text-[#64748b]">Loading research data...</span>
        </div>
      ) : hasSession ? (
        <>
        {researchData?.war_room && <WarRoomReport data={researchData.war_room} />}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 12 }}>
          {/* Row 1 — full-width header */}
          <div style={{ gridColumn: 'span 12' }}>
            <CompanyHeader
              researchData={researchData}
              livePrice={livePrice}
              liveChangePct={liveChangePct}
              onDownloadExcel={downloadDcfExcel}
              xlsmState={xlsmState}
              onDownloadPdf={downloadReport}
              reportLoading={reportLoading}
              sessionId={sessionId}
            />
          </div>

          {/* Sector framework strip */}
          <div style={{ gridColumn: 'span 12' }}>
            <SectorCallout sector={researchData?.sector} />
          </div>

          {/* Row 2 — Valuation / Reverse DCF / Score / Factor Scores */}
          <div style={{ gridColumn: 'span 4' }}>
            <ValuationPanel scenarios={scenarios} assumptionConfidence={researchData?.assumption_confidence} sym={sym} />
          </div>
          <div style={{ gridColumn: 'span 4' }}>
            <ReverseDcfPanel researchData={researchData} sym={sym} />
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <ScorePanel researchData={researchData} />
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <FactorScoresPanel sessionId={sessionId} scoring={researchData?.scoring} />
          </div>

          {/* Row 3 — Sensitivity / Forecast / Peer Comparison */}
          <div style={{ gridColumn: 'span 4' }}>
            <SensitivityPanel researchData={researchData} currentPrice={livePrice} />
          </div>
          <div style={{ gridColumn: 'span 4' }}>
            <ForecastPanel researchData={researchData} dcfData={dcfData} sym={sym} />
          </div>
          <div style={{ gridColumn: 'span 4' }}>
            <PeerComparisonPanel sessionId={sessionId} />
          </div>

          {/* Row 4 — History / Risk flags */}
          <div style={{ gridColumn: 'span 6' }}>
            <HistoryPanel researchData={researchData} />
          </div>
          <div style={{ gridColumn: 'span 6' }}>
            <RiskFlagsPanel researchData={researchData} />
          </div>

          {/* Row 5 — SWOT */}
          <div style={{ gridColumn: 'span 12' }}>
            <SWOTPanel swotData={swotData} loading={swotLoading} />
          </div>

          {/* Row 6 — Porter's Five Forces */}
          <div style={{ gridColumn: 'span 12' }}>
            <PorterPanel porterData={porterData} loading={porterLoading} />
          </div>

          {/* Row 7 — Financial Charts */}
          <div style={{ gridColumn: 'span 12' }}>
            <FinancialChartsPanel sessionId={sessionId} />
          </div>

          {/* Row 8 — Audit Trail */}
          <div style={{ gridColumn: 'span 12' }}>
            <AuditPanel sessionId={sessionId} />
          </div>

          {/* Row 8a — Sources Tracker */}
          <div style={{ gridColumn: 'span 12' }}>
            <SourcesPanel sessionId={sessionId} />
          </div>

          {/* Row 8b — Guardrail Log */}
          <div style={{ gridColumn: 'span 6' }}>
            <GuardrailPanel sessionId={sessionId} />
          </div>

          {/* Row 8c — Assumption History */}
          <div style={{ gridColumn: 'span 6' }}>
            <AssumptionHistoryPanel sessionId={sessionId} />
          </div>

          {/* Row 9 — F&O Pulse */}
          <div style={{ gridColumn: 'span 12' }}>
            <FnoPulseStrip ticker={researchData?.ticker} />
          </div>

          {/* Row 10 — Insider Trades */}
          <div style={{ gridColumn: 'span 12' }}>
            <InsiderTradesPanel ticker={researchData?.ticker} sym={sym} />
          </div>
        </div>
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
