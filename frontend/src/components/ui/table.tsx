import type { ComponentPropsWithRef } from 'react'
import { cn } from '../../lib/utils'

/**
 * Table primitives.
 *
 * Screens with a lot of rows use `DataTable`, which owns search, filtering and
 * the mobile card fallback; these are the parts, for a table that is small and
 * static enough not to need any of that.
 */

export function Table({ className, ...rest }: ComponentPropsWithRef<'table'>) {
  return (
    <div className="scrollbar-slim w-full overflow-x-auto">
      <table className={cn('w-full border-separate border-spacing-0 text-left', className)} {...rest} />
    </div>
  )
}

export function TableHeader({ className, ...rest }: ComponentPropsWithRef<'thead'>) {
  return <thead className={cn('', className)} {...rest} />
}

export function TableBody({ className, ...rest }: ComponentPropsWithRef<'tbody'>) {
  return <tbody className={cn('', className)} {...rest} />
}

export function TableRow({ className, ...rest }: ComponentPropsWithRef<'tr'>) {
  return <tr className={cn('group transition-colors duration-150', className)} {...rest} />
}

export function TableHead({ className, ...rest }: ComponentPropsWithRef<'th'>) {
  return (
    <th
      scope="col"
      className={cn(
        'border-b border-line px-4 py-3 text-[0.7rem] font-semibold tracking-[0.1em] text-ink/45 uppercase',
        className,
      )}
      {...rest}
    />
  )
}

export function TableCell({ className, ...rest }: ComponentPropsWithRef<'td'>) {
  return (
    <td className={cn('border-b border-line-soft px-4 py-3.5 align-middle text-[0.85rem] text-ink/75', className)} {...rest} />
  )
}

export function TableCaption({ className, ...rest }: ComponentPropsWithRef<'caption'>) {
  return <caption className={cn('mt-4 text-[0.75rem] text-ink/40', className)} {...rest} />
}
