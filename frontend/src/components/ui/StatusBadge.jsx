import { cn } from "@/lib/utils";

export const StatusBadge = ({ variant = 'info', children }) => {
  const variants = {
    success: 'bg-[#10b981]/20 text-[#10b981] border-[#10b981]/30',
    warning: 'bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/30',
    danger: 'bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/30',
    info: 'bg-[#3b82f6]/20 text-[#3b82f6] border-[#3b82f6]/30',
  };

  return (
    <span 
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border",
        variants[variant]
      )}
      data-testid={`status-badge-${variant}`}
    >
      {children}
    </span>
  );
};
