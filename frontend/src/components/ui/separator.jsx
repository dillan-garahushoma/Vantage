import * as SeparatorPrimitive from '@radix-ui/react-separator';
import { cn } from '../../lib/utils';
export function Separator({ className, orientation = 'horizontal', decorative = true, ...rest }) {
    return (<SeparatorPrimitive.Root decorative={decorative} orientation={orientation} className={cn('shrink-0 bg-line', orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px', className)} {...rest}/>);
}
