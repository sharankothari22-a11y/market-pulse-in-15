import { cn } from "@/lib/utils";

export const MetricCard = ({ title, value, change, changeType, subtitle }) => {
  const changeColor = {
    positive: 'text-[#10b981]',
    negative: 'text-[#ef4444]',
    neutral: 'text-[#9ca3af]',
  };

  return (
    <div 
      className="metric-card"
      data-testid={`metric-card-${title?.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <p className="text-xs text-[#9ca3af] uppercase tracking-wider mb-1">{title}</p>
      <p className="text-2xl font-semibold text-[#f9fafb] font-outfit">{value}</p>
      <div className="flex items-center gap-2 mt-1">
        <span className={cn("text-sm font-medium", changeColor[changeType] || changeColor.neutral)}>
          {change}
        </span>
        {subtitle && <span className="text-xs text-[#9ca3af]">{subtitle}</span>}
      </div>
    </div>
  );
};
