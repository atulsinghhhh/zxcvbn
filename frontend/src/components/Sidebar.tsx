import { Wind, LayoutDashboard, TrendingUp, Clock, Database, ChevronLeft } from 'lucide-react';
import type { SectionId } from '../hooks/useActiveSection';

interface NavItem {
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
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
  onBack?: () => void;
}

export function Sidebar({ activeSection, onNavigate, onBack }: SidebarProps) {
  return (
    <aside
      className="fixed left-0 top-0 flex h-full w-60 flex-col"
      style={{ borderRight: '1px solid #d4d4dc', background: '#f6f5f9' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-4" style={{ borderBottom: '1px solid #d4d4dc' }}>
        <Wind className="h-5 w-5" style={{ color: '#7132f5' }} />
        <span className="text-base font-bold tracking-tight" style={{ color: '#101114' }}>WindSight</span>
      </div>

      {/* Nav */}
      <nav aria-label="Dashboard sections" className="flex-1 overflow-y-auto px-3 py-4">
        <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-widest" style={{ color: '#9497a9' }}>
          Navigation
        </p>
        <ul className="space-y-0.5">
          {navItems.map(({ icon: Icon, label, section }) => {
            const isActive = activeSection === section;
            return (
              <li key={section}>
                <button
                  type="button"
                  onClick={() => onNavigate(section)}
                  aria-current={isActive ? 'page' : undefined}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors"
                  style={
                    isActive
                      ? {
                          background: '#ffffff',
                          color: '#7132f5',
                          fontWeight: 500,
                          borderLeft: '2px solid #7132f5',
                          boxShadow: 'rgba(0,0,0,0.03) 0px 4px 24px 0px',
                        }
                      : { color: '#686b82', borderLeft: '2px solid transparent' }
                  }
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = '#ffffff';
                      (e.currentTarget as HTMLButtonElement).style.color = '#101114';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                      (e.currentTarget as HTMLButtonElement).style.color = '#686b82';
                    }
                  }}
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
      <div className="px-4 py-4" style={{ borderTop: '1px solid #d4d4dc' }}>
        <p className="mb-2 text-xs font-medium" style={{ color: '#686b82' }}>UK National Wind</p>
        <span
          className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
          style={{ background: '#e4dcf9', color: '#7132f5' }}
        >
          Historical Demo
        </span>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mt-3 flex items-center gap-1.5 text-xs transition-colors"
            style={{ color: '#9497a9', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = '#686b82'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = '#9497a9'; }}
          >
            <ChevronLeft className="h-3 w-3" />
            Back to Home
          </button>
        )}
      </div>
    </aside>
  );
}
