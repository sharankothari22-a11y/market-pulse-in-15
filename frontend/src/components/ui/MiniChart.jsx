export const MiniChart = ({ title, height = 240 }) => {
  return (
    <div
      className="mini-chart flex items-center justify-center"
      style={{ height: `${height}px` }}
      data-testid={`mini-chart-${title?.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <span style={{ color: 'rgba(10, 22, 40, 0.5)', fontSize: 12, letterSpacing: '0.08em' }}>
        Chart · {title}
      </span>
    </div>
  );
};
