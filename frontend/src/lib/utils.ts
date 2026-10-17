import { clsx } from 'clsx'
import type { ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * The one class-name join in the UI layer.
 *
 * `clsx` for conditionals, `tailwind-merge` so a caller's `className` prop wins
 * against a primitive's own conflicting utility (`px-6` passed to a component
 * that says `px-4` keeps `px-6`) instead of the two racing in the stylesheet.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
