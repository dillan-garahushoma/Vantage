import { LogOut } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { roleLabels } from '../../lib/display';
import { initials } from '../../lib/format';
import { navGroupsForRole } from '../../lib/nav';
import { cn } from '../../lib/utils';
import { Logo } from '../valora/Logo';
import { EstateSwitcher } from './EstateSwitcher';

function UserPill() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  return (
    <div className="mt-3 flex items-center gap-2.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-[0.72rem] font-bold text-white">
        {initials(user.full_name)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[0.82rem] font-semibold text-ink">{user.full_name}</span>
        <span className="block truncate text-[0.7rem] text-ink/45">
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
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink/40 transition-colors duration-200 hover:bg-canvas hover:text-ink"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

/** The navigation rail, shared by the desktop sidebar and the mobile sheet. */
export function SidebarNav({ onNavigate }) {
  const { user } = useAuth();
  const groups = navGroupsForRole(user?.role);
  return (
    <nav className="scrollbar-slim flex-1 overflow-y-auto px-3 pb-4" aria-label="Sections">
      {groups.map((group) => (
        <div key={group.label} className="mb-5">
          <p className="px-3 pb-2 text-[0.64rem] font-semibold tracking-[0.16em] text-ink/35 uppercase">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/app'}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[0.86rem] font-medium transition-all duration-200 ease-soft',
                      isActive ? 'bg-canvas text-brand-ink' : 'text-ink/65 hover:bg-canvas/60 hover:text-ink'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={cn(
                          'absolute top-1/2 left-0 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand transition-opacity duration-200',
                          isActive ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      <item.icon
                        className={cn(
                          'h-[1.05rem] w-[1.05rem] shrink-0 transition-colors duration-200',
                          isActive ? 'text-brand' : 'text-ink/40 group-hover:text-ink/60'
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                      {item.accent && !isActive ? (
                        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-soft" />
                      ) : null}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

/** The estate switcher above the rail, on a light header strip. */
export function SidebarHeader() {
  return (
    <div className="px-5 pt-6 pb-4">
      <NavLink to="/app" className="inline-flex">
        <Logo size={28} />
      </NavLink>
      <div className="mt-6">
        <EstateSwitcher />
      </div>
    </div>
  );
}

/** The full rail, fixed to the left edge from `lg` up. */
export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[272px] flex-col border-r border-line bg-surface lg:flex">
      <SidebarHeader />
      <SidebarNav />
      <div className="border-t border-line px-4 py-4">
        <UserPill />
      </div>
    </aside>
  );
}
