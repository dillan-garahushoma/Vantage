import type { ComponentPropsWithRef } from 'react'
import { cn } from '../../lib/utils'

/** A multi-line text control, matched to `Input`. */
export function Textarea({ className, rows = 3, ...rest }: ComponentPropsWithRef<'textarea'>) {
  return (
    <textarea
      rows={rows}
      className={cn(
        'flex w-full resize-y rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm text-ink transition-colors duration-200 placeholder:text-ink-muted/70 focus-visible:border-brand-soft focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...rest}
    />
  )
}
