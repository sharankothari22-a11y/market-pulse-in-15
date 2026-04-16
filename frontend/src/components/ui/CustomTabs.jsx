import { useState } from 'react';
import { cn } from '@/lib/utils';

export const CustomTabs = ({ tabs, defaultTab, children }) => {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.value);

  return (
    <div data-testid="custom-tabs">
      <div
        className="flex gap-1 mb-4"
        style={{ borderBottom: '1px solid rgba(201, 168, 76, 0.18)' }}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.value;
          return (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className="relative px-4 py-2.5 transition-colors"
              style={{
                color: isActive ? '#C9A84C' : 'rgba(245, 240, 232, 0.55)',
                fontSize: 11,
                letterSpacing: '0.18em',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
              onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.color = '#F5F0E8'; }}
              onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.color = 'rgba(245, 240, 232, 0.55)'; }}
              data-testid={`tab-${tab.value}`}
            >
              {tab.label}
              {isActive && (
                <span
                  className="absolute bottom-0 left-0 right-0"
                  style={{ height: 2, backgroundColor: '#C9A84C' }}
                />
              )}
            </button>
          );
        })}
      </div>
      {typeof children === 'function' ? children(activeTab) : children}
    </div>
  );
};
