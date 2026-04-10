import { cn } from "@/lib/utils";

export const ScenarioBadge = ({ label, price, upside }) => {
  const colors = {
    Bull: 'bg-[#16a34a]/10 border-[#16a34a] text-[#16a34a]',
    Base: 'bg-[#2563eb]/10 border-[#2563eb] text-[#2563eb]',
    Bear: 'bg-[#dc2626]/10 border-[#dc2626] text-[#dc2626]',
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
