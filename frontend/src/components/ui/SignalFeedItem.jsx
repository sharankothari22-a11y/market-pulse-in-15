import { cn } from '@/lib/utils';

export const SignalFeedItem = ({ title, timestamp, severity, sector, signalType, transmission }) => {
  const severityColor = {
    positive: '#4CAF7D',
    warning:  '#E6A544',
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
      <p style={{ color: '#F5F0E8', fontSize: 13, lineHeight: 1.5 }}>{title}</p>
      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span style={{ color: 'rgba(245, 240, 232, 0.5)', fontSize: 10.5 }}>{timestamp}</span>
        {sector && (
          <>
            <span style={{ color: 'rgba(201, 168, 76, 0.4)' }}>·</span>
            <span style={{ color: 'rgba(245, 240, 232, 0.5)', fontSize: 10.5 }}>{sector}</span>
          </>
        )}
        {signalType && (
          <>
            <span style={{ color: 'rgba(201, 168, 76, 0.4)' }}>·</span>
            <span style={{ color: '#C9A84C', fontSize: 10.5, letterSpacing: '0.08em' }}>{signalType}</span>
          </>
        )}
      </div>
      {transmission && (
        <p style={{ color: 'rgba(245, 240, 232, 0.5)', fontSize: 11, marginTop: 4, fontStyle: 'italic' }}>
          {transmission}
        </p>
      )}
    </div>
  );
};
