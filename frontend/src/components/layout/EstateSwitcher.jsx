import { Check, ChevronsUpDown } from 'lucide-react';
import { useEstate } from '../../context/EstateContext';
import { cn } from '../../lib/utils';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/dropdown-menu';

/**
 * Switch the estate that scopes every screen. This is account-authorised context
 * from /auth/estates; the browser never invents membership or grants access.
 */
export function EstateSwitcher({ className }) {
  const { estates, active, selectEstate } = useEstate();
  if (estates.length === 0) {
    return (
      <div className="border border-brand/10 bg-white/70 px-3 py-3">
        <p className="text-[0.78rem] font-semibold text-ink">No estate linked</p>
        <p className="mt-1 text-[0.68rem] leading-relaxed text-ink/50">Your workspace appears when an estate grants access.</p>
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex w-full items-center gap-2.5 border border-brand/10 bg-white/75 p-2 text-left transition-colors hover:border-brand/30 hover:bg-white focus-visible:outline-2 focus-visible:outline-brand',
          className,
        )}
        aria-label="Switch estate"
      >
        <img src="/estate-hero.jpg" alt="" aria-hidden="true" className="h-10 w-11 shrink-0 object-cover" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[0.75rem] font-semibold leading-snug text-ink">
            {active?.estate_name ?? 'Select an estate'}
          </span>
          <span className="mt-0.5 block truncate text-[0.64rem] leading-snug text-ink/50">
            {active ? [active.suburb, active.city].filter(Boolean).join(', ') : 'Choose a workspace'}
          </span>
        </span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-ink/40" aria-hidden="true" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-[260px]">
        <DropdownMenuLabel>Your estates</DropdownMenuLabel>
        {estates.map((estate) => (
          <DropdownMenuItem
            key={estate.estate_id}
            onSelect={() => selectEstate(estate.estate_id)}
            className="items-start justify-between gap-3 py-2.5"
          >
            <span className="min-w-0">
              <span className="block truncate text-[0.82rem] font-semibold text-ink">{estate.estate_name}</span>
              <span className="block truncate text-[0.68rem] text-ink/45">
                {[estate.suburb, estate.city, estate.province].filter(Boolean).join(', ')} · {estate.property_ids.length} unit{estate.property_ids.length === 1 ? '' : 's'}
              </span>
            </span>
            {estate.estate_id === active?.estate_id ? <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" aria-label="Selected" /> : null}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <p className="px-2.5 py-2 text-[0.68rem] leading-relaxed text-ink/45">
          Switching estate changes the records shown in this workspace. The server still checks your membership.
        </p>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
