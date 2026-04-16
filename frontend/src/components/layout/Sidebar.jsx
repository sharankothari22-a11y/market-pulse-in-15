import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Search,
  Bell,
  Globe,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const BEAVER_LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-review-38/artifacts/tqw73ol3_Screenshot%202026-04-16%20at%206.20.25%E2%80%AFPM.png';

const navItems = [
  { id: 'market-overview',   label: 'MARKET OVERVIEW',   icon: LayoutDashboard, path: '/' },
  { id: 'research-session',  label: 'RESEARCH SESSION',  icon: Search,          path: '/research' },
  { id: 'signals-alerts',    label: 'SIGNALS & ALERTS',  icon: Bell,            path: '/signals' },
  { id: 'macro-dashboard',   label: 'MACRO DASHBOARD',   icon: Globe,           path: '/macro' },
];

const bottomItems = [
  { id: 'settings', label: 'SETTINGS', icon: Settings, path: '/settings' },
];

export const Sidebar = ({ activePage, onNavigate }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <motion.aside
      className="sidebar h-screen flex flex-col relative"
      initial={{ width: 72 }}
      animate={{ width: isExpanded ? 240 : 72 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
      style={{
        backgroundColor: '#0A1628',
        borderRight: '1px solid rgba(201, 168, 76, 0.2)',
      }}
      data-testid="sidebar"
    >
      {/* Branding */}
      <div
        className="py-4 px-3 flex flex-col items-center justify-center"
        style={{ borderBottom: '1px solid rgba(201, 168, 76, 0.2)', minHeight: 92 }}
      >
        {!isExpanded ? (
          <div style={{
            width: 44, height: 44, borderRadius: '50%', overflow: 'hidden',
            backgroundColor: '#0A1628',
          }}>
            <img
              src={BEAVER_LOGO_URL}
              alt="Beaver"
              style={{ width: '100%', height: '100%', objectFit: 'cover', mixBlendMode: 'lighten' }}
            />
          </div>
        ) : (
          <motion.div
            className="flex flex-col items-center text-center w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.25 }}
          >
            <div style={{
              width: 72, height: 72, borderRadius: '50%', overflow: 'hidden',
              backgroundColor: '#0A1628',
            }}>
              <img
                src={BEAVER_LOGO_URL}
                alt="Beaver Intelligence"
                style={{ width: '100%', height: '100%', objectFit: 'cover', mixBlendMode: 'lighten' }}
              />
            </div>
            <div
              className="text-[#C9A84C] font-medium mt-2"
              style={{ fontSize: 9, letterSpacing: '0.45em' }}
            >
              INTELLIGENCE
            </div>
          </motion.div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 flex flex-col gap-0.5">
        {navItems.map((item) => {
          const isActive = activePage === item.path;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.path)}
              className={cn(
                'group w-full flex items-center transition-all relative',
                'pl-4 pr-3 py-3',
              )}
              style={{
                color: isActive ? '#C9A84C' : 'rgba(245, 240, 232, 0.72)',
                backgroundColor: isActive ? 'rgba(30, 58, 95, 0.5)' : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(30, 58, 95, 0.3)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
              }}
              data-testid={`nav-${item.id}`}
            >
              {/* Active left bar */}
              <span
                className="absolute left-0 top-0 bottom-0"
                style={{
                  width: '2px',
                  backgroundColor: isActive ? '#C9A84C' : 'transparent',
                  transition: 'background-color 0.2s',
                }}
              />
              <item.icon
                className="w-[18px] h-[18px] flex-shrink-0"
                strokeWidth={isActive ? 2 : 1.5}
              />
              <motion.span
                className="ml-3 font-medium whitespace-nowrap overflow-hidden"
                style={{
                  fontSize: 11,
                  letterSpacing: '0.22em',
                }}
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? 'auto' : 0 }}
                transition={{ duration: 0.2 }}
              >
                {item.label}
              </motion.span>
            </button>
          );
        })}
      </nav>

      {/* Divider */}
      <div
        className="mx-3"
        style={{ height: '1px', backgroundColor: 'rgba(201, 168, 76, 0.2)' }}
      />

      {/* Bottom items */}
      <div className="py-3">
        {bottomItems.map((item) => {
          const isActive = activePage === item.path;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.path)}
              className="w-full flex items-center pl-4 pr-3 py-3 transition-colors"
              style={{
                color: isActive ? '#C9A84C' : 'rgba(245, 240, 232, 0.55)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#C9A84C'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = isActive ? '#C9A84C' : 'rgba(245, 240, 232, 0.55)'; }}
              data-testid={`nav-${item.id}`}
            >
              <item.icon className="w-[18px] h-[18px] flex-shrink-0" strokeWidth={1.5} />
              <motion.span
                className="ml-3 font-medium whitespace-nowrap overflow-hidden"
                style={{ fontSize: 11, letterSpacing: '0.22em' }}
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? 'auto' : 0 }}
                transition={{ duration: 0.2 }}
              >
                {item.label}
              </motion.span>
            </button>
          );
        })}
      </div>

      {/* Tagline */}
      {isExpanded && (
        <motion.div
          className="px-4 pb-4 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          style={{
            borderTop: '1px solid rgba(201, 168, 76, 0.15)',
            paddingTop: 14,
          }}
        >
          <div
            style={{
              color: 'rgba(201, 168, 76, 0.7)',
              fontSize: 8.5,
              letterSpacing: '0.28em',
              lineHeight: 1.6,
            }}
          >
            EQUITY RESEARCH<br />
            <span style={{ color: 'rgba(201, 168, 76, 0.4)' }}>·</span>&nbsp;
            DECISION INTELLIGENCE
          </div>
        </motion.div>
      )}
    </motion.aside>
  );
};
