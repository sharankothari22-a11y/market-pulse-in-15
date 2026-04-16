export const StatusBadge = ({ variant = 'info', children }) => {
  const variants = {
    success: { bg: 'rgba(45, 106, 79, 0.12)',   fg: '#2D6A4F', bd: 'rgba(45, 106, 79, 0.4)' },
    warning: { bg: 'rgba(181, 134, 44, 0.14)',  fg: '#B5862C', bd: 'rgba(181, 134, 44, 0.4)' },
    danger:  { bg: 'rgba(224, 82, 82, 0.12)',   fg: '#E05252', bd: 'rgba(224, 82, 82, 0.4)' },
    info:    { bg: 'rgba(10, 22, 40, 0.06)',    fg: '#0A1628', bd: 'rgba(201, 168, 76, 0.4)' },
  };
  const v = variants[variant] || variants.info;

  return (
    <span
      className="inline-flex items-center"
      style={{
        padding: '2px 8px',
        fontSize: 10,
        fontWeight: 700,
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
