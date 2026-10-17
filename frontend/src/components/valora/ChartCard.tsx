import type { ReactNode } from 'react'
import { Surface } from './Surface'
import { cn } from '../../lib/utils'

export interface ChartCardProps {
  title: string
  description?: string
  action?: ReactNode
  children: ReactNode
  footer?: ReactNode
  className?: string
  height?: number | string
}

export function ChartCard({
  title,
  description,
  action,
  children,
  footer,
  className,
  height = 260,
}: ChartCardProps) {
  return (
    <Surface className={cn('flex flex-col', className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-heading text-[1rem] font-bold tracking-[-0.01em] text-ink">{title}</h3>
          {description && (
            <p className="mt-1 text-[0.82rem] leading-relaxed text-ink-muted">{description}</p>
          )}
        </div>
        {action}
      </div>
      <div className="mt-5" style={{ height }}>
        {children}
      </div>
      {footer && (
        <div className="mt-4 border-t border-line pt-4 text-[0.78rem] text-ink-muted">{footer}</div>
      )}
    </Surface>
  )
}

export default ChartCard
