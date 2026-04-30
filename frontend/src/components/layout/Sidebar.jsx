import { LayoutDashboard, Search } from 'lucide-react';

const navItems = [
  { id: 'market-overview',  label: 'Market overview',  icon: LayoutDashboard, path: '/' },
  { id: 'research-session', label: 'Research session', icon: Search,          path: '/research' },
  // HIDDEN FOR DEMO — re-enable when feature is ready
  // { id: 'signals-alerts',   label: 'Signals & alerts', icon: Bell,            path: '/signals' },
  // HIDDEN FOR DEMO — re-enable when feature is ready
  // { id: 'macro-dashboard',  label: 'Macro dashboard',  icon: Globe,           path: '/macro' },
  // HIDDEN FOR DEMO — re-enable when feature is ready
  // { id: 'settings',         label: 'Settings',         icon: Settings,        path: '/settings' },
];

export const Sidebar = ({ activePage, onNavigate }) => {
  return (
    <aside
      className="flex flex-col flex-shrink-0"
      style={{
        width: 220,
        backgroundColor: 'var(--bi-bg-card)',
        borderRight: '1px solid var(--bi-border-subtle)',
      }}
      data-testid="sidebar"
    >
      <nav className="flex-1 py-4">
        {navItems.map((item) => {
          const isActive = activePage === item.path;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.path)}
              className="w-full flex items-center transition-colors relative"
              style={{
                gap: 12,
                padding: '10px 16px',
                color: isActive ? 'var(--bi-navy-900)' : 'var(--bi-text-secondary)',
                backgroundColor: isActive ? 'var(--bi-navy-100)' : 'transparent',
                fontSize: 14,
                fontWeight: 500,
                textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.backgroundColor = 'var(--bi-bg-subtle)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
              }}
              data-testid={`nav-${item.id}`}
            >
              {isActive && (
                <span
                  style={{
                    position: 'absolute', left: 0, top: 0, bottom: 0,
                    width: 3, backgroundColor: 'var(--bi-navy-700)',
                  }}
                />
              )}
              <Icon size={18} strokeWidth={isActive ? 2 : 1.75} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

    </aside>
  );
};
