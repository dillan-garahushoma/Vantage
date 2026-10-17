import * as TabsPrimitive from '@radix-ui/react-tabs'
import type { ComponentPropsWithRef } from 'react'
import { cn } from '../../lib/utils'

/**
 * Radix tabs, styled as a lavender track with a white raised thumb.
 *
 * The active tab is a real `aria-selected` tab, so a screen reader announces the
 * change rather than relying on the visual weight shift.
 */
export const Tabs = TabsPrimitive.Root

export function TabsList({ className, ...rest }: ComponentPropsWithRef<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn(
        'inline-flex items-center gap-1 rounded-2xl bg-canvas p-1 text-ink-muted',
        className,
      )}
      {...rest}
    />
  )
}

export function TabsTrigger({
  className,
  ...rest
}: ComponentPropsWithRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        'inline-flex items-center justify-center gap-1.5 rounded-xl px-3.5 py-1.5 text-[0.82rem] font-semibold whitespace-nowrap transition-all duration-200 data-[state=active]:bg-surface data-[state=active]:text-brand-ink data-[state=active]:shadow-soft disabled:pointer-events-none disabled:opacity-50',
        className,
      )}
      {...rest}
    />
  )
}

export function TabsContent({
  className,
  ...rest
}: ComponentPropsWithRef<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn('focus-visible:outline-none', className)} {...rest} />
}
