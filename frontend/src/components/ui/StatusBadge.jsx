import { cn } from "@/lib/utils";

export const StatusBadge = ({ variant = 'info', children }) => {
  const variants = {
    success: 'bg-[#16a34a]/10 text-[#16a34a] border-[#16a34a]/30',
    warning: 'bg-[#d97706]/10 text-[#d97706] border-[#d97706]/30',
    danger: 'bg-[#dc2626]/10 text-[#dc2626] border-[#dc2626]/30',
    info: 'bg-[#2563eb]/10 text-[#2563eb] border-[#2563eb]/30',
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
