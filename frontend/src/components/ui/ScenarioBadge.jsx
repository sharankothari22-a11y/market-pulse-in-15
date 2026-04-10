import { cn } from "@/lib/utils";

export const ScenarioBadge = ({ label, price, upside }) => {
  const colors = {
    Bull: 'bg-[#10b981]/20 border-[#10b981] text-[#10b981]',
    Base: 'bg-[#3b82f6]/20 border-[#3b82f6] text-[#3b82f6]',
    Bear: 'bg-[#ef4444]/20 border-[#ef4444] text-[#ef4444]',
  };

  return (
    <div 
      className={cn(
        "scenario-badge px-4 py-3 rounded-lg border",
        colors[label] || colors.Base
      )}
      data-testid={`scenario-badge-${label?.toLowerCase()}`}
    >
      <p className="text-xs uppercase tracking-wider opacity-80">{label}</p>
      <p className="text-lg font-semibold font-outfit mt-1">{price}</p>
      <p className="text-sm">{upside}</p>
    </div>
  );
};
