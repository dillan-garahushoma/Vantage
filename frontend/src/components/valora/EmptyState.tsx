import { Inbox } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

export interface EmptyStateProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

/**
 * The state a screen is in before it has anything to show.
 *
 * It always says what would appear here and, when there is one, offers the
 * action that would create it — an empty table with no next step is a dead end.
 */
export function EmptyState({ title, description, action, icon, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center px-6 py-12 text-center', className)}>
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-canvas text-brand">
        {icon ?? <Inbox className="h-5 w-5" />}
      </span>
      <p className="mt-4 font-heading text-[0.98rem] font-bold text-ink">{title}</p>
      {description ? (
        <p className="mt-1.5 max-w-md text-[0.84rem] leading-relaxed text-ink/55">{description}</p>
      ) : null}
      {action ? <div className="mt-4 flex flex-wrap justify-center gap-2">{action}</div> : null}
    </div>
  )
}
