const RATING_STYLES = {
  Low:    { bg: 'rgba(15,122,62,0.10)',  fg: '#0F7A3E' },
  Medium: { bg: 'rgba(180,120,0,0.10)',  fg: '#B47800' },
  High:   { bg: 'rgba(199,55,47,0.10)', fg: '#C7372F' },
};

const RatingChip = ({ rating }) => {
  const s = RATING_STYLES[rating] || RATING_STYLES.Medium;
  return (
    <span style={{
      display: 'inline-block', fontSize: 10, fontWeight: 700,
      padding: '2px 8px', borderRadius: 4,
      background: s.bg, color: s.fg, whiteSpace: 'nowrap',
    }}>
      {rating || 'Medium'}
    </span>
  );
};

const PorterPanel = ({ porterData, loading }) => {
  const panelStyle = {
    backgroundColor: 'var(--bi-bg-card, #FFFFFF)',
    border: '1px solid var(--bi-border-subtle, #E2E7EF)',
    borderRadius: 10,
    padding: 14,
    boxShadow: 'var(--bi-shadow-card, 0 1px 2px rgba(15,37,64,0.04))',
  };

  const forces = porterData?.forces || [];

  return (
    <div style={panelStyle}>
      <div style={{
        fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
        textTransform: 'uppercase', color: 'var(--bi-text-secondary, #4B5A75)',
        marginBottom: 10,
      }}>
        Porter's Five Forces
      </div>

      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--bi-text-secondary, #4B5A75)', padding: '12px 0' }}>
          Loading Porter's Five Forces…
        </div>
      ) : forces.length === 0 ? (
        <div style={{ fontSize: 12, color: 'var(--bi-text-secondary, #4B5A75)', padding: '12px 0' }}>
          Porter's Five Forces analysis pending
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['Force', 'Rating', 'Rationale'].map((h) => (
                <th key={h} style={{
                  textAlign: 'left', padding: '4px 8px',
                  fontSize: 10, fontWeight: 600, letterSpacing: '0.05em',
                  textTransform: 'uppercase', color: 'var(--bi-text-secondary, #4B5A75)',
                  borderBottom: '1px solid var(--bi-border-subtle, #E2E7EF)',
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {forces.map((f, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--bi-border-subtle, #E2E7EF)' }}>
                <td style={{ padding: '6px 8px', fontWeight: 600, whiteSpace: 'nowrap', color: 'var(--bi-text-primary, #0F2540)' }}>
                  {f.name}
                </td>
                <td style={{ padding: '6px 8px', whiteSpace: 'nowrap' }}>
                  <RatingChip rating={f.rating} />
                </td>
                <td style={{ padding: '6px 8px', color: 'var(--bi-text-primary, #0F2540)', lineHeight: 1.5 }}>
                  {f.rationale}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {porterData?.error && !loading && forces.length === 0 && (
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
          Note: {porterData.error}
        </div>
      )}
    </div>
  );
};

export default PorterPanel;
