const TAG_STYLES = {
  FACT:           { bg: 'rgba(15,122,62,0.10)',  fg: '#0F7A3E' },
  ASSUMPTION:     { bg: 'rgba(180,120,0,0.10)',   fg: '#B47800' },
  INTERPRETATION: { bg: 'rgba(100,116,139,0.10)', fg: '#64748B' },
};

const TagChip = ({ label }) => {
  const s = TAG_STYLES[label] || TAG_STYLES.INTERPRETATION;
  return (
    <span style={{
      display: 'inline-block', fontSize: 9, fontWeight: 600,
      letterSpacing: '0.05em', textTransform: 'uppercase',
      padding: '1px 5px', borderRadius: 4,
      background: s.bg, color: s.fg, marginLeft: 5, verticalAlign: 'middle',
    }}>
      {label}
    </span>
  );
};

const extractTag = (text) => {
  const m = text.match(/^\[(FACT|ASSUMPTION|INTERPRETATION)\]\s*/i);
  if (m) return { tag: m[1].toUpperCase(), body: text.slice(m[0].length) };
  return { tag: null, body: text };
};

const QUADRANTS = [
  { key: 'strengths',     label: 'Strengths',     headerBg: 'rgba(15,122,62,0.08)',  headerFg: '#0F7A3E' },
  { key: 'weaknesses',    label: 'Weaknesses',    headerBg: 'rgba(199,55,47,0.08)',  headerFg: '#C7372F' },
  { key: 'opportunities', label: 'Opportunities', headerBg: 'rgba(37,99,235,0.08)',  headerFg: '#2563EB' },
  { key: 'threats',       label: 'Threats',       headerBg: 'rgba(180,120,0,0.08)',  headerFg: '#B47800' },
];

const Quadrant = ({ label, items, headerBg, headerFg }) => (
  <div style={{ border: '1px solid var(--bi-border-subtle, #E2E7EF)', borderRadius: 8, overflow: 'hidden' }}>
    <div style={{
      background: headerBg, color: headerFg,
      fontSize: 11, fontWeight: 700, letterSpacing: '0.06em',
      textTransform: 'uppercase', padding: '6px 10px',
    }}>
      {label}
    </div>
    <ul style={{ margin: 0, padding: '8px 10px 8px 20px', listStyle: 'disc' }}>
      {items.length === 0 ? (
        <li style={{ color: 'var(--bi-text-secondary, #4B5A75)', fontSize: 12, listStyle: 'none', marginLeft: -8 }}>—</li>
      ) : items.map((item, i) => {
        const { tag, body } = extractTag(item);
        return (
          <li key={i} style={{ fontSize: 12, color: 'var(--bi-text-primary, #0F2540)', marginBottom: 4, lineHeight: 1.5 }}>
            {body}{tag && <TagChip label={tag} />}
          </li>
        );
      })}
    </ul>
  </div>
);

const SWOTPanel = ({ swotData, loading }) => {
  const panelStyle = {
    backgroundColor: 'var(--bi-bg-card, #FFFFFF)',
    border: '1px solid var(--bi-border-subtle, #E2E7EF)',
    borderRadius: 10,
    padding: 14,
    boxShadow: 'var(--bi-shadow-card, 0 1px 2px rgba(15,37,64,0.04))',
  };

  return (
    <div style={panelStyle}>
      <div style={{
        fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
        textTransform: 'uppercase', color: 'var(--bi-text-secondary, #4B5A75)',
        marginBottom: 10,
      }}>
        SWOT Analysis
      </div>

      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--bi-text-secondary, #4B5A75)', padding: '12px 0' }}>
          Loading SWOT analysis…
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {QUADRANTS.map(({ key, label, headerBg, headerFg }) => (
            <Quadrant
              key={key}
              label={label}
              items={swotData?.[key] || []}
              headerBg={headerBg}
              headerFg={headerFg}
            />
          ))}
        </div>
      )}

      {swotData?.error && !loading && (
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
          Note: {swotData.error}
        </div>
      )}
    </div>
  );
};

export default SWOTPanel;
