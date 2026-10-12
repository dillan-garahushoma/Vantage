import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useEstate } from '../context/EstateContext'
import { roleLabels } from '../lib/display'
import type { UserRole } from '../lib/types'
import { initials } from '../lib/format'
import { Wordmark } from './Brand'
import {
  IconGrid,
  IconHome,
  IconLogout,
  IconMegaphone,
  IconMenu,
  IconPin,
  IconReport,
  IconShield,
  IconUsers,
  IconWrench,
} from './Icons'
import { Button, Chip, cx } from './ui'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  roles?: UserRole[]
  hint?: string
}

const NAV: NavItem[] = [
  { to: '/app', label: 'Overview', icon: <IconGrid size={17} />, hint: 'Estate health at a glance' },
  {
    to: '/app/complaints',
    label: 'Complaints',
    icon: <IconReport size={17} />,
    roles: ['resident', 'hoa_admin'],
  },
  {
    to: '/app/work-orders',
    label: 'Work orders',
    icon: <IconWrench size={17} />,
    roles: ['hoa_admin', 'service_provider'],
  },
  { to: '/app/announcements', label: 'Announcements', icon: <IconMegaphone size={17} /> },
  {
    to: '/app/properties',
    label: 'Properties',
    icon: <IconHome size={17} />,
    roles: ['resident', 'hoa_admin', 'investor', 'estate_agent'],
  },
  {
    to: '/app/providers',
    label: 'Providers',
    icon: <IconUsers size={17} />,
    roles: ['hoa_admin'],
  },
  {
    to: '/provider/work',
    label: 'My work',
    icon: <IconWrench size={17} />,
    roles: ['service_provider'],
    hint: 'Jobs assigned to your provider profile',
  },
  {
    to: '/admin/setup',
    label: 'Estate setup',
    icon: <IconShield size={17} />,
    roles: ['hoa_admin'],
    hint: 'Description, units, photographs, publishing',
  },
  {
    to: '/admin/members',
    label: 'Members',
    icon: <IconUsers size={17} />,
    roles: ['hoa_admin'],
    hint: 'Who may act inside this estate',
  },
]

function EstateSelector() {
  const { estates, active, selectEstate } = useEstate()
  if (estates.length === 0) return null

  // `min-w-0` on both the wrapper and the control: a `<select>`'s min-content
  // width is its longest option, which is what used to push the header wider than
  // a 390px viewport. Shrinking is safe — the selected name is `truncate`d.
  return (
    <label className="flex min-w-0 items-center gap-2">
      <span className="hidden text-[11px] tracking-wider text-ink-muted uppercase sm:inline">
        Estate
      </span>
      <select
        value={active?.estate_id ?? ''}
        onChange={(event) => selectEstate(Number(event.target.value))}
        className="w-full min-w-0 max-w-[8.5rem] truncate rounded-xs border border-ink/20 bg-surface px-2.5 py-1.5 text-[13px] focus:border-accent focus:outline-none sm:max-w-[15rem]"
      >
        {estates.map((estate) => (
          <option key={estate.estate_id} value={estate.estate_id}>
            {estate.estate_name}
          </option>
        ))}
      </select>
    </label>
  )
}

export function AppShell() {
  const { user, logout } = useAuth()
  const { active } = useEstate()
  const navigate = useNavigate()
  const [railOpen, setRailOpen] = useState(false)

  if (!user) return null

  const items = NAV.filter((item) => !item.roles || item.roles.includes(user.role))

  const rail = (
    <nav className="flex flex-col gap-0.5" aria-label="Sections">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/app'}
          onClick={() => setRailOpen(false)}
          className={({ isActive }) =>
            cx(
              'flex items-center gap-2.5 rounded-xs border px-3 py-2 text-[13.5px] transition-colors duration-150',
              isActive
                ? 'border-ink/20 bg-surface font-medium text-ink'
                : 'border-transparent text-ink-soft hover:border-ink/12 hover:bg-surface/60',
            )
          }
        >
          {({ isActive }) => (
            <>
              <span className={isActive ? 'text-accent' : 'text-ink-muted'}>{item.icon}</span>
              {item.label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-ink/15 bg-surface">
        <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-2.5 sm:px-6">
          <button
            type="button"
            className="rounded-xs border border-ink/20 p-1.5 lg:hidden"
            aria-label="Toggle navigation"
            aria-expanded={railOpen}
            onClick={() => setRailOpen((open) => !open)}
          >
            <IconMenu size={18} />
          </button>

          <Wordmark to="/app" compact />

          <div className="ml-auto flex min-w-0 items-center gap-2 sm:gap-3">
            <EstateSelector />
            <div className="hidden items-center gap-2 sm:flex">
              <span className="flex h-7 w-7 items-center justify-center rounded-xs bg-ink text-[11px] font-semibold text-paper">
                {initials(user.full_name)}
              </span>
              <span className="leading-tight">
                <span className="block max-w-[12rem] truncate text-[13px] font-medium">
                  {user.full_name}
                </span>
                <span className="block text-[11px] text-ink-muted">
                  {roleLabels[user.role] ?? user.role}
                </span>
              </span>
            </div>
            <Button
              variant="ghost"
              onClick={() => {
                logout()
                navigate('/')
              }}
              aria-label="Sign out"
            >
              <IconLogout size={16} />
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1400px] gap-6 px-4 py-5 sm:px-6">
        <aside className="hidden w-56 shrink-0 lg:block">
          <div className="sticky top-[4.5rem]">
            {rail}
            {active ? (
              <div className="mt-5 hairline rounded-xs bg-surface p-3">
                <p className="text-[11px] tracking-wider text-ink-muted uppercase">Scope</p>
                <p className="mt-1 text-[13px] font-medium">{active.estate_name}</p>
                <p className="num mt-0.5 text-[11px] text-ink-muted">
                  {active.suburb}, {active.city}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {active.is_estate_admin ? <Chip tone="progress">HOA admin</Chip> : null}
                  {active.is_estate_provider ? <Chip tone="progress">Provider</Chip> : null}
                  {!active.is_estate_admin && !active.is_estate_provider ? (
                    <Chip>{active.membership_roles[0] ?? 'member'}</Chip>
                  ) : null}
                </div>
                {active.is_estate_admin ? (
                  <Link
                    to={`/estates/${active.estate_id}`}
                    className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-accent-ink hover:underline"
                  >
                    <IconPin size={14} />
                    View the public profile
                  </Link>
                ) : null}
              </div>
            ) : null}

            <Link
              to="/estates"
              className="mt-4 inline-flex items-center gap-1.5 text-[12.5px] text-ink-muted hover:text-accent-ink"
            >
              <IconGrid size={15} />
              Find a complex
            </Link>
          </div>
        </aside>

        {railOpen ? (
          <div className="fixed inset-0 z-20 bg-ink/20 lg:hidden" onClick={() => setRailOpen(false)}>
            <div
              className="absolute top-[3.6rem] left-0 w-64 border-r border-b border-ink/15 bg-paper p-3"
              onClick={(event) => event.stopPropagation()}
            >
              {rail}
            </div>
          </div>
        ) : null}

        <main className="min-w-0 flex-1 pb-16">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
