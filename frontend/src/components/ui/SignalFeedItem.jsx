export const SignalFeedItem = ({ title, timestamp, severity, sector, signalType, transmission }) => {
  const severityColor = {
    positive: '#2D6A4F',
    warning:  '#B5862C',
    danger:   '#E05252',
    negative: '#E05252',
    info:     '#C9A84C',
  }[severity] || '#C9A84C';

  return (
    <div
      className="signal-feed-item pl-3 py-2.5"
      style={{ borderLeft: `3px solid ${severityColor}` }}
      data-testid={`signal-item-${title?.substring(0, 20).toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <p style={{ color: '#0A1628', fontSize: 13, lineHeight: 1.5, fontWeight: 500 }}>{title}</p>
      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span style={{ color: 'rgba(10, 22, 40, 0.55)', fontSize: 10.5 }}>{timestamp}</span>
        {sector && (
          <>
            <span style={{ color: 'rgba(201, 168, 76, 0.7)' }}>·</span>
            <span style={{ color: 'rgba(10, 22, 40, 0.55)', fontSize: 10.5 }}>{sector}</span>
          </>
        )}
        {signalType && (
          <>
            <span style={{ color: 'rgba(201, 168, 76, 0.7)' }}>·</span>
            <span style={{ color: '#B5862C', fontSize: 10.5, letterSpacing: '0.08em', fontWeight: 600 }}>{signalType}</span>
          </>
        )}
      </div>
      {transmission && (
        <p style={{ color: 'rgba(10, 22, 40, 0.55)', fontSize: 11, marginTop: 4, fontStyle: 'italic' }}>
          {transmission}
        </p>
      )}
    </div>
  );
};
