import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useEstate } from '../context/EstateContext'
import { useAuth } from '../context/AuthContext'
import { Button, ErrorState, LoadingState } from './ui'
import { IconClock } from './Icons'

/**
 * Estate-scoped screens can only render once the server has resolved which
 * estates the caller may act inside. An unresolved or empty membership list is a
 * real state, not an error: the account is registered but not yet provisioned.
 */
export function RequireEstate({ children }: { children: ReactNode }) {
  const { loading, error, awaitingProvisioning, reload } = useEstate()
  const { user } = useAuth()

  if (loading) return <LoadingState label="Resolving your estate access" />

  if (error) {
    return (
      <ErrorState
        title="Could not resolve your estates"
        message={error.message}
        requestId={error.requestId}
        action={
          <Button variant="secondary" onClick={reload}>
            Try again
          </Button>
        }
      />
    )
  }

  if (awaitingProvisioning) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="hairline rounded-xs bg-surface p-6">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xs bg-ochre-wash text-ochre-ink">
            <IconClock size={19} />
          </span>
          <h1 className="mt-4 text-[22px] font-semibold">Awaiting estate provisioning</h1>
          <p className="mt-2 text-[14px] text-ink-soft">
            Welcome, {user?.full_name?.split(' ')[0] ?? 'there'}. Your account is active, but no HOA
            has linked it to an estate yet.
          </p>
          <p className="mt-2 text-[14px] text-ink-soft">
            Your estate administrator needs to add you as a member of your estate — usually by
            matching the unit number you registered with. Until then, estate data stays closed to
            you. That is the point of the boundary: a registration alone is not proof of access.
          </p>

          <ul className="mt-5 space-y-2.5">
            {[
              'Ask your HOA administrator to add you to the estate register.',
              'Confirm the unit number on this account matches your property.',
              'Once provisioned, your dashboard opens automatically.',
            ].map((step, index) => (
              <li key={step} className="flex gap-3">
                <span className="num mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-xs border border-ink/20 text-[11px] font-semibold text-accent-ink">
                  {index + 1}
                </span>
                <span className="text-[13.5px] text-ink-soft">{step}</span>
              </li>
            ))}
          </ul>

          <div className="mt-6 flex flex-wrap gap-3 border-t border-ink/15 pt-5">
            <Button variant="primary" onClick={reload}>
              Check again
            </Button>
            <Link
              to="/"
              className="inline-flex items-center rounded-xs border border-ink/25 px-3.5 py-2 text-sm font-medium hover:bg-paper"
            >
              Back to home
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
