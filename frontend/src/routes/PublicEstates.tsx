import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Keyline } from '../components/Brand'
import { PublicShell } from '../components/PublicShell'
import { IconArrowRight, IconSearch } from '../components/Icons'
import { Button, Card, Chip, EmptyState, ErrorState, Input, LoadingState } from '../components/ui'
import type { PublicEstateListItem } from '../lib/contract'
import { PUBLIC_PAGE_SIZE, listPublicEstates, photoAlt, publicPhotoUrl } from '../lib/publicDirectory'
import { useAsync } from '../lib/useAsync'

/**
 * A thumbnail whose reserved box matches what is rendered, so a slow image does
 * not shift the grid. The stored shapes vary, hence `object-cover` and an
 * explicit 3:2 box rather than the file's own dimensions.
 */
export function EstateThumb({ item, className }: { item: PublicEstateListItem; className?: string }) {
  if (!item.cover_photo_public_id) {
    return (
      <div
        className={`flex h-40 w-full items-center justify-center border-b border-ink/15 bg-ink/5 text-[12px] text-ink-muted ${className ?? ''}`}
      >
        No photograph yet
      </div>
    )
  }
  return (
    <img
      src={publicPhotoUrl(item.cover_photo_public_id, 'thumb')}
      alt={photoAlt(item.name, null)}
      width={480}
      height={320}
      loading="lazy"
      className={`h-40 w-full border-b border-ink/15 bg-ink/5 object-cover ${className ?? ''}`}
    />
  )
}

function EstateCardRow({ item }: { item: PublicEstateListItem }) {
  return (
    <li>
      <Card className="flex h-full flex-col overflow-hidden">
        <EstateThumb item={item} />
        <div className="flex flex-1 flex-col p-4">
          <h2 className="text-[16px] font-semibold">{item.name}</h2>
          <p className="num mt-1 text-[12.5px] text-ink-muted">
            {item.suburb}, {item.city}, {item.province}
          </p>
          {item.description ? (
            <p className="mt-2.5 line-clamp-3 text-[13px] text-ink-soft">{item.description}</p>
          ) : null}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Chip glyph="◫">{item.unit_count} units</Chip>
          </div>
          <Link
            to={`/estates/${item.estate_id}`}
            className="mt-auto inline-flex items-center gap-1.5 pt-4 text-[13px] font-medium text-accent-ink hover:underline"
          >
            View this complex
            <IconArrowRight size={15} />
          </Link>
        </div>
      </Card>
    </li>
  )
}

export function PublicEstates() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') ?? ''
  const [query, setQuery] = useState(initialQuery)
  const [page, setPage] = useState(1)
  const [submitted, setSubmitted] = useState(initialQuery)

  const directory = useAsync(
    () => listPublicEstates({ page, page_size: PUBLIC_PAGE_SIZE, q: submitted }),
    [page, submitted],
  )

  function submit(event: FormEvent) {
    event.preventDefault()
    setPage(1)
    setSubmitted(query.trim())
    const next = query.trim()
    setSearchParams(next ? { q: next } : {}, { replace: true })
  }

  const items = directory.data?.items ?? []
  const total = directory.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PUBLIC_PAGE_SIZE))

  return (
    <PublicShell>
      <section className="border-b border-ink/15 bg-surface">
        <div className="mx-auto max-w-[1200px] px-5 py-10">
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Public directory
          </p>
          <h1 className="mt-3 text-[30px] leading-tight font-semibold sm:text-[36px]">
            Find a complex
          </h1>
          <p className="mt-3 max-w-2xl text-[14.5px] text-ink-soft">
            These are the estates whose administrators have chosen to publish a profile. An estate
            that has not opted in simply is not here — there is no way to look one up, and nothing
            about its residents, units or complaints is ever published.
          </p>

          <form className="mt-6 flex max-w-xl items-end gap-2" onSubmit={submit} role="search">
            <label className="flex-1">
              <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                Search by name, suburb or city
              </span>
              <Input
                name="q"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Centurion"
              />
            </label>
            <Button type="submit" variant="primary">
              <IconSearch size={16} />
              Search
            </Button>
          </form>
          <Keyline className="mt-8" />
        </div>
      </section>

      <section className="mx-auto max-w-[1200px] px-5 py-8">
        {directory.loading ? (
          <LoadingState label="Loading published complexes" />
        ) : directory.error ? (
          <ErrorState
            title={
              directory.error.status === 503
                ? 'The directory is unavailable right now'
                : 'Could not load the directory'
            }
            message={directory.error.message}
            requestId={directory.error.requestId}
            action={
              <Button variant="secondary" onClick={directory.reload}>
                Try again
              </Button>
            }
          />
        ) : items.length === 0 ? (
          <EmptyState
            title={submitted ? 'No complex matches that search' : 'No complexes are published yet'}
            body={
              submitted
                ? 'Try a different estate name, suburb or city — or clear the search to see everything that is published.'
                : 'When an estate administrator publishes their complex, it appears here with its description and photographs.'
            }
            action={
              submitted ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setQuery('')
                    setSubmitted('')
                    setSearchParams({}, { replace: true })
                  }}
                >
                  Clear the search
                </Button>
              ) : undefined
            }
          />
        ) : (
          <>
            <p className="num mb-4 text-[12.5px] text-ink-muted">
              {total} published {total === 1 ? 'complex' : 'complexes'}
              {submitted ? ` matching “${submitted}”` : ''}
            </p>
            <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <EstateCardRow key={item.estate_id} item={item} />
              ))}
            </ul>

            {pages > 1 ? (
              <div className="mt-8 flex items-center justify-between gap-3">
                <p className="num text-[12px] text-ink-muted">
                  page {page} of {pages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    disabled={page <= 1}
                    onClick={() => setPage((current) => current - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={page >= pages}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </section>
    </PublicShell>
  )
}
