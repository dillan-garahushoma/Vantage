import { LogOut } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEstate } from '../../context/EstateContext';
import { roleLabels } from '../../lib/display';
import { initials } from '../../lib/format';
import { navGroupsForRole } from '../../lib/nav';
import { cn } from '../../lib/utils';
import { Sparkline } from '../valora/Sparkline';
import { Logo } from '../valora/Logo';
import { EstateSwitcher } from './EstateSwitcher';
/**
 * The Living Score in the shell's footer.
 *
 * It renders the estate's *stored* score: the published figure, the difference
 * between the two most recent snapshots, and a written status. There is no
 * formula here — the pillars, the weights and the rolling window live in the
 * backend engine, and an estate that has never been scored says so instead of
 * showing a zero.
 */
function LivingScoreWidget() {
    const { livingScore } = useEstate();
    const navigate = useNavigate();
    const trend = livingScore.trend;
    const trendLabel = trend === null ? null : `${trend > 0 ? '+' : ''}${Number.isInteger(trend) ? trend : trend.toFixed(1)}`;
    return (<button type="button" onClick={() => navigate('/app/health')} className="w-full rounded-xl border border-line bg-canvas px-3.5 py-3 text-left transition-colors duration-200 hover:border-brand-soft">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[0.66rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">
          Living Score
        </p>
        {trendLabel ? (<span className={cn('num rounded-full bg-surface px-2 py-0.5 text-[0.66rem] font-bold', trend !== null && trend < 0 ? 'text-signal-ink' : 'text-mint-ink')}>
            {trendLabel}
          </span>) : null}
      </div>

      {livingScore.loading ? (<p className="mt-2 text-[0.72rem] text-ink/40">Reading the stored score…</p>) : livingScore.value === null ? (<>
          <p className="num mt-1.5 font-heading text-[1.3rem] leading-none font-extrabold text-ink-muted">
            ——
            <span className="text-[0.85rem] font-bold text-ink/25">/100</span>
          </p>
          <p className="mt-1 text-[0.7rem] text-ink/45">{livingScore.label}</p>
        </>) : (<>
          <p className="num mt-1.5 font-heading text-[1.5rem] leading-none font-extrabold text-ink">
            {livingScore.value.toLocaleString('en-ZA', { maximumFractionDigits: 1 })}
            <span className="text-[0.85rem] font-bold text-ink/30">/100</span>
          </p>
          <p className="mt-1 text-[0.7rem] text-ink/45">{livingScore.label}</p>
          {livingScore.history.length > 1 ? (<div className="mt-2">
              <Sparkline data={livingScore.history} tone={trend !== null && trend < 0 ? 'critical' : 'brand'} height={22} label="Stored Living Score, oldest first"/>
            </div>) : null}
        </>)}
    </button>);
}
function UserPill() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    if (!user)
        return null;
    return (<div className="mt-3 flex items-center gap-2.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-[0.72rem] font-bold text-white">
        {initials(user.full_name)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[0.82rem] font-semibold text-ink">{user.full_name}</span>
        <span className="block truncate text-[0.7rem] text-ink/45">
          {roleLabels[user.role] ?? user.role}
        </span>
      </span>
      <button type="button" onClick={() => {
            logout();
            navigate('/');
        }} aria-label="Sign out" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink/40 transition-colors duration-200 hover:bg-canvas hover:text-ink">
        <LogOut className="h-4 w-4"/>
      </button>
    </div>);
}
/** The navigation rail, shared by the desktop sidebar and the mobile sheet. */
export function SidebarNav({ onNavigate }) {
    const { user } = useAuth();
    const groups = navGroupsForRole(user?.role);
    return (<nav className="scrollbar-slim flex-1 overflow-y-auto px-3 pb-4" aria-label="Sections">
      {groups.map((group) => (<div key={group.label} className="mb-5">
          <p className="px-3 pb-2 text-[0.64rem] font-semibold tracking-[0.16em] text-ink/35 uppercase">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (<li key={item.to}>
                <NavLink to={item.to} end={item.to === '/app'} onClick={onNavigate} className={({ isActive }) => cn('group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[0.86rem] font-medium transition-all duration-200 ease-soft', isActive
                    ? 'bg-canvas text-brand-ink'
                    : 'text-ink/65 hover:bg-canvas/60 hover:text-ink')}>
                  {({ isActive }) => (<>
                      <span className={cn('absolute top-1/2 left-0 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand transition-opacity duration-200', isActive ? 'opacity-100' : 'opacity-0')}/>
                      <item.icon className={cn('h-[1.05rem] w-[1.05rem] shrink-0 transition-colors duration-200', isActive ? 'text-brand' : 'text-ink/40 group-hover:text-ink/60')}/>
                      <span className="truncate">{item.label}</span>
                      {item.accent && !isActive ? (<span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-soft"/>) : null}
                    </>)}
                </NavLink>
              </li>))}
          </ul>
        </div>))}
    </nav>);
}
/** The estate switcher above the rail, on a light header strip. */
export function SidebarHeader() {
    return (<div className="px-5 pt-6 pb-4">
      <NavLink to="/app" className="inline-flex">
        <Logo size={28}/>
      </NavLink>
      <div className="mt-6">
        <EstateSwitcher />
      </div>
    </div>);
}
/** The full rail, fixed to the left edge from `lg` up. */
export function Sidebar() {
    return (<aside className="fixed inset-y-0 left-0 z-40 hidden w-[272px] flex-col border-r border-line bg-surface lg:flex">
      <SidebarHeader />
      <SidebarNav />
      <div className="border-t border-line px-4 py-4">
        <LivingScoreWidget />
        <UserPill />
      </div>
    </aside>);
}
