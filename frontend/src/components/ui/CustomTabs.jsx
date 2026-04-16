import { useState } from 'react';

export const CustomTabs = ({ tabs, defaultTab, children }) => {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.value);

  return (
    <div data-testid="custom-tabs">
      <div
        className="flex gap-1 mb-4"
        style={{ borderBottom: '1px solid rgba(10, 22, 40, 0.12)' }}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.value;
          return (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className="relative px-4 py-2.5 transition-colors"
              style={{
                color: isActive ? '#0A1628' : 'rgba(10, 22, 40, 0.55)',
                fontSize: 11,
                letterSpacing: '0.18em',
                fontWeight: 700,
                textTransform: 'uppercase',
              }}
              onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.color = '#0A1628'; }}
              onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.color = 'rgba(10, 22, 40, 0.55)'; }}
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
