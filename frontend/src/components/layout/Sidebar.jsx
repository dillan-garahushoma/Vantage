import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, LogOut, MoreHorizontal } from 'lucide-react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { roleLabels } from '../../lib/display';
import { initials } from '../../lib/format';
import { navItemsForRole, navGroupsForRole } from '../../lib/nav';
import { cn } from '../../lib/utils';
import { Logo } from '../valora/Logo';
import { EstateSwitcher } from './EstateSwitcher';

const PRIMARY_PATHS = {
  resident: ['/app', '/app/complaints', '/app/announcements', '/app/health'],
  hoa_admin: ['/app', '/app/complaints', '/app/work-orders', '/app/incidents', '/app/health', '/intelligence', '/admin/members'],
  service_provider: ['/provider/work', '/app/work-orders', '/intelligence'],
};

const PRIMARY_LABELS = {
  '/app': { resident: 'Home', hoa_admin: 'Overview' },
  '/app/complaints': { resident: 'My requests', hoa_admin: 'Complaints' },
  '/app/announcements': { resident: 'Notices' },
  '/app/work-orders': { hoa_admin: 'Work orders', service_provider: 'Assigned work' },
  '/app/incidents': { hoa_admin: 'Incidents' },
  '/app/health': { resident: 'Estate health', hoa_admin: 'Estate health' },
  '/intelligence': { resident: 'VALORA Intelligence', hoa_admin: 'VALORA Intelligence', service_provider: 'VALORA Intelligence' },
  '/admin/members': { hoa_admin: 'Residents' },
  '/provider/work': { service_provider: 'My work' },
};

function UserPill() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  return (
    <div className="flex min-w-0 items-center gap-2.5 border-t border-brand/10 px-4 py-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-wash text-[0.72rem] font-bold text-brand-ink">
        {initials(user.full_name)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[0.8rem] font-semibold text-ink">{user.full_name}</span>
        <span className="block truncate text-[0.68rem] text-ink/50">
          {roleLabels[user.role] ?? user.role}
        </span>
      </span>
      <button
        type="button"
        onClick={() => {
          logout();
          navigate('/');
        }}
        aria-label="Sign out"
        title="Sign out"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink/40 transition-colors hover:bg-white hover:text-ink focus-visible:outline-2 focus-visible:outline-brand"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

function NavigationLink({ item, user, onNavigate }) {
  const label = PRIMARY_LABELS[item.to]?.[user?.role] ?? item.label;
  return (
    <NavLink
      to={item.to}
      end={item.to === '/app'}
      onClick={onNavigate}
      className={({ isActive }) => cn(
        'group relative flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-[0.82rem] font-medium transition-colors duration-150',
        isActive
          ? 'bg-brand-wash text-brand-ink'
          : 'text-ink/65 hover:bg-white/70 hover:text-ink',
      )}
    >
      {({ isActive }) => (
        <>
          <item.icon className={cn('h-[1.05rem] w-[1.05rem] shrink-0', isActive ? 'text-brand' : 'text-ink/40 group-hover:text-ink/70')} aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">{label}</span>
          {item.accent && !isActive ? <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand" /> : null}
        </>
      )}
    </NavLink>
  );
}

/** Compact, role-aware rail; secondary tools remain accessible under More. */
export function SidebarNav({ onNavigate }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const groups = navGroupsForRole(user?.role);
  const allowed = navItemsForRole(user?.role);
  const primaryPaths = PRIMARY_PATHS[user?.role] ?? [];
  const primary = primaryPaths
    .map((path) => allowed.find((item) => item.to === path))
    .filter(Boolean);
  const primarySet = new Set(primary.map((item) => item.to));
  const secondaryGroups = groups
    .map((group) => ({ ...group, items: group.items.filter((item) => !primarySet.has(item.to)) }))
    .filter((group) => group.items.length > 0);
  const [moreOpen, setMoreOpen] = useState(() => !primaryPaths.includes(pathname));

  useEffect(() => {
    if (!primaryPaths.includes(pathname)) setMoreOpen(true);
  }, [pathname, user?.role]);

  return (
    <nav className="scrollbar-slim flex-1 overflow-y-auto px-3 pb-4 pt-2" aria-label="Workspace navigation">
      <div className="space-y-1">
        {primary.map((item) => (
          <NavigationLink key={item.to} item={item} user={user} onNavigate={onNavigate} />
        ))}
      </div>

      {secondaryGroups.length > 0 ? (
        <div className="mt-4 border-t border-brand/10 pt-3">
          <button
            type="button"
            aria-expanded={moreOpen}
            onClick={() => setMoreOpen((open) => !open)}
            className="flex min-h-10 w-full items-center gap-3 px-3 py-2 text-left text-[0.8rem] font-medium text-ink/60 transition-colors hover:bg-white/70 hover:text-ink focus-visible:outline-2 focus-visible:outline-brand"
          >
            <MoreHorizontal className="h-[1.05rem] w-[1.05rem] text-ink/45" aria-hidden="true" />
            <span className="flex-1">More tools</span>
            {moreOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          {moreOpen ? (
            <div className="mt-2 space-y-4 border-l border-brand/15 pl-2">
              {secondaryGroups.map((group) => (
                <div key={group.label}>
                  <p className="px-3 pb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-ink/35">
                    {group.label}
                  </p>
                  <div className="space-y-0.5">
                    {group.items.map((item) => (
                      <NavigationLink key={item.to} item={item} user={user} onNavigate={onNavigate} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </nav>
  );
}

/** Brand and the currently selected estate live together like a workspace switcher. */
export function SidebarHeader() {
  return (
    <div className="px-4 pb-4 pt-5">
      <NavLink to="/app" className="inline-flex rounded-sm px-1 py-1" aria-label="VALORA workspace home">
        <Logo size={42} />
      </NavLink>
      <div className="mt-5">
        <EstateSwitcher />
      </div>
    </div>
  );
}

/** Desktop rail. The mobile sheet reuses the same header and navigation. */
export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[232px] flex-col border-r border-brand/10 bg-[#F8F6FD] lg:flex">
      <SidebarHeader />
      <SidebarNav />
      <UserPill />
    </aside>
  );
}
