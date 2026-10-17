import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import type { ComponentPropsWithRef } from 'react'
import { cn } from '../../lib/utils'

/** Radix dropdown, styled as a soft white surface with a lifted shadow. */

export const DropdownMenu = DropdownMenuPrimitive.Root
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger
export const DropdownMenuGroup = DropdownMenuPrimitive.Group
export const DropdownMenuPortal = DropdownMenuPrimitive.Portal

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  ...rest
}: ComponentPropsWithRef<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'vl-pop z-50 min-w-[10rem] overflow-hidden rounded-2xl border border-line bg-surface p-1.5 text-ink shadow-lift',
          className,
        )}
        {...rest}
      />
    </DropdownMenuPrimitive.Portal>
  )
}

export function DropdownMenuItem({
  className,
  ...rest
}: ComponentPropsWithRef<typeof DropdownMenuPrimitive.Item>) {
  return (
    <DropdownMenuPrimitive.Item
      className={cn(
        'relative flex cursor-pointer select-none items-center gap-2.5 rounded-xl px-2.5 py-2 text-[0.85rem] outline-none transition-colors duration-150 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-canvas data-[highlighted]:text-brand-ink',
        className,
      )}
      {...rest}
    />
  )
}

export function DropdownMenuLabel({
  className,
  ...rest
}: ComponentPropsWithRef<typeof DropdownMenuPrimitive.Label>) {
  return (
    <DropdownMenuPrimitive.Label
      className={cn(
        'px-2.5 py-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/40 uppercase',
        className,
      )}
      {...rest}
    />
  )
}

export function DropdownMenuSeparator({
  className,
  ...rest
}: ComponentPropsWithRef<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator
      className={cn('-mx-1.5 my-1 h-px bg-line', className)}
      {...rest}
    />
  )
}
