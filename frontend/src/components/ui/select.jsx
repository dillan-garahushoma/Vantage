import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
/**
 * Radix select, styled to match the workspace.
 *
 * Used where a native `<select>` cannot carry a label above each option (filters
 * with a “show all” state, provider and priority pickers in dialogs). The trigger
 * is the same height and radius as `Input`, so the two sit on one row cleanly.
 */
export const Select = SelectPrimitive.Root;
export const SelectGroup = SelectPrimitive.Group;
export const SelectValue = SelectPrimitive.Value;
export function SelectTrigger({ className, children, ...rest }) {
    return (<SelectPrimitive.Trigger className={cn('flex h-10 w-full items-center justify-between gap-2 rounded-xl border border-line bg-surface px-3 text-left text-sm text-ink transition-colors duration-200 hover:border-brand-soft focus-visible:border-brand-soft focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50', className)} {...rest}>
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="h-4 w-4 shrink-0 text-ink-muted"/>
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>);
}
export function SelectContent({ className, children, position = 'popper', ...rest }) {
    return (<SelectPrimitive.Portal>
      <SelectPrimitive.Content position={position} sideOffset={6} className={cn('vl-pop z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-2xl border border-line bg-surface p-1.5 text-ink shadow-lift', className)} {...rest}>
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>);
}
export function SelectItem({ className, children, ...rest }) {
    return (<SelectPrimitive.Item className={cn('relative flex cursor-pointer select-none items-center justify-between gap-3 rounded-xl px-2.5 py-2 text-[0.85rem] outline-none data-[highlighted]:bg-canvas data-[highlighted]:text-brand-ink', className)} {...rest}>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator>
        <Check className="h-3.5 w-3.5 text-brand"/>
      </SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>);
}
export function SelectLabel({ className, children, ...rest }) {
    return (<SelectPrimitive.Label className={cn('px-2.5 py-1.5 text-[0.66rem] font-semibold tracking-[0.14em] text-ink/40 uppercase', className)} {...rest}>
      {children}
    </SelectPrimitive.Label>);
}
