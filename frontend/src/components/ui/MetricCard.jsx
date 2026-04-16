export const MetricCard = ({ title, value, change, changeType, subtitle }) => {
  const changeColor = {
    positive: '#2D6A4F',
    negative: '#E05252',
    neutral:  'rgba(10, 22, 40, 0.5)',
  };

  const arrow = changeType === 'positive' ? '▲' : changeType === 'negative' ? '▼' : '';

  return (
    <div
      className="metric-card"
      data-testid={`metric-card-${title?.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <p
        className="mb-1.5"
        style={{
          color: '#0A1628',
          fontSize: 9.5,
          letterSpacing: '0.26em',
          fontWeight: 700,
          textTransform: 'uppercase',
        }}
      >
        {title}
      </p>
      <p
        className="tabular-nums"
        style={{
          color: '#0A1628',
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: '-0.005em',
          lineHeight: 1.1,
        }}
      >
        {value}
      </p>
      <div className="flex items-center gap-2 mt-2">
        {change && (
          <span
            className="tabular-nums"
            style={{
              color: changeColor[changeType] || changeColor.neutral,
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            {arrow && <span style={{ marginRight: 4 }}>{arrow}</span>}
            {change}
          </span>
        )}
        {subtitle && (
          <span style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 10.5 }}>
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
};
