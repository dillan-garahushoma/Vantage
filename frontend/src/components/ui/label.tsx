import * as LabelPrimitive from '@radix-ui/react-label'
import type { ComponentPropsWithRef } from 'react'
import { cn } from '../../lib/utils'

/** Radix label: clicking it focuses the control, as a label should. */
export function Label({ className, ...rest }: ComponentPropsWithRef<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      className={cn('block text-[0.8rem] font-semibold text-ink/70', className)}
      {...rest}
    />
  )
}
