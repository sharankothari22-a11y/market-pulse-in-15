import { cn } from '@/lib/utils';

export const MetricCard = ({ title, value, change, changeType, subtitle }) => {
  const changeColor = {
    positive: '#4CAF7D',
    negative: '#E05252',
    neutral:  'rgba(245, 240, 232, 0.55)',
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
          color: '#C9A84C',
          fontSize: 9.5,
          letterSpacing: '0.26em',
          fontWeight: 600,
          textTransform: 'uppercase',
        }}
      >
        {title}
      </p>
      <p
        className="tabular-nums"
        style={{
          color: '#F5F0E8',
          fontSize: 22,
          fontWeight: 600,
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
              fontWeight: 600,
            }}
          >
            {arrow && <span style={{ marginRight: 4 }}>{arrow}</span>}
            {change}
          </span>
        )}
        {subtitle && (
          <span style={{ color: 'rgba(245, 240, 232, 0.4)', fontSize: 10.5 }}>
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
};
