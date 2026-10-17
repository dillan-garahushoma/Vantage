import { ArrowDown, ArrowUp, ChevronsUpDown, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { Input } from '../ui/input'
import { EmptyState } from './EmptyState'

export interface DataTableColumn<T> {
  key: string
  header: ReactNode
  align?: 'left' | 'right'
  sortable?: boolean
  /** Columns whose value needs a phone-sized explanation are hidden on mobile. */
  hideOnMobile?: boolean
  width?: string
  render?: (row: T) => ReactNode
}

export interface DataTableFilter {
  key: string
  /** The label of the “no filter” option, e.g. “All statuses”. */
  label: string
  options: string[]
  /** The row value the option is matched against; defaults to the column key. */
  getValue?: (row: Record<string, unknown>) => string
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  /** Stable React key for a row. */
  rowKey: (row: T) => string | number
  /** Object keys the search box looks through. */
  searchKeys?: string[]
  searchPlaceholder?: string
  filters?: DataTableFilter[]
  initialSort?: { key: string; dir: 'asc' | 'desc' }
  onRowClick?: (row: T) => void
  emptyTitle?: string
  emptyDescription?: ReactNode
  emptyAction?: ReactNode
  className?: string
}

function sortable(value: unknown): string | number {
  if (typeof value === 'number') return value
  if (value instanceof Date) return value.getTime()
  return String(value ?? '').toLowerCase()
}

/**
 * The operational table.
 *
 * Search, sort and filters are client-side over the page the API already
 * returned — the server owns scoping and paging, so this never re-filters beyond
 * what the caller was allowed to see. On a phone the same rows render as cards,
 * because a horizontally scrolled table hides the one column that matters.
 */
export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  rowKey,
  searchKeys = [],
  searchPlaceholder = 'Search',
  filters = [],
  initialSort,
  onRowClick,
  emptyTitle = 'Nothing here yet',
  emptyDescription,
  emptyAction,
  className,
}: DataTableProps<T>) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState(initialSort ?? null)
  const [active, setActive] = useState<Record<string, string>>({})

  const processed = useMemo(() => {
    let list = [...rows]
    const needle = query.trim().toLowerCase()

    if (needle) {
      const keys = searchKeys.length > 0 ? searchKeys : Object.keys(list[0] ?? {})
      list = list.filter((row) =>
        keys.some((key) => String(row[key] ?? '').toLowerCase().includes(needle)),
      )
    }

    for (const filter of filters) {
      const chosen = active[filter.key]
      if (!chosen || chosen === 'all') continue
      list = list.filter((row) =>
        filter.getValue
          ? filter.getValue(row) === chosen
          : String(row[filter.key] ?? '') === chosen,
      )
    }

    if (sort) {
      const direction = sort.dir === 'desc' ? -1 : 1
      list.sort((a, b) => {
        const av = sortable(a[sort.key])
        const bv = sortable(b[sort.key])
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * direction
        return String(av).localeCompare(String(bv)) * direction
      })
    }

    return list
  }, [rows, query, active, sort, searchKeys, filters])

  function toggleSort(key: string) {
    setSort((current) =>
      current?.key === key
        ? { key, dir: current.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'asc' },
    )
  }

  const hasControls = searchKeys.length > 0 || filters.length > 0

  return (
    <div className={cn('flex flex-col', className)}>
      {hasControls ? (
        <div className="flex flex-col gap-3 border-b border-line pb-4 sm:flex-row sm:items-center sm:justify-between">
          {searchKeys.length > 0 ? (
            <div className="relative w-full sm:max-w-[280px]">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink/30" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                aria-label={searchPlaceholder}
                className="h-10 bg-surface pl-9 text-[0.85rem]"
              />
            </div>
          ) : null}

          {filters.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              {filters.map((filter) => (
                <select
                  key={filter.key}
                  aria-label={filter.label}
                  value={active[filter.key] ?? 'all'}
                  onChange={(event) =>
                    setActive((current) => ({ ...current, [filter.key]: event.target.value }))
                  }
                  className="h-10 rounded-xl border border-line bg-surface px-3 text-[0.82rem] font-medium text-ink/75 transition-colors duration-200 hover:border-brand-soft focus:border-brand focus:outline-none"
                >
                  <option value="all">{filter.label}</option>
                  {filter.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {processed.length === 0 ? (
        <div className="py-8">
          <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
        </div>
      ) : (
        <>
          <div className="scrollbar-slim hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[720px] border-separate border-spacing-0">
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      scope="col"
                      style={column.width ? { width: column.width } : undefined}
                      className={cn(
                        'border-b border-line px-4 py-3 text-left text-[0.7rem] font-semibold tracking-[0.1em] text-ink/45 uppercase',
                        column.align === 'right' && 'text-right',
                        column.sortable && 'cursor-pointer select-none hover:text-brand-ink',
                      )}
                      onClick={column.sortable ? () => toggleSort(column.key) : undefined}
                    >
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5',
                          column.align === 'right' && 'flex-row-reverse',
                        )}
                      >
                        {column.header}
                        {column.sortable ? (
                          sort?.key === column.key ? (
                            sort.dir === 'asc' ? (
                              <ArrowUp className="h-3 w-3" />
                            ) : (
                              <ArrowDown className="h-3 w-3" />
                            )
                          ) : (
                            <ChevronsUpDown className="h-3 w-3 opacity-40" />
                          )
                        ) : null}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {processed.map((row) => (
                    <tr
                      key={rowKey(row)}
                      className={cn(
                        'transition-colors duration-150',
                        onRowClick && 'cursor-pointer hover:bg-canvas/70',
                      )}
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                    >
                      {columns.map((column) => (
                        <td
                          key={column.key}
                          className={cn(
                            'border-b border-line-soft px-4 py-3.5 align-middle text-[0.85rem] text-ink/75',
                            column.align === 'right' && 'text-right',
                          )}
                        >
                          {column.render ? column.render(row) : String(row[column.key] ?? '—')}
                        </td>
                      ))}
                    </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3 pt-4 lg:hidden">
            {processed.map((row) => (
              <button
                key={rowKey(row)}
                type="button"
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  'w-full rounded-2xl border border-line bg-surface p-4 text-left transition-all duration-200',
                  onRowClick && 'hover:border-brand-soft hover:shadow-soft',
                )}
              >
                {columns.map((column) => (
                  <div
                    key={column.key}
                    className={cn(
                      'flex items-center justify-between gap-4 py-1.5',
                      column.hideOnMobile && 'hidden',
                    )}
                  >
                    <span className="text-[0.72rem] font-semibold tracking-[0.08em] text-ink/40 uppercase">
                      {column.header}
                    </span>
                    <span className="text-right text-[0.83rem] text-ink/75">
                      {column.render ? column.render(row) : String(row[column.key] ?? '—')}
                    </span>
                  </div>
                ))}
              </button>
            ))}
          </div>
        </>
      )}

      <div className="pt-4 text-[0.75rem] text-ink/40">
        {processed.length} of {rows.length} records
      </div>
    </div>
  )
}
