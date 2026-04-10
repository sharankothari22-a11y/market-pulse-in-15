export const MiniChart = ({ title, height = 240 }) => {
  return (
    <div 
      className="mini-chart flex items-center justify-center"
      style={{ height: `${height}px` }}
      data-testid={`mini-chart-${title?.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <span className="text-[#9ca3af] text-sm">Chart: {title}</span>
    </div>
  );
};
