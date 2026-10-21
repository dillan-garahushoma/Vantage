import * as SheetPrimitive from '@radix-ui/react-dialog';
import { cva } from 'class-variance-authority';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';
/**
 * A side sheet built on Radix Dialog: the same focus trap and escape handling as
 * `Dialog`, pinned to an edge. Used for the detail drawer, the record drawers and
 * the mobile navigation panel.
 */
export const Sheet = SheetPrimitive.Root;
export const SheetTrigger = SheetPrimitive.Trigger;
export const SheetClose = SheetPrimitive.Close;
export function SheetOverlay({ className, ...rest }) {
    return (<SheetPrimitive.Overlay className={cn('vl-overlay fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm', className)} {...rest}/>);
}
const sheetVariants = cva('fixed z-50 flex flex-col gap-4 bg-surface shadow-lift', {
    variants: {
        side: {
            right: 'vl-panel-right inset-y-0 right-0 h-full w-full border-l border-line sm:max-w-[560px]',
            left: 'vl-panel-left inset-y-0 left-0 h-full w-[86vw] border-r border-line sm:max-w-[320px]',
            top: 'vl-panel-top inset-x-0 top-0 border-b border-line',
            bottom: 'vl-panel-bottom inset-x-0 bottom-0 rounded-t-3xl border-t border-line',
        },
    },
    defaultVariants: { side: 'right' },
});
export function SheetContent({ side = 'right', className, children, showClose = true, ...rest }) {
    return (<SheetPrimitive.Portal>
      <SheetOverlay />
      <SheetPrimitive.Content className={cn(sheetVariants({ side }), className)} {...rest}>
        {showClose ? (<SheetPrimitive.Close aria-label="Close panel" className="absolute top-4 right-4 z-20 flex h-8 w-8 items-center justify-center rounded-full text-ink/45 transition-colors duration-200 hover:bg-canvas hover:text-ink">
            <X className="h-4 w-4"/>
          </SheetPrimitive.Close>) : null}
        {children}
      </SheetPrimitive.Content>
    </SheetPrimitive.Portal>);
}
export function SheetHeader({ className, ...rest }) {
    return <div className={cn('flex flex-col gap-1.5 text-left', className)} {...rest}/>;
}
export function SheetFooter({ className, ...rest }) {
    return (<div className={cn('mt-auto flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...rest}/>);
}
export function SheetTitle({ className, ...rest }) {
    return (<SheetPrimitive.Title className={cn('font-heading text-[1.15rem] font-extrabold tracking-[-0.01em] text-ink', className)} {...rest}/>);
}
export function SheetDescription({ className, ...rest }) {
    return (<SheetPrimitive.Description className={cn('text-[0.82rem] text-ink-muted', className)} {...rest}/>);
}
