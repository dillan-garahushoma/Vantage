import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';
/**
 * Radix dialog, dressed as a soft, centred panel.
 *
 * The open/close transition lives in `index.css` as `.vl-overlay` / `.vl-dialog`
 * (keyed on `data-state`), so every dialog in the product animates the same way
 * and nothing depends on an animation plugin.
 */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export function DialogOverlay({ className, ...rest }) {
    return (<DialogPrimitive.Overlay className={cn('vl-overlay fixed inset-0 z-50 bg-ink/45 backdrop-blur-sm', className)} {...rest}/>);
}
export function DialogContent({ className, children, showClose = true, ...rest }) {
    return (<DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content className={cn('vl-dialog fixed top-1/2 left-1/2 z-50 grid w-[94vw] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 rounded-3xl border border-line bg-surface shadow-lift', className)} {...rest}>
        {children}
        {showClose ? (<DialogPrimitive.Close aria-label="Close" className="absolute top-4 right-4 flex h-8 w-8 items-center justify-center rounded-full text-ink/45 transition-colors duration-200 hover:bg-canvas hover:text-ink">
            <X className="h-4 w-4"/>
          </DialogPrimitive.Close>) : null}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>);
}
export function DialogHeader({ className, ...rest }) {
    return <div className={cn('flex flex-col gap-1.5 text-left', className)} {...rest}/>;
}
export function DialogFooter({ className, ...rest }) {
    return (<div className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...rest}/>);
}
export function DialogTitle({ className, ...rest }) {
    return (<DialogPrimitive.Title className={cn('font-heading text-[1.15rem] font-extrabold tracking-[-0.01em] text-ink', className)} {...rest}/>);
}
export function DialogDescription({ className, ...rest }) {
    return (<DialogPrimitive.Description className={cn('text-[0.85rem] leading-relaxed text-ink-muted', className)} {...rest}/>);
}
