import { cn } from '@/lib/utils';

export const StatusBadge = ({ variant = 'info', children }) => {
  const variants = {
    success: { bg: 'rgba(76, 175, 125, 0.14)',  fg: '#4CAF7D', bd: 'rgba(76, 175, 125, 0.4)' },
    warning: { bg: 'rgba(230, 165, 68, 0.14)',  fg: '#E6A544', bd: 'rgba(230, 165, 68, 0.4)' },
    danger:  { bg: 'rgba(224, 82, 82, 0.14)',   fg: '#E05252', bd: 'rgba(224, 82, 82, 0.4)' },
    info:    { bg: 'rgba(201, 168, 76, 0.12)',  fg: '#C9A84C', bd: 'rgba(201, 168, 76, 0.4)' },
  };
  const v = variants[variant] || variants.info;

  return (
    <span
      className="inline-flex items-center"
      style={{
        padding: '2px 8px',
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        borderRadius: 2,
        backgroundColor: v.bg,
        color: v.fg,
        border: `1px solid ${v.bd}`,
      }}
      data-testid={`status-badge-${variant}`}
    >
      {children}
    </span>
  );
};
