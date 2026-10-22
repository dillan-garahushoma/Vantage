import { cn } from '../../lib/utils';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './sheet';

/**
 * The record panel every operational screen opens from a row.
 *
 * Default side is 'center': a centered glassmorphism overlay with blurred
 * backdrop. Pass side='right' only for contexts where a side panel is
 * semantically correct (none currently — MobileNav uses Sheet directly).
 *
 * One component so complaint, work order, member and property panels all
 * behave identically: aria-modal focus trap, escape to close, sticky header,
 * optional sticky footer.
 */
export function Drawer({
  open,
  onOpenChange,
  onClose,
  title,
  subtitle,
  badge,
  children,
  footer,
  width = 'sm:max-w-[620px]',
  side = 'center',
  className,
}) {
  // Support both onOpenChange (Radix pattern) and onClose (legacy pattern)
  const handleOpenChange = onOpenChange ?? ((open) => { if (!open && onClose) onClose(); });

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent
        side={side}
        className={cn(
          'scrollbar-slim gap-0 overflow-y-auto p-0',
          side === 'center' ? width : undefined,
          className,
        )}
      >
        <SheetHeader className={cn(
          'sticky top-0 z-10 border-b px-6 py-5',
          side === 'center'
            ? 'border-white/10 bg-surface/70 backdrop-blur-md'
            : 'border-line bg-surface/95 backdrop-blur',
        )}>
          <div className="flex items-start justify-between gap-4 pr-8">
            <div className="min-w-0">
              <SheetTitle>{title}</SheetTitle>
              {subtitle ? (
                <SheetDescription className="mt-1 truncate">{subtitle}</SheetDescription>
              ) : null}
            </div>
            {badge ? (
              <div className="flex shrink-0 items-center gap-2">{badge}</div>
            ) : null}
          </div>
        </SheetHeader>

        <div className="px-6 py-5">{children}</div>

        {footer ? (
          <div className={cn(
            'sticky bottom-0 border-t px-6 py-4',
            side === 'center'
              ? 'border-white/10 bg-surface/70 backdrop-blur-md'
              : 'border-line bg-surface/95 backdrop-blur',
          )}>
            {footer}
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
