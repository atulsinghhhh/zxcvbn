import { Wind, LayoutDashboard, TrendingUp, Clock, Database } from 'lucide-react';
import type { SectionId } from '../hooks/useActiveSection';

interface NavItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  section: SectionId;
}

const navItems: NavItem[] = [
  { icon: LayoutDashboard, label: 'Overview', section: 'overview' },
  { icon: TrendingUp, label: 'Forecast Analysis', section: 'forecast' },
  { icon: Clock, label: 'Historical Accuracy', section: 'accuracy' },
  { icon: Database, label: 'Data Sources', section: 'data-sources' },
];

interface SidebarProps {
  activeSection: SectionId;
  onNavigate: (section: SectionId) => void;
}

export function Sidebar({ activeSection, onNavigate }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 flex h-full w-60 flex-col border-r border-slate-700 bg-slate-900">
      {/* Logo */}
      <div className="flex items-center gap-2 border-b border-slate-700 px-5 py-4">
        <Wind className="h-6 w-6 text-emerald-400" />
        <span className="text-base font-bold tracking-tight text-white">WindSight</span>
      </div>

      {/* Nav */}
      <nav aria-label="Dashboard sections" className="flex-1 overflow-y-auto px-3 py-4">
        <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
          Navigation
        </p>
        <ul className="space-y-1">
          {navItems.map(({ icon: Icon, label, section }) => {
            const isActive = activeSection === section;
            return (
              <li key={section}>
                <button
                  type="button"
                  onClick={() => onNavigate(section)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                    isActive
                      ? 'bg-emerald-900/40 font-medium text-emerald-300'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-700 px-4 py-4">
        <p className="mb-2 text-xs font-semibold text-slate-400">UK National Wind</p>
        <span className="inline-flex items-center rounded-full bg-amber-900/50 px-2.5 py-1 text-xs font-medium text-amber-300">
          Historical Analytics Demo
        </span>
      </div>
    </aside>
  );
}
