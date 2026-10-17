import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './sheet'

export interface DrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  subtitle?: ReactNode
  /** A chip beside the title — usually the record's status or confidence. */
  badge?: ReactNode
  children: ReactNode
  /** Sticky action row, pinned to the bottom of the panel. */
  footer?: ReactNode
  /** Tailwind width utilities for the desktop panel. */
  width?: string
  side?: 'right' | 'left'
  className?: string
}

/**
 * The record panel every operational screen opens from a row.
 *
 * One component so a complaint, a work order and an Intelligence finding all
 * behave identically: `aria-modal` focus trap, escape to close, a sticky header
 * that keeps the record's identity visible while the body scrolls, and an
 * optional sticky footer for its actions.
 */
export function Drawer({
  open,
  onOpenChange,
  title,
  subtitle,
  badge,
  children,
  footer,
  width = 'sm:max-w-[560px]',
  side = 'right',
  className,
}: DrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side={side}
        className={cn('scrollbar-slim gap-0 overflow-y-auto p-0', width, className)}
      >
        <SheetHeader className="sticky top-0 z-10 border-b border-line bg-surface/95 px-6 py-5 backdrop-blur">
          <div className="flex items-start justify-between gap-4 pr-8">
            <div className="min-w-0">
              <SheetTitle>{title}</SheetTitle>
              {subtitle ? (
                <SheetDescription className="mt-1 truncate">{subtitle}</SheetDescription>
              ) : null}
            </div>
            {badge ? <div className="flex shrink-0 items-center gap-2">{badge}</div> : null}
          </div>
        </SheetHeader>

        <div className="px-6 py-5">{children}</div>

        {footer ? (
          <div className="sticky bottom-0 border-t border-line bg-surface/95 px-6 py-4 backdrop-blur">
            {footer}
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
