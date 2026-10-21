import * as SwitchPrimitive from '@radix-ui/react-switch';
import { cn } from '../../lib/utils';
export function Switch({ className, ...rest }) {
    return (<SwitchPrimitive.Root className={cn('peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-brand data-[state=unchecked]:bg-line', className)} {...rest}>
      <SwitchPrimitive.Thumb className="pointer-events-none block h-4 w-4 rounded-full bg-white shadow-soft transition-transform duration-200 data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0"/>
    </SwitchPrimitive.Root>);
}
