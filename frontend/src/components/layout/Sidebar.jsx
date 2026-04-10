import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Search, 
  Bell, 
  Globe, 
  Settings,
  ChevronRight
} from 'lucide-react';
import { cn } from "@/lib/utils";

const navItems = [
  { id: 'market-overview', label: 'Market Overview', icon: LayoutDashboard, path: '/' },
  { id: 'research-session', label: 'Research Session', icon: Search, path: '/research' },
  { id: 'signals-alerts', label: 'Signals & Alerts', icon: Bell, path: '/signals' },
  { id: 'macro-dashboard', label: 'Macro Dashboard', icon: Globe, path: '/macro' },
];

const bottomItems = [
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];

export const Sidebar = ({ activePage, onNavigate }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <motion.aside
      className="sidebar h-screen bg-[#f1f5f9] border-r border-[#e5e7eb] flex flex-col"
      initial={{ width: 64 }}
      animate={{ width: isExpanded ? 200 : 64 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
      data-testid="sidebar"
    >
      {/* Logo */}
      <div className="p-3 flex items-center justify-center border-b border-[#e5e7eb]">
        <img 
          src="https://static.prod-images.emergentagent.com/jobs/2a0b1db4-ca8c-467b-bf34-af2a2ee9980c/images/32c0104271c6d67f5f4a6ff72b878f0bfe83fedaebfc6403d600733719158aea.png"
          alt="Logo"
          className="w-10 h-10 object-contain"
        />
        <motion.span
          className="ml-2 text-[#0f172a] font-outfit font-semibold text-lg whitespace-nowrap overflow-hidden"
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? 'auto' : 0 }}
          transition={{ duration: 0.2 }}
        >
          MarketPulse
        </motion.span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.path)}
            className={cn(
              "w-full flex items-center px-4 py-3 transition-colors",
              activePage === item.path
                ? "bg-[#2563eb]/10 text-[#2563eb] border-r-2 border-[#2563eb]"
                : "text-[#64748b] hover:bg-[#e5e7eb] hover:text-[#0f172a]"
            )}
            data-testid={`nav-${item.id}`}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            <motion.span
              className="ml-3 text-sm font-medium whitespace-nowrap overflow-hidden"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? 'auto' : 0 }}
              transition={{ duration: 0.2 }}
            >
              {item.label}
            </motion.span>
            {activePage === item.path && (
              <motion.div
                className="ml-auto"
                initial={{ opacity: 0 }}
                animate={{ opacity: isExpanded ? 1 : 0 }}
              >
                <ChevronRight className="w-4 h-4" />
              </motion.div>
            )}
          </button>
        ))}
      </nav>

      {/* Divider */}
      <div className="mx-3 border-t border-[#e5e7eb]" />

      {/* Bottom Items */}
      <div className="py-4">
        {bottomItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.path)}
            className={cn(
              "w-full flex items-center px-4 py-3 transition-colors",
              activePage === item.path
                ? "bg-[#2563eb]/10 text-[#2563eb]"
                : "text-[#64748b] hover:bg-[#e5e7eb] hover:text-[#0f172a]"
            )}
            data-testid={`nav-${item.id}`}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            <motion.span
              className="ml-3 text-sm font-medium whitespace-nowrap overflow-hidden"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? 'auto' : 0 }}
              transition={{ duration: 0.2 }}
            >
              {item.label}
            </motion.span>
          </button>
        ))}
      </div>
    </motion.aside>
  );
};
