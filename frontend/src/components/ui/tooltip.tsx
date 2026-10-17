import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import type { ComponentPropsWithRef } from 'react'
import { cn } from '../../lib/utils'

/**
 * Radix tooltip.
 *
 * `TooltipProvider` is mounted once inside `App`, so every tooltip in the tree
 * shares one delay: a hovered icon explains itself quickly, and moving across a
 * row of them does not re-wait.
 */
export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  sideOffset = 6,
  ...rest
}: ComponentPropsWithRef<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'vl-pop z-50 max-w-[18rem] rounded-xl bg-ink px-3 py-1.5 text-[0.75rem] leading-snug font-medium text-white shadow-lift',
          className,
        )}
        {...rest}
      />
    </TooltipPrimitive.Portal>
  )
}
