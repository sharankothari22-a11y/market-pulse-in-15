import { cn } from "@/lib/utils";

export const SignalFeedItem = ({ title, timestamp, severity, sector, signalType, transmission }) => {
  const severityColors = {
    positive: 'border-l-[#10b981]',
    warning: 'border-l-[#f59e0b]',
    danger: 'border-l-[#ef4444]',
    info: 'border-l-[#3b82f6]',
  };

  return (
    <div 
      className={cn(
        "signal-feed-item border-l-4 pl-3 py-2",
        severityColors[severity] || severityColors.info
      )}
      data-testid={`signal-item-${title?.substring(0, 20).toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <p className="text-sm text-[#f9fafb] leading-snug">{title}</p>
      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span className="text-xs text-[#9ca3af]">{timestamp}</span>
        <span className="text-xs text-[#6b7280]">•</span>
        <span className="text-xs text-[#9ca3af]">{sector}</span>
        <span className="text-xs text-[#6b7280]">•</span>
        <span className="text-xs text-[#3b82f6]">{signalType}</span>
      </div>
      {transmission && (
        <p className="text-xs text-[#9ca3af] mt-1 italic">{transmission}</p>
      )}
    </div>
  );
};
