import type { ComponentPropsWithRef, ReactNode } from 'react'
import { cn } from '../../lib/utils'

/** Surface primitives: white card, lavender hairline, soft shadow, generous radius. */

export function Card({ className, ...rest }: ComponentPropsWithRef<'div'>) {
  return <div className={cn('rounded-2xl border border-line bg-surface shadow-soft', className)} {...rest} />
}

export function CardHeader({ className, ...rest }: ComponentPropsWithRef<'div'>) {
  return <div className={cn('flex flex-col gap-1.5 p-5', className)} {...rest} />
}

export function CardTitle({ className, children, ...rest }: ComponentPropsWithRef<'div'>) {
  return (
    <div
      className={cn('font-heading text-[1.05rem] leading-none font-bold tracking-[-0.01em] text-ink', className)}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardDescription({ className, ...rest }: ComponentPropsWithRef<'div'>) {
  return <div className={cn('text-[0.85rem] text-ink-muted', className)} {...rest} />
}

export function CardContent({ className, ...rest }: ComponentPropsWithRef<'div'>) {
  return <div className={cn('p-5 pt-0', className)} {...rest} />
}

export function CardFooter({ className, children, ...rest }: ComponentPropsWithRef<'div'>) {
  return (
    <div className={cn('flex items-center gap-2 p-5 pt-0', className)} {...rest}>
      {children}
    </div>
  )
}

export type { ReactNode }
