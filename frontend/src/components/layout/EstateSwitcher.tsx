import { Check, ChevronsUpDown } from 'lucide-react'
import { useEstate } from '../../context/EstateContext'
import { cn } from '../../lib/utils'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu'

/**
 * Switch the estate that scopes every screen.
 *
 * The list is the server's answer to “which estates may you act in”, and choosing
 * one only changes the `estate_id` this client sends; the server re-authorizes
 * each request, so a client-invented estate is still refused. Role is shown per
 * estate because the same person can be an administrator in one and a resident in
 * another.
 */
export function EstateSwitcher({ className }: { className?: string }) {
  const { estates, active, selectEstate } = useEstate()

  if (estates.length === 0) {
    return (
      <p className="rounded-xl border border-line bg-canvas px-3 py-2.5 text-[0.76rem] text-ink-muted">
        No estate is linked to this account yet.
      </p>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex w-full items-center justify-between gap-2 rounded-xl border border-line bg-surface px-3 py-2.5 text-left transition-all duration-200 hover:border-brand-soft hover:bg-canvas',
          className,
        )}
        aria-label="Switch estate"
      >
        <span className="min-w-0">
          <span className="block truncate text-[0.82rem] font-semibold text-ink">
            {active?.estate_name ?? 'Select an estate'}
          </span>
          <span className="block truncate text-[0.68rem] text-ink/45">
            {active
              ? `${active.suburb}, ${active.city}${active.is_estate_admin ? ' · administrator' : ''}`
              : 'Choose where you are working'}
          </span>
        </span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-ink/35" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-[256px]">
        <DropdownMenuLabel>Your estates</DropdownMenuLabel>
        {estates.map((estate) => (
          <DropdownMenuItem
            key={estate.estate_id}
            onSelect={() => selectEstate(estate.estate_id)}
            className="items-start justify-between gap-3 py-2.5"
          >
            <span className="min-w-0">
              <span className="block truncate text-[0.84rem] font-semibold text-ink">
                {estate.estate_name}
              </span>
              <span className="block truncate text-[0.7rem] text-ink/45">
                {estate.province} · {estate.property_ids.length} unit
                {estate.property_ids.length === 1 ? '' : 's'}
              </span>
            </span>
            {estate.estate_id === active?.estate_id ? (
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
            ) : null}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <p className="px-2.5 py-2 text-[0.68rem] leading-relaxed text-ink/45">
          Switching estate changes the scope of every screen. Access is still resolved on the server
          from your membership.
        </p>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
