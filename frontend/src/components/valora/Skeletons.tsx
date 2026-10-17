import { cn } from '../../lib/utils'

export function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={cn('animate-pulse rounded-xl bg-line-soft', className)} style={style} />
}

export function MetricCardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-2xl border border-line bg-surface p-5', className)}>
      <Skeleton className="h-9 w-9 rounded-xl" />
      <Skeleton className="mt-6 h-8 w-28" />
      <Skeleton className="mt-2 h-3 w-36" />
      <Skeleton className="mt-5 h-7 w-full" />
    </div>
  )
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number
  columns?: number
  className?: string
}) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: rows }, (_, row) => (
        <div key={row} className="flex gap-4 border-b border-line-soft pb-3">
          {Array.from({ length: columns }, (_, column) => (
            <Skeleton key={column} className={cn('h-4', column === 0 ? 'w-1/3' : 'flex-1')} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('flex h-48 items-end gap-2 rounded-2xl bg-canvas p-5', className)}>
      {[36, 58, 44, 76, 52, 88, 64, 72, 49, 82, 60, 94].map((height, index) => (
        <Skeleton
          key={index}
          className="flex-1 rounded-t-md rounded-b-sm"
          style={{ height: `${height}%` }}
        />
      ))}
    </div>
  )
}

export default Skeleton
