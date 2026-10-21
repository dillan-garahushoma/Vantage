import { Bell, Menu, Plus, Search } from 'lucide-react';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { roleLabels } from '../../lib/display';
import { initials } from '../../lib/format';
import { allNavItems, navGroupsForRole, navItemsForRole } from '../../lib/nav';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Logo } from '../valora/Logo';
/**
 * The workspace header.
 *
 * It answers two questions on every screen: where am I (the eyebrow and title
 * come from the navigation model, not from the page) and what can I do from here.
 * The quick action follows the same role rules as the navigation, so it never
 * offers an action the API would refuse.
 */
export function TopBar({ onOpenNav, onCreateWorkOrder, onLogComplaint }) {
    const { user } = useAuth();
    const { pathname } = useLocation();
    const navigate = useNavigate();
    const [query, setQuery] = useState('');
    const [focused, setFocused] = useState(false);
    const current = allNavItems.find((item) => item.to === pathname);
    // The eyebrow names the section the screen belongs to, read from the same
    // navigation model the sidebar renders.
    const group = navGroupsForRole(user?.role).find((candidate) => candidate.items.some((item) => item.to === pathname))?.label;
    const allowed = navItemsForRole(user?.role);
    const needle = query.trim().toLowerCase();
    const results = needle
        ? allowed.filter((item) => item.label.toLowerCase().includes(needle))
        : [];
    const quickAction = user?.role === 'hoa_admin' && onCreateWorkOrder
        ? { label: 'Create work order', onClick: onCreateWorkOrder }
        : user?.role === 'resident' && onLogComplaint
            ? { label: 'Log a complaint', onClick: onLogComplaint }
            : null;
    return (<header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1440px] items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <button type="button" onClick={onOpenNav} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-ink transition-colors duration-200 hover:bg-canvas lg:hidden" aria-label="Open navigation">
          <Menu className="h-5 w-5"/>
        </button>

        <div className="lg:hidden">
          <Logo size={24} withWordmark={false}/>
        </div>

        <div className="hidden min-w-0 lg:block">
          <p className="text-[0.66rem] font-semibold tracking-[0.16em] text-ink/35 uppercase">
            {group ?? 'Estate workspace'}
          </p>
          <h1 className="truncate font-heading text-[1.15rem] font-extrabold tracking-[-0.01em] text-ink">
            {current?.label ?? 'Estate workspace'}
          </h1>
        </div>

        <div className="relative ml-auto hidden md:block">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink/30"/>
          <Input value={query} onChange={(event) => setQuery(event.target.value)} onFocus={() => setFocused(true)} onBlur={() => window.setTimeout(() => setFocused(false), 150)} placeholder="Search the estate workspace" aria-label="Search the estate workspace" className="h-10 w-[240px] bg-canvas pl-9"/>
          {focused && results.length > 0 ? (<div className="animate-fade-in absolute top-[46px] right-0 left-0 z-40 rounded-2xl border border-line bg-surface p-1.5 shadow-lift">
              {results.map((item) => (<button key={item.to} type="button" onMouseDown={() => {
                    navigate(item.to);
                    setQuery('');
                }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[0.85rem] font-medium text-ink/75 transition-colors duration-150 hover:bg-canvas hover:text-brand-ink">
                  <item.icon className="h-4 w-4 shrink-0 text-ink/35"/>
                  {item.label}
                </button>))}
            </div>) : null}
        </div>

        <div className="flex items-center gap-2 md:ml-0">
          {quickAction ? (<Button variant="ink" onClick={quickAction.onClick} className="hidden h-10 rounded-full px-5 sm:inline-flex">
              <Plus className="h-3.5 w-3.5"/>
              {quickAction.label}
            </Button>) : null}

          <div className="relative hidden h-10 w-10 items-center justify-center rounded-xl text-ink/50 sm:flex">
            <Bell className="h-[1.1rem] w-[1.1rem]" aria-hidden="true"/>
            <span className="sr-only">Notifications</span>
            <span className="absolute top-2.5 right-2.5 h-2 w-2 rounded-full bg-signal ring-2 ring-surface"/>
          </div>

          <div className="flex items-center gap-2.5 rounded-full border border-line py-1 pr-3 pl-1">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-[0.68rem] font-bold text-white">
              {initials(user?.full_name ?? '')}
            </span>
            <span className="hidden leading-tight sm:block">
              <span className="block max-w-[10rem] truncate text-[0.78rem] font-semibold text-ink">
                {user?.full_name}
              </span>
              <span className="block text-[0.68rem] text-ink/45">
                {user ? (roleLabels[user.role] ?? user.role) : ''}
              </span>
            </span>
          </div>
        </div>
      </div>

      {quickAction ? (<div className="border-t border-line px-4 py-2 sm:hidden">
          <Button variant="ink" onClick={quickAction.onClick} className={cn('h-9 w-full rounded-full text-[0.82rem]')}>
            <Plus className="h-3.5 w-3.5"/>
            {quickAction.label}
          </Button>
        </div>) : null}
    </header>);
}
