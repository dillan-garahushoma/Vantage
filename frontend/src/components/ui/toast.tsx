import { useEffect, useState } from 'react'
import { CheckCircle2, Info } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface ToastInput {
  title: string
  description?: string
  tone?: 'positive' | 'neutral'
}

interface ToastItem extends ToastInput {
  id: number
}

/**
 * A deliberately tiny toaster.
 *
 * Nothing here is business logic: it is the single place a screen says “that
 * worked”. The API's own error surface is `ErrorState`, shown inline where the
 * failure happened, so a toast is only ever used for a confirmed success. A
 * module-level listener keeps it usable from a plain function — no context, no
 * provider, no dependency.
 */
const TOAST_MS = 5000
let items: ToastItem[] = []
const listeners = new Set<(next: ToastItem[]) => void>()
let nextId = 1

function publish() {
  const snapshot = items
  for (const listener of listeners) listener(snapshot)
}

export function toast(input: ToastInput) {
  const item: ToastItem = { id: nextId++, ...input }
  items = [...items, item]
  publish()
  window.setTimeout(() => dismiss(item.id), TOAST_MS)
}

export function dismiss(id: number) {
  items = items.filter((item) => item.id !== id)
  publish()
}

export function Toaster() {
  const [shown, setShown] = useState<ToastItem[]>(items)

  useEffect(() => {
    listeners.add(setShown)
    return () => {
      listeners.delete(setShown)
    }
  }, [])

  if (shown.length === 0) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-4 bottom-4 z-[60] flex flex-col items-end gap-2 sm:right-6 sm:bottom-6 sm:left-auto"
    >
      {shown.map((item) => (
        <div
          key={item.id}
          className="animate-fade-up pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl border border-line bg-surface px-4 py-3.5 shadow-lift"
        >
          <span
            className={cn(
              'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl',
              item.tone === 'neutral' ? 'bg-brand-wash text-brand-ink' : 'bg-mint-wash text-mint-ink',
            )}
          >
            {item.tone === 'neutral' ? (
              <Info className="h-4 w-4" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[0.85rem] font-semibold text-ink">{item.title}</p>
            {item.description ? (
              <p className="mt-0.5 text-[0.78rem] leading-relaxed text-ink-muted">
                {item.description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => dismiss(item.id)}
            className="shrink-0 rounded-full px-1.5 text-[0.75rem] text-ink/40 hover:text-ink"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
