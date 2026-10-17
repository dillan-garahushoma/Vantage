import { Menu, MoreHorizontal, Plus } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { initials } from '../../lib/format'
import { mobilePrimaryPaths, navItemsForRole } from '../../lib/nav'
import type { NavItem } from '../../lib/nav'
import { cn } from '../../lib/utils'
import { Sheet, SheetContent, SheetTitle } from '../ui/sheet'
import { SidebarHeader, SidebarNav } from './Sidebar'

/**
 * The phone navigation.
 *
 * A bottom bar carries the four destinations a member opens most (the list is
 * filtered by role, so a provider never sees a dead link) and everything else
 * lives behind “More”, which opens the same rail as the desktop sidebar —
 * including the estate switcher, so scope is changeable on a phone too.
 */
export function MobileNav({
  onOpenNav,
  onCreate,
  createLabel,
}: {
  onOpenNav: () => void
  onCreate?: () => void
  createLabel?: string
}) {
  const { pathname } = useLocation()
  const { user } = useAuth()
  const allowed = navItemsForRole(user?.role)
  const primary = mobilePrimaryPaths
    .map((path) => allowed.find((item) => item.to === path))
    .filter((item): item is NavItem => Boolean(item))

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
      aria-label="Sections"
    >
      <ul className="mx-auto flex max-w-md items-stretch justify-between px-2">
        {primary.slice(0, 3).map((item) => {
          const isActive = pathname === item.to
          return (
            <li key={item.to} className="flex-1">
              <Link
                to={item.to}
                className={cn(
                  'flex w-full flex-col items-center gap-1 rounded-xl px-1 py-2.5 text-[0.62rem] font-semibold transition-colors duration-200',
                  isActive ? 'text-brand-ink' : 'text-ink/45',
                )}
              >
                <item.icon className="h-[1.15rem] w-[1.15rem]" />
                <span className="truncate">{item.label.split(' ')[0]}</span>
              </Link>
            </li>
          )
        })}

        <li className="flex-1">
          <button
            type="button"
            onClick={onCreate}
            disabled={!onCreate}
            className={cn(
              'flex w-full flex-col items-center gap-1 rounded-xl px-1 py-2.5 text-[0.62rem] font-semibold transition-colors duration-200',
              onCreate ? 'text-ink/45 hover:text-ink' : 'text-ink/20',
            )}
          >
            <Plus className="h-[1.15rem] w-[1.15rem]" />
            <span className="truncate">{createLabel ?? 'Create'}</span>
          </button>
        </li>

        <li className="flex-1">
          <button
            type="button"
            onClick={onOpenNav}
            className="flex w-full flex-col items-center gap-1 rounded-xl px-1 py-2.5 text-[0.62rem] font-semibold text-ink/45 transition-colors duration-200 hover:text-ink"
          >
            <MoreHorizontal className="h-[1.15rem] w-[1.15rem]" />
            More
          </button>
        </li>
      </ul>
    </nav>
  )
}

/** The sheet behind “More”: the full rail, with the estate switcher on top. */
export function MobileNavSheet({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { user } = useAuth()

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="scrollbar-slim gap-0 overflow-y-auto p-0" showClose={false}>
        <SheetTitle className="sr-only">Estate navigation</SheetTitle>
        <SidebarHeader />
        <div className="flex items-center gap-2 border-y border-line px-5 py-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-[0.68rem] font-bold text-white">
            {initials(user?.full_name ?? '')}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-[0.8rem] font-semibold text-ink">
              {user?.full_name ?? 'Signed in'}
            </span>
            <span className="block truncate text-[0.68rem] text-ink/45">{user?.email}</span>
          </span>
        </div>
        <SidebarNav onNavigate={() => onOpenChange(false)} />
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="mx-5 mb-5 flex items-center justify-center gap-2 rounded-xl border border-line px-4 py-2.5 text-[0.82rem] font-semibold text-ink/70"
        >
          <Menu className="h-4 w-4" />
          Close navigation
        </button>
      </SheetContent>
    </Sheet>
  )
}
