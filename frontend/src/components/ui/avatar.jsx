import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { cn } from '../../lib/utils';
export function Avatar({ className, ...rest }) {
    return (<AvatarPrimitive.Root className={cn('relative flex h-9 w-9 shrink-0 overflow-hidden rounded-full', className)} {...rest}/>);
}
export function AvatarImage({ className, ...rest }) {
    return <AvatarPrimitive.Image className={cn('aspect-square h-full w-full', className)} {...rest}/>;
}
export function AvatarFallback({ className, ...rest }) {
    return (<AvatarPrimitive.Fallback className={cn('flex h-full w-full items-center justify-center rounded-full bg-ink text-[0.72rem] font-bold text-white', className)} {...rest}/>);
}
