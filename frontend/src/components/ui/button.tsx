import { cva } from 'class-variance-authority'
import type { VariantProps } from 'class-variance-authority'
import type { ComponentPropsWithRef, ReactNode } from 'react'
import { cn } from '../../lib/utils'

/**
 * The one button in the product.
 *
 * `default` is the brand action (violet), `ink` is the dark, high-contrast
 * action the workspace uses for “+ Create work order”, and the rest are
 * supporting weight. Radii and heights are overridable from `className` — the
 * merge in `cn` keeps the caller's `rounded-full` or `h-11` rather than racing it.
 */
export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-[background-color,border-color,color,transform,box-shadow] duration-200 ease-soft disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-brand text-white shadow-soft hover:bg-brand-ink',
        ink: 'bg-ink text-white hover:bg-brand',
        secondary: 'bg-canvas text-ink hover:bg-brand-wash',
        outline: 'border border-line bg-surface text-ink hover:border-brand-soft hover:bg-canvas',
        ghost: 'text-ink-soft hover:bg-canvas hover:text-ink',
        destructive: 'bg-signal text-white hover:bg-signal-ink',
        link: 'text-brand-ink underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3 text-[0.82rem]',
        lg: 'h-11 px-6',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

export interface ButtonProps
  extends ComponentPropsWithRef<'button'>,
    VariantProps<typeof buttonVariants> {
  children?: ReactNode
}

export function Button({ className, variant, size, type = 'button', ...rest }: ButtonProps) {
  return (
    <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...rest} />
  )
}
