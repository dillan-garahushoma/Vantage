import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { Photo, PhotoFallback } from '../components/Photo';
import { IconArrowRight, IconPin, IconSearch } from '../components/Icons';
import { Button, Card, EmptyState, ErrorState, Input, Skeleton, SkeletonText } from '../components/ui';
import { PUBLIC_PAGE_SIZE, listPublicEstates, photoAlt, publicPhotoUrl } from '../lib/publicDirectory';
import { useAsync } from '../lib/useAsync';
/**
 * One published complex, as a card.
 *
 * The photograph *is* the card: a reserved 3:2 box, cropped rather than
 * letterboxed, which measures 371 × 247 against the 371 × 160 strip this screen
 * used to draw — 1.55× the height, and 56% of the card instead of 42%.
 * A visitor comparing complexes compares photographs first, then where, then how
 * big — so those are the three things in reading order, and everything else the
 * API does not publish (no price, no rating, no badge) is simply absent rather
 * than invented.
 *
 * The estate name is the card's only link, stretched over the card with an
 * `::after` overlay. That gives one link with a real destination name instead of
 * a card-shaped click target with no accessible name, while making the whole
 * card clickable. `relative` + `overflow-hidden` on the card keep the overlay
 * inside its own bounds.
 */
function EstateCard({ item }) {
    return (<Card as="li" className="group relative flex h-full flex-col overflow-hidden transition-colors hover:border-ink/40">
      <div className="relative aspect-[3/2] w-full overflow-hidden border-b border-ink/15 bg-ink/5">
        {item.cover_photo_public_id ? (<Photo src={publicPhotoUrl(item.cover_photo_public_id, 'thumb')} alt={photoAlt(item.name, null)} width={480} height={320} fallbackLabel="No photograph yet" className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.02]"/>) : (<PhotoFallback label="No photograph yet" className="h-full w-full"/>)}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <h2 className="text-[16px] leading-snug font-semibold">
          <Link to={`/estates/${item.estate_id}`} className="after:absolute after:inset-0 after:content-[''] hover:underline">
            {item.name}
          </Link>
        </h2>

        <p className="mt-1.5 flex items-start gap-1.5 text-[12.5px] text-ink-muted">
          <IconPin size={14} className="mt-[2px] shrink-0"/>
          <span>
            {item.suburb}, {item.city}, {item.province}
          </span>
        </p>

        {item.description ? (<p className="mt-3 line-clamp-3 text-[13px] leading-relaxed text-ink-soft">
            {item.description}
          </p>) : null}

        <div className="mt-auto flex items-center justify-between gap-3 pt-4">
          <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-accent-ink">
            View this complex
            <IconArrowRight size={15}/>
          </span>
          <span className="num shrink-0 text-[12.5px] text-ink-muted">{item.unit_count} units</span>
        </div>
      </div>
    </Card>);
}
/**
 * The grid, at its final geometry, before the data arrives.
 *
 * A skeleton is only worth having if it is the same shape as the thing it stands
 * in for — otherwise the page reflows when the data lands, which is the defect it
 * was meant to remove. It is `aria-hidden`, the region is `aria-busy`, and a
 * polite status carries the words, so a screen reader hears "loading" once
 * instead of hearing six decorative boxes.
 */
function DirectorySkeleton() {
    return (<div aria-busy="true">
      <p role="status" className="sr-only">
        Loading published complexes…
      </p>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => (<div key={index} className="hairline flex flex-col overflow-hidden rounded-xs bg-surface">
            <Skeleton className="aspect-[3/2] w-full"/>
            <div className="p-4">
              <Skeleton className="h-4 w-2/3"/>
              <Skeleton className="mt-3 h-3 w-1/2"/>
              <SkeletonText lines={3} className="mt-4"/>
            </div>
          </div>))}
      </div>
    </div>);
}
export function PublicEstates() {
    const [searchParams, setSearchParams] = useSearchParams();
    const initialQuery = searchParams.get('q') ?? '';
    const [query, setQuery] = useState(initialQuery);
    const [page, setPage] = useState(1);
    const [submitted, setSubmitted] = useState(initialQuery);
    const directory = useAsync(() => listPublicEstates({ page, page_size: PUBLIC_PAGE_SIZE, q: submitted }), [page, submitted]);
    function submit(event) {
        event.preventDefault();
        setPage(1);
        setSubmitted(query.trim());
        const next = query.trim();
        setSearchParams(next ? { q: next } : {}, { replace: true });
    }
    function clear() {
        setQuery('');
        setSubmitted('');
        setPage(1);
        setSearchParams({}, { replace: true });
    }
    const items = directory.data?.items ?? [];
    const total = directory.data?.total ?? 0;
    const pages = Math.max(1, Math.ceil(total / PUBLIC_PAGE_SIZE));
    const first = (page - 1) * PUBLIC_PAGE_SIZE + 1;
    const last = Math.min(page * PUBLIC_PAGE_SIZE, total);
    return (<PublicShell>
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

          <form className="mt-6" onSubmit={submit} role="search">
            <label htmlFor="estate-search" className="block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
              Search by name, suburb or city
            </label>
            {/* One capsule: the field and the action share an edge, so the pair
            reads as a single control rather than two things to line up. */}
            <div className="mt-2 flex max-w-xl">
              <Input id="estate-search" name="q" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Centurion" className="rounded-r-none border-r-0"/>
              <Button type="submit" variant="primary" className="shrink-0 rounded-l-none">
                <IconSearch size={16}/>
                Search
              </Button>
            </div>
          </form>
          <Keyline className="mt-8"/>
        </div>
      </section>

      <section className="mx-auto max-w-[1200px] px-5 py-8">
        {directory.loading ? (<DirectorySkeleton />) : directory.error ? (<ErrorState title={directory.error.status === 503
                ? 'The directory is unavailable right now'
                : 'Could not load the directory'} message={directory.error.message} requestId={directory.error.requestId} action={<Button variant="secondary" onClick={directory.reload}>
                Try again
              </Button>}/>) : items.length === 0 ? (<EmptyState title={submitted ? 'No complex matches that search' : 'No complexes are published yet'} body={submitted
                ? 'Try a different estate name, suburb or city — or clear the search to see everything that is published.'
                : 'When an estate administrator publishes their complex, it appears here with its description and photographs.'} action={submitted ? (<Button variant="secondary" onClick={clear}>
                  Clear the search
                </Button>) : undefined}/>) : (<>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
              <p className="num text-[12.5px] text-ink-muted">
                showing {first}–{last} of {total} published {total === 1 ? 'complex' : 'complexes'}
                {submitted ? ` matching “${submitted}”` : ''}
              </p>
              {submitted ? (<button type="button" onClick={clear} className="text-[12.5px] font-medium text-accent-ink hover:underline">
                  Clear
                </button>) : null}
            </div>

            <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (<EstateCard key={item.estate_id} item={item}/>))}
            </ul>

            {pages > 1 ? (<div className="mt-8 flex items-center justify-between gap-3 border-t border-ink/15 pt-4">
                <p className="num text-[12px] text-ink-muted">
                  page {page} of {pages}
                </p>
                <div className="flex gap-2">
                  <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                    Previous
                  </Button>
                  <Button variant="secondary" disabled={page >= pages} onClick={() => setPage((current) => current + 1)}>
                    Next
                  </Button>
                </div>
              </div>) : null}
          </>)}
      </section>
    </PublicShell>);
}
