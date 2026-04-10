import { useState } from 'react';
import { cn } from "@/lib/utils";

export const CustomTabs = ({ tabs, defaultTab, children }) => {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.value);

  return (
    <div data-testid="custom-tabs">
      <div className="flex gap-1 border-b border-[#e5e7eb] mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors relative",
              activeTab === tab.value
                ? "text-[#2563eb]"
                : "text-[#64748b] hover:text-[#0f172a]"
            )}
            data-testid={`tab-${tab.value}`}
          >
            {tab.label}
            {activeTab === tab.value && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2563eb]" />
            )}
          </button>
        ))}
      </div>
      {typeof children === 'function' ? children(activeTab) : children}
    </div>
  );
};
