import type { ReactNode } from 'react'
import { statusTone, statusToneClasses } from '../../lib/display'
import { cn } from '../../lib/utils'

export interface StatusChipProps {
  /** A status word from the backend or the screen; tone is resolved from it. */
  status: string | null | undefined
  size?: 'sm' | 'md'
  className?: string
  /** Overrides the words when the tone is right but the label needs different copy. */
  children?: ReactNode
}

/**
 * A filled status pill.
 *
 * The dot is the colour cue and the words carry the state, so the chip still
 * reads correctly in greyscale or to somebody who cannot separate rose from
 * amber. `statusTone` accepts `in_progress` and `In progress` alike.
 */
export function StatusChip({ status, size = 'md', className, children }: StatusChipProps) {
  const tone = statusTone(status)
  const label = children ?? (status ? String(status) : '—')

  return (
    <span
      className={cn(
        'inline-flex w-fit items-center gap-1.5 rounded-full font-semibold leading-none whitespace-nowrap',
        size === 'sm' ? 'px-2.5 py-1.5 text-[0.66rem]' : 'px-3 py-1.5 text-[0.72rem]',
        statusToneClasses[tone].pill,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', statusToneClasses[tone].dot)} />
      {label}
    </span>
  )
}
