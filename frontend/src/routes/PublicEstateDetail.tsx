import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Keyline } from '../components/Brand'
import { PublicShell } from '../components/PublicShell'
import { IconArrowRight, IconCheck, IconPin } from '../components/Icons'
import { Button, Card, Chip, EmptyState, ErrorState, LinkButton, LoadingState } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import type { PublicEstateDetail as EstateDetail, PublicLivingScoreSummary } from '../lib/contract'
import { getPublicEstate, photoAlt, publicPhotoUrl } from '../lib/publicDirectory'
import { displayLabel } from '../lib/format'
import { useAsync } from '../lib/useAsync'

/**
 * The published score, and only what was published: a number, the status the
 * engine recorded, when it was calculated and which engine version produced it.
 * Nothing here recomputes, averages or re-weights anything — if the API does not
 * send a score there is no score to show, and the card says so.
 */
export function PublicScoreCard({ summary }: { summary: PublicLivingScoreSummary }) {
  const isDemo = summary.data_origin === 'demo'
  const hasScore = summary.overall_score !== null && summary.overall_score !== undefined

  return (
    <Card as="section" className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
          Living Score
        </p>
        {isDemo ? (
          <Chip tone="warn" glyph="◷">
            Demo data
          </Chip>
        ) : null}
      </div>

      <p className="num mt-2 text-[34px] leading-none font-semibold">
        {hasScore ? Number(summary.overall_score).toFixed(1) : '—'}
        {hasScore ? <span className="ml-1 text-[14px] font-normal text-ink-muted">/ 100</span> : null}
      </p>

      <dl className="mt-4 space-y-2 border-t border-ink/15 pt-3 text-[12.5px]">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Status</dt>
          <dd className="num font-medium">{displayLabel(summary.status)}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Calculated for</dt>
          <dd className="num font-medium">{summary.as_of.slice(0, 10)}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-ink-soft">Engine</dt>
          <dd className="num font-medium">{summary.engine_version}</dd>
        </div>
      </dl>

      <p className="mt-3 border-t border-ink/15 pt-3 text-[12px] text-ink-muted">
        {isDemo
          ? 'This estate is a demonstration environment. The figures show how the score works; they are not a real community’s record.'
          : 'Published by this estate’s administrator. The score is a stored calculation, not a live estimate.'}
      </p>
    </Card>
  )
}

function Gallery({ estate }: { estate: EstateDetail }) {
  const [active, setActive] = useState(0)
  // The contract marks every nested list optional, so the screen treats a
  // missing gallery exactly like an empty one rather than rendering nothing.
  const photos = estate.photos ?? []

  if (photos.length === 0) {
    return (
      <EmptyState
        title="No photographs published yet"
        body="This estate has published its profile but has not added any photographs."
      />
    )
  }

  const current = photos[active] ?? photos[0]

  return (
    <div>
      <img
        src={publicPhotoUrl(current.public_id, 'full')}
        alt={photoAlt(estate.name, current.caption)}
        width={1920}
        height={1280}
        className="hairline h-64 w-full rounded-xs bg-ink/5 object-cover sm:h-80"
      />
      {current.caption ? (
        <p className="mt-2 text-[12.5px] text-ink-muted">{current.caption}</p>
      ) : null}

      {photos.length > 1 ? (
        <ul className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {photos.map((photo, index) => (
            <li key={photo.public_id}>
              <button
                type="button"
                onClick={() => setActive(index)}
                aria-label={`Show ${photoAlt(estate.name, photo.caption)}`}
                aria-current={index === active}
                className={
                  index === active
                    ? 'block rounded-xs border-2 border-accent p-0.5'
                    : 'block rounded-xs border border-ink/15 p-0.5 hover:border-ink/40'
                }
              >
                <img
                  src={publicPhotoUrl(photo.public_id, 'thumb')}
                  alt=""
                  width={480}
                  height={320}
                  className="h-14 w-20 bg-ink/5 object-cover"
                />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function DetailBody({ estateId }: { estateId: number }) {
  const { user } = useAuth()
  const estate = useAsync(() => getPublicEstate(estateId), [estateId])

  if (estate.loading) return <LoadingState label="Loading this complex" />

  if (estate.error) {
    const notFound = estate.error.status === 404
    return (
      <div className="mx-auto max-w-2xl px-5 py-16">
        <ErrorState
          title={notFound ? 'That complex is not published' : 'Could not load this complex'}
          message={
            notFound
              ? 'Either it does not exist, or its administrator has not published it. A private estate is indistinguishable from an unknown one.'
              : estate.error.message
          }
          requestId={estate.error.requestId}
          action={
            notFound ? (
              <LinkButton to="/estates" variant="secondary">
                Back to the directory
              </LinkButton>
            ) : (
              <Button variant="secondary" onClick={estate.reload}>
                Try again
              </Button>
            )
          }
        />
      </div>
    )
  }

  const detail = estate.data
  if (!detail) return null

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8">
      <nav className="mb-4 text-[12.5px] text-ink-muted">
        <Link to="/estates" className="hover:underline">
          Find a complex
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink-soft">{detail.name}</span>
      </nav>

      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[30px] leading-tight font-semibold">{detail.name}</h1>
          <p className="num mt-2 flex items-center gap-1.5 text-[13px] text-ink-muted">
            <IconPin size={15} />
            {detail.suburb}, {detail.city}, {detail.province}
          </p>
        </div>
        <Chip glyph="◫">{detail.unit_count} units</Chip>
      </header>

      <Keyline className="mt-5" />

      {/* `min-w-0` on both tracks: a grid item's automatic minimum is its
          min-content, and a published photograph's intrinsic width is much wider
          than a phone — without this the column, and the page, grew with it. */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="min-w-0 space-y-6">
          <Gallery estate={detail} />

          <Card as="section" className="p-5">
            <h2 className="text-[15px] font-semibold">About this complex</h2>
            {detail.description ? (
              <p className="mt-2 whitespace-pre-line text-[14px] text-ink-soft">
                {detail.description}
              </p>
            ) : (
              <p className="mt-2 text-[13px] text-ink-muted">
                The administrator has not written a description yet.
              </p>
            )}
          </Card>
        </div>

        <div className="min-w-0 space-y-5">
          {detail.living_score ? <PublicScoreCard summary={detail.living_score} /> : null}

          <Card as="section" className="p-5">
            <h2 className="text-[15px] font-semibold">Join this estate</h2>
            <p className="mt-2 text-[13px] text-ink-soft">
              Membership is by invitation: your estate office gives you a one-time code, and you redeem
              it against your unit number. A code is the proof of the right to join — and an estate is
              never listed here until its administrator publishes it.
            </p>
            <ul className="mt-4 space-y-2">
              {[
                'Ask your estate office for the join code.',
                'Create an account (residents register themselves).',
                'Redeem the code against your unit number.',
              ].map((step, index) => (
                <li key={step} className="flex gap-2.5 text-[13px] text-ink-soft">
                  <span className="num mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-xs border border-ink/20 text-[11px] font-semibold text-accent-ink">
                    {index + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ul>
            <div className="mt-5 flex flex-wrap gap-2">
              {user ? (
                <LinkButton to="/join" variant="primary">
                  I have a code
                  <IconArrowRight size={16} />
                </LinkButton>
              ) : (
                <LinkButton to="/register" variant="primary">
                  Create an account
                  <IconArrowRight size={16} />
                </LinkButton>
              )}
              <LinkButton to="/estates" variant="secondary">
                Other complexes
              </LinkButton>
            </div>
            <p className="mt-4 flex items-start gap-2 border-t border-ink/15 pt-3 text-[12px] text-ink-muted">
              <IconCheck size={14} className="mt-0.5 shrink-0 text-accent-ink" />
              VALORA never publishes unit numbers, addresses, resident names or complaint records.
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}

export function PublicEstateDetail() {
  const params = useParams()
  const estateId = Number(params.id)
  if (!Number.isFinite(estateId) || estateId <= 0) {
    return (
      <PublicShell>
        <div className="mx-auto max-w-2xl px-5 py-16">
          <ErrorState title="That address is not a complex" message="Check the link and try again." />
        </div>
      </PublicShell>
    )
  }
  return (
    <PublicShell>
      <DetailBody estateId={estateId} />
    </PublicShell>
  )
}
