import { useState } from 'react';
import { cn } from "@/lib/utils";

export const CustomTabs = ({ tabs, defaultTab, children }) => {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.value);

  return (
    <div data-testid="custom-tabs">
      <div className="flex gap-1 border-b border-[#1f2937] mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors relative",
              activeTab === tab.value
                ? "text-[#3b82f6]"
                : "text-[#9ca3af] hover:text-[#f9fafb]"
            )}
            data-testid={`tab-${tab.value}`}
          >
            {tab.label}
            {activeTab === tab.value && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#3b82f6]" />
            )}
          </button>
        ))}
      </div>
      {typeof children === 'function' ? children(activeTab) : children}
    </div>
  );
};
