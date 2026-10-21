import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area';
import { cn } from '../../lib/utils';
/** A themed scroll region, for panes that scroll independently of the page. */
export function ScrollArea({ className, children, ...rest }) {
    return (<ScrollAreaPrimitive.Root className={cn('relative overflow-hidden', className)} {...rest}>
      <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollAreaPrimitive.Scrollbar orientation="vertical" className="flex w-2 touch-none select-none p-px transition-colors">
        <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-line"/>
      </ScrollAreaPrimitive.Scrollbar>
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>);
}
