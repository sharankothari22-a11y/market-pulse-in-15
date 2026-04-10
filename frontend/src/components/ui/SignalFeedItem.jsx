import { cn } from "@/lib/utils";

export const SignalFeedItem = ({ title, timestamp, severity, sector, signalType, transmission }) => {
  const severityColors = {
    positive: 'border-l-[#16a34a]',
    warning: 'border-l-[#d97706]',
    danger: 'border-l-[#dc2626]',
    info: 'border-l-[#2563eb]',
  };

  return (
    <div 
      className={cn(
        "signal-feed-item border-l-4 pl-3 py-2",
        severityColors[severity] || severityColors.info
      )}
      data-testid={`signal-item-${title?.substring(0, 20).toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <p className="text-sm text-[#0f172a] leading-snug">{title}</p>
      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span className="text-xs text-[#64748b]">{timestamp}</span>
        <span className="text-xs text-[#94a3b8]">•</span>
        <span className="text-xs text-[#64748b]">{sector}</span>
        <span className="text-xs text-[#94a3b8]">•</span>
        <span className="text-xs text-[#2563eb]">{signalType}</span>
      </div>
      {transmission && (
        <p className="text-xs text-[#64748b] mt-1 italic">{transmission}</p>
      )}
    </div>
  );
};
