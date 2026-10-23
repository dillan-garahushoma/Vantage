import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { Photo, PhotoFallback } from '../components/Photo';
import { IconArrowRight, IconPin, IconSearch } from '../components/Icons';
import { Button, Card, EmptyState, ErrorState, Input, Skeleton, SkeletonText, cx } from '../components/ui';
import { PUBLIC_PAGE_SIZE, listPublicEstates, photoAlt, publicPhotoUrl } from '../lib/publicDirectory';
import { scoreBand } from '../lib/display';
import { useAsync } from '../lib/useAsync';

const PROVINCES = [
  'All',
  'Gauteng',
  'Western Cape',
  'KwaZulu-Natal',
  'Eastern Cape',
  'Free State',
  'Mpumalanga',
  'Limpopo',
  'North West',
  'Northern Cape',
];

/**
 * One published complex, as an Airbnb-inspired card.
 *
 * The photograph is a clean 4:3 box with rounded-2xl styling, an overlaid
 * Living Score badge pill on top-left (when published), and a favorite heart
 * button on top-right.
 *
 * The estate name is the card's only link, stretched over the card with an
 * `::after` overlay so the entire card is clickable while maintaining accessibility.
 */
function EstateCard({ item, isSaved, onToggleSave }) {
    const rawScore = item.living_score?.overall_score;
    const hasScore = rawScore !== null && rawScore !== undefined;
    const score = hasScore ? Number(rawScore) : null;
    const band = score !== null ? scoreBand(score) : null;

    return (<Card as="li" className="group relative flex h-full flex-col overflow-hidden rounded-2xl border border-ink/15 bg-surface transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:border-ink/30">
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-ink/5">
        {hasScore && band ? (<div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 rounded-full bg-surface/90 px-2.5 py-1 text-[11px] font-semibold text-ink shadow-sm backdrop-blur-md border border-ink/10">
            <span className="h-2 w-2 rounded-full bg-accent-ink"/>
            <span>Living Score {score.toFixed(1)}</span>
          </div>) : null}

        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggleSave?.();
          }}
          aria-label={isSaved ? `Remove ${item.name} from saved complexes` : `Save ${item.name} to saved complexes`}
          className="absolute top-3 right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-surface/85 text-ink shadow-sm backdrop-blur-md transition-all hover:scale-110 hover:bg-surface active:scale-95"
        >
          <Heart size={16} className={isSaved ? 'fill-red-500 text-red-500' : 'text-ink-soft hover:text-ink'} />
        </button>

        {item.cover_photo_public_id ? (<Photo src={publicPhotoUrl(item.cover_photo_public_id, 'thumb')} alt={photoAlt(item.name, null)} width={480} height={360} fallbackLabel="No photograph yet" className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"/>) : (<PhotoFallback label="No photograph yet" className="h-full w-full"/>)}
      </div>

      <div className="flex flex-1 flex-col p-5">
        <h2 className="text-[17px] leading-snug font-semibold text-ink transition-colors group-hover:text-accent-ink">
          <Link to={`/estates/${item.estate_id}`} className="after:absolute after:inset-0 after:content-[''] hover:underline">
            {item.name}
          </Link>
        </h2>

        <p className="mt-1.5 flex items-start gap-1.5 text-[12.5px] text-ink-muted">
          <IconPin size={14} className="mt-[2px] shrink-0 text-accent-ink"/>
          <span>
            {item.suburb}, {item.city}, {item.province}
          </span>
        </p>

        {item.description ? (<p className="mt-2.5 line-clamp-2 text-[13px] leading-relaxed text-ink-soft">
            {item.description}
          </p>) : null}

        <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-ink/10">
          <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-accent-ink group-hover:underline">
            <span>Explore complex</span>
            <span className="text-ink/30">·</span>
            <span>View this complex</span>
            <IconArrowRight size={14} className="transition-transform group-hover:translate-x-0.5"/>
          </span>
          <span className="num shrink-0 text-[12.5px] font-medium text-ink-muted">{item.unit_count} units</span>
        </div>
      </div>
    </Card>);
}

/**
 * The grid, at its final geometry, before the data arrives.
 */
function DirectorySkeleton() {
    return (<div aria-busy="true">
      <p role="status" className="sr-only">
        Loading published complexes…
      </p>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => (<div key={index} className="hairline flex flex-col overflow-hidden rounded-2xl bg-surface">
            <Skeleton className="aspect-[4/3] w-full"/>
            <div className="p-5">
              <Skeleton className="h-4 w-2/3"/>
              <Skeleton className="mt-3 h-3 w-1/2"/>
              <SkeletonText lines={2} className="mt-4"/>
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
    const [savedIds, setSavedIds] = useState(() => {
        try {
            const saved = JSON.parse(window.localStorage.getItem('valora.saved-estates') || '[]');
            return Array.isArray(saved) ? saved : [];
        } catch {
            return [];
        }
    });

    const toggleSave = (estateId) => {
        setSavedIds((prev) => {
            const next = prev.includes(estateId) ? prev.filter((id) => id !== estateId) : [...prev, estateId];
            try {
                window.localStorage.setItem('valora.saved-estates', JSON.stringify(next));
            } catch {
                // ignore
            }
            return next;
        });
    };

    const directory = useAsync(() => listPublicEstates({ page, page_size: PUBLIC_PAGE_SIZE, q: submitted }), [page, submitted]);

    function submit(event) {
        event.preventDefault();
        setPage(1);
        const next = query.trim();
        setSubmitted(next);
        setSearchParams(next ? { q: next } : {}, { replace: true });
    }

    function clear() {
        setQuery('');
        setSubmitted('');
        setPage(1);
        setSearchParams({}, { replace: true });
    }

    function selectProvince(prov) {
        setPage(1);
        if (prov === 'All') {
            setQuery('');
            setSubmitted('');
            setSearchParams({}, { replace: true });
        } else {
            setQuery(prov);
            setSubmitted(prov);
            setSearchParams({ q: prov }, { replace: true });
        }
    }

    const items = directory.data?.items ?? [];
    const total = directory.data?.total ?? 0;
    const pages = Math.max(1, Math.ceil(total / PUBLIC_PAGE_SIZE));
    const first = (page - 1) * PUBLIC_PAGE_SIZE + 1;
    const last = Math.min(page * PUBLIC_PAGE_SIZE, total);
    const isAllActive = !submitted || submitted === '';

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
            <div className="mt-2 flex max-w-xl">
              <Input id="estate-search" name="q" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Centurion" className="rounded-r-none border-r-0"/>
              <Button type="submit" variant="primary" className="shrink-0 rounded-l-none">
                <IconSearch size={16}/>
                Search
              </Button>
            </div>
          </form>

          {/* Airbnb-style Province filter pills */}
          <div className="mt-6 flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none" aria-label="Filter complexes by province">
            {PROVINCES.map((prov) => {
              const isActive = prov === 'All' ? isAllActive : submitted.toLowerCase() === prov.toLowerCase();
              return (
                <button
                  key={prov}
                  type="button"
                  onClick={() => selectProvince(prov)}
                  className={cx(
                    'inline-flex items-center rounded-full px-4 py-2 text-[13px] font-medium whitespace-nowrap transition-all duration-150',
                    isActive
                      ? 'bg-ink text-paper shadow-sm'
                      : 'border border-ink/15 bg-surface text-ink-soft hover:border-ink/30 hover:bg-ink/5 hover:text-ink'
                  )}
                >
                  {prov}
                </button>
              );
            })}
          </div>

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
            <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
              <p className="num text-[12.5px] text-ink-muted">
                showing {first}–{last} of {total} published {total === 1 ? 'complex' : 'complexes'}
                {submitted ? ` matching “${submitted}”` : ''}
              </p>
              {submitted ? (<button type="button" onClick={clear} className="text-[12.5px] font-medium text-accent-ink hover:underline">
                  Clear
                </button>) : null}
            </div>

            <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (<EstateCard
                  key={item.estate_id}
                  item={item}
                  isSaved={savedIds.includes(item.estate_id)}
                  onToggleSave={() => toggleSave(item.estate_id)}
                />))}
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
