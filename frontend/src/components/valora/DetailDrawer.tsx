import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { Drawer } from '../ui/drawer'

export interface DetailDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  subtitle?: ReactNode
  badge?: ReactNode
  children: ReactNode
  footer?: ReactNode
  width?: string
  /** Shows a skeleton for a moment while the detail settles into place. */
  loading?: boolean
}

/**
 * The review panel for a finding.
 *
 * Its only difference from the operational drawers is the skeleton: a finding
 * opens with a lot of text, and showing the shape of it first keeps the panel
 * from jumping while the content settles.
 */
export function DetailDrawer({
  open,
  onOpenChange,
  title,
  subtitle,
  badge,
  children,
  footer,
  width = 'sm:max-w-[600px]',
  loading = false,
}: DetailDrawerProps) {
  const [showSkeleton, setShowSkeleton] = useState(loading)

  useEffect(() => {
    if (!open) return
    setShowSkeleton(loading)
    if (!loading) return
    const timer = window.setTimeout(() => setShowSkeleton(false), 520)
    return () => window.clearTimeout(timer)
  }, [open, loading])

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      subtitle={subtitle}
      badge={badge}
      width={width}
      footer={footer}
    >
      {showSkeleton ? (
        <div className="space-y-4" aria-busy="true">
          <div className={cn('h-24 animate-pulse rounded-2xl bg-canvas')} />
          <div className="h-3 w-2/3 animate-pulse rounded-full bg-line-soft" />
          <div className="h-3 w-full animate-pulse rounded-full bg-line-soft" />
          <div className="h-3 w-4/5 animate-pulse rounded-full bg-line-soft" />
          <div className="h-40 animate-pulse rounded-2xl bg-canvas" />
        </div>
      ) : (
        children
      )}
    </Drawer>
  )
}
