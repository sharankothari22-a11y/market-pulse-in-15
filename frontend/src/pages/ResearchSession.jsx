import { useState, useEffect, useRef } from 'react';
import { validateTicker } from '@/lib/ticker';
import {
  Search, Loader2, Plus, X, AlertTriangle, CheckCircle2,
} from 'lucide-react';
import { apiGet, apiPost, API_ENDPOINTS } from '@/services/api';
import { cn } from '@/lib/utils';

const SCENARIO_KEYS = ['bull', 'base', 'bear'];

const isValidSessionId = (id) =>
  !!id && typeof id === 'string' && id !== 'undefined' && id !== 'null' && id.length > 2;

const unwrapList = (raw, key) => {
  if (Array.isArray(raw)) return raw;
  if (raw && Array.isArray(raw[key])) return raw[key];
  return [];
};

// ─── formatting helpers ────────────────────────────────────────────────────
const fmtInr = (n) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
};
const fmtInr2 = (n) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const fmtPct = (n, digits = 1) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  return `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`;
};
const fmtPctPlain = (n, digits = 1) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return `${Number(n).toFixed(digits)}%`;
};
// Heuristic large-money formatter. If the value is clearly in INR rupees,
// collapse to lakh crore. If it's already in millions/crores, still renders
// a reasonable compact string.
const fmtLargeInr = (n) => {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  if (v >= 1e13) return `₹${(v / 1e13).toFixed(1)} lakh cr`;
  if (v >= 1e11) return `₹${(v / 1e7).toLocaleString('en-IN', { maximumFractionDigits: 0 })} cr`;
  if (v >= 1e7)  return `₹${(v / 1e7).toLocaleString('en-IN', { maximumFractionDigits: 2 })} cr`;
  return `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
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
  backgroundColor: 'var(--bi-bg-card, #ffffff)',
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
}) => {
  const ticker = researchData?.ticker || '—';
  const name = researchData?.long_name || researchData?.name || researchData?.company_name || '';
  const sector = researchData?.sector || '—';
  const sid = (researchData?.session_id || '').slice(-12);
  const status = researchData?.status || 'Active';
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
            {priceMissing ? '—' : fmtInr2(livePrice)}
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
              backgroundColor: 'var(--bi-navy-700, #1B3A6B)',
              color: '#ffffff', fontSize: 13, fontWeight: 500,
              border: '1px solid var(--bi-navy-700, #1B3A6B)',
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
              backgroundColor: 'var(--bi-navy-700, #1B3A6B)',
              color: '#ffffff', fontSize: 13, fontWeight: 500,
              border: '1px solid var(--bi-navy-700, #1B3A6B)',
            }}
            data-testid="header-download-pdf"
          >
            {reportLoading && <Loader2 className="w-3 h-3 animate-spin" />}
            {reportLoading ? 'Loading…' : 'Download Report'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Panel 2 — Valuation (base scenario hero, bull/bear secondary) ─────────
const ValuationPanel = ({ scenarios }) => {
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
            {fmtInr(base.price_per_share)}
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
            <div title={base.key_assumption} style={{
              fontSize: 12, color: 'var(--bi-text-secondary, #4B5A75)',
              marginTop: 8, lineHeight: 1.4,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {base.key_assumption}
            </div>
          )}
        </>
      )}
      <div style={dividerStyle} />
      <div style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)',
                    display: 'flex', gap: 10, fontVariantNumeric: 'tabular-nums' }}>
        <span>Bull: <strong style={{ color: 'var(--bi-text-secondary, #4B5A75)', fontWeight: 500 }}>
          {bull?.price_per_share != null ? fmtInr(bull.price_per_share) : '—'}
        </strong></span>
        <span>·</span>
        <span>Bear: <strong style={{ color: 'var(--bi-text-secondary, #4B5A75)', fontWeight: 500 }}>
          {bear?.price_per_share != null ? fmtInr(bear.price_per_share) : '—'}
        </strong></span>
      </div>
    </Panel>
  );
};

// ─── Panel 3 — Market-implied (reverse DCF) ────────────────────────────────
const ReverseDcfPanel = ({ researchData }) => {
  const rd = researchData?.reverse_dcf
    || researchData?.scenarios?.reverse_dcf
    || null;
  const rows = [
    { label: 'Implied growth', value: rd?.implied_growth_rate != null ? fmtPctPlain(rd.implied_growth_rate) : null },
    { label: 'Implied WACC',   value: rd?.implied_wacc != null ? fmtPctPlain(rd.implied_wacc) : null },
    { label: 'Market cap',     value: rd?.market_cap != null ? fmtLargeInr(rd.market_cap) : null },
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
const DEFAULT_DIMS = ['quality', 'growth', 'valuation', 'momentum', 'sentiment'];

const pickDimensionScores = (scoring) => {
  if (!scoring) return [];
  // Try a few plausible shapes.
  const src = scoring.dimensions || scoring.scores || scoring.pillars || scoring;
  const out = [];
  for (const key of DEFAULT_DIMS) {
    const v = src?.[key] ?? scoring?.[`${key}_score`] ?? scoring?.[key];
    const num = typeof v === 'number' ? v
      : typeof v === 'object' && v != null ? (v.score ?? v.value ?? v.pct) : null;
    if (typeof num === 'number' && !Number.isNaN(num)) {
      out.push({ key, label: key.charAt(0).toUpperCase() + key.slice(1),
                 score: Math.max(0, Math.min(100, num)) });
    }
  }
  return out;
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {dims.map((d) => (
            <div key={d.key} className="flex items-center gap-2">
              <span style={{ fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)',
                             width: 66, flexShrink: 0 }}>
                {d.label}
              </span>
              <div style={{ flex: 1, height: 4, borderRadius: 2,
                            backgroundColor: 'var(--bi-bg-subtle, #EEF1F6)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${d.score}%`,
                              backgroundColor: 'var(--bi-navy-700, #1B3A6B)' }} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--bi-text-primary, #0F2540)',
                             width: 28, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                {Math.round(d.score)}
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
const ForecastPanel = ({ researchData, dcfData }) => {
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
            <th style={head}>EBIT</th>
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
                {r.ebit != null ? Number(r.ebit).toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '—'}
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
        All figures ₹ {(dcfData?.meta?.units || researchData?.dcf_summary?.meta?.units || '').toLowerCase() === 'millions' ? 'mn' : 'cr'}
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
export const ResearchSession = ({ onSessionChange, pendingTicker }) => {
  const [ticker, setTicker] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [researchData, setResearchData] = useState(null);
  const [dcfData, setDcfData] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [xlsmState, setXlsmState] = useState('idle');
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
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

  const handleAnalyze = async (overrideTicker) => {
    const raw = typeof overrideTicker === 'string' ? overrideTicker : ticker;
    const { ok, value: t, error: vErr } = validateTicker(raw);
    if (!ok) { flashTickerError(vErr); return; }
    setTickerError('');
    if (overrideTicker) setTicker(t);
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
    const src = (dcfData?.scenarios && Object.keys(dcfData.scenarios).length > 0)
      ? dcfData.scenarios
      : researchData?.scenarios;
    if (!src) return [];
    return SCENARIO_KEYS
      .filter((key) => src[key] != null)
      .map((key) => ({
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1),
        ...src[key],
        price_per_share: src[key]?.per_share ?? src[key]?.price_per_share,
      }));
  };

  const livePrice = researchData?.price ?? researchData?.ltp ?? researchData?.last_price
    ?? researchData?.current_price ?? researchData?.dcf?.current_price
    ?? researchData?.price_data?.price;
  const liveChangePct = researchData?.change_percent ?? researchData?.change_pct
    ?? researchData?.price_data?.change_pct;

  const scenarios = getScenarios();
  const hasSession = researchData && researchData.status !== 'not_found';

  return (
    <div className="page-content overflow-y-auto" style={{ padding: 24, backgroundColor: '#ffffff' }}
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

      {sessions.length > 0 && (() => {
        const seen = new Set();
        const unique = sessions.filter((s) => {
          if (!s.ticker || seen.has(s.ticker)) return false;
          seen.add(s.ticker); return true;
        });
        return (
          <section className="flex items-center gap-2 flex-wrap mb-4">
            <span className="text-xs text-[#94a3b8]">Recent:</span>
            {unique.slice(0, 8).map((s) => (
              <button
                key={s.session_id || s._id}
                onClick={() => { setSessionId(s.session_id); setTicker(s.ticker || ''); }}
                className={cn(
                  'px-3 py-1 text-xs rounded-full border transition-colors',
                  (s.session_id || s._id) === sessionId
                    ? 'bg-[#2563eb] text-white border-[#2563eb]'
                    : 'bg-[#f8fafc] text-[#64748b] border-[#e5e7eb] hover:border-[#2563eb] hover:text-[#2563eb]'
                )}
              >{s.ticker}</button>
            ))}
          </section>
        );
      })()}

      {error && (
        <div className="p-3 bg-[#dc2626]/10 border border-[#dc2626]/30 rounded-lg text-[#dc2626] text-sm mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-[#2563eb]" />
          <span className="ml-2 text-[#64748b]">Loading research data...</span>
        </div>
      ) : hasSession ? (
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
            />
          </div>

          {/* Row 2 — Valuation / Reverse DCF / Score */}
          <div style={{ gridColumn: 'span 4' }}>
            <ValuationPanel scenarios={scenarios} />
          </div>
          <div style={{ gridColumn: 'span 4' }}>
            <ReverseDcfPanel researchData={researchData} />
          </div>
          <div style={{ gridColumn: 'span 4' }}>
            <ScorePanel researchData={researchData} />
          </div>

          {/* Row 3 — Sensitivity / Forecast */}
          <div style={{ gridColumn: 'span 6' }}>
            <SensitivityPanel researchData={researchData} currentPrice={livePrice} />
          </div>
          <div style={{ gridColumn: 'span 6' }}>
            <ForecastPanel researchData={researchData} dcfData={dcfData} />
          </div>

          {/* Row 4 — History / Risk flags */}
          <div style={{ gridColumn: 'span 6' }}>
            <HistoryPanel researchData={researchData} />
          </div>
          <div style={{ gridColumn: 'span 6' }}>
            <RiskFlagsPanel researchData={researchData} />
          </div>
        </div>
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
