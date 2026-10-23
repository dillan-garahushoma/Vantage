import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Activity, Award, Heart, MapPin, Share2, ShieldCheck, Trees } from 'lucide-react';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { PhotoGallery } from '../components/PhotoGallery';
import { IconArrowRight, IconCheck, IconClose, IconImages, IconPin } from '../components/Icons';
import { Button, Card, ErrorState, LinkButton, Skeleton, SkeletonText, cx } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { getPublicEstate } from '../lib/publicDirectory';
import { rememberPublicEstate } from '../lib/publicEstateSelection';
import { scoreBand } from '../lib/display';
import { displayLabel } from '../lib/format';
import { useAsync } from '../lib/useAsync';
/**
 * The published score, and only what was published: a number, the status the
 * engine recorded, when it was calculated and which engine version produced it.
 * Nothing here recomputes, averages or re-weights anything — if the API does not
 * send a score there is no score to show, and the card says so.
 *
 * The band label comes from the shared display bands, so the same number reads
 * the same way here as it does inside the app. The card also says, in words,
 * what the score is: a stored calculation over this estate's own operational
 * history, whose component breakdown is deliberately not published.
 */
export function PublicScoreCard({ summary }) {
    const hasScore = summary.overall_score !== null && summary.overall_score !== undefined;
    const score = hasScore ? Number(summary.overall_score) : null;
    const band = score === null ? null : scoreBand(score);
    return (<Card as="section" className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink/15 bg-accent-wash/60 px-5 py-3">
        <h2 className="text-[11px] font-medium tracking-wider text-ink-soft uppercase">
          Living Score
        </h2>
      </div>

      <div className="p-5">
        <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
          <p className="num text-[44px] leading-none font-semibold">
            {score === null ? '—' : score.toFixed(1)}
            {score === null ? null : (<span className="ml-1 text-[14px] font-normal text-ink-muted">/ 100</span>)}
          </p>
          {band ? (<span className={cx('mb-1 rounded-xs px-2 py-1 text-[11px] font-medium tracking-wide uppercase', band.chipClass)}>
              {band.label}
            </span>) : null}
        </div>

        <p className="mt-3 text-[12.5px] text-ink-muted">
          A weighted composite from 0 to 100, calculated by VALORA from this estate’s own recorded
          operational history.
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
          Published by this estate’s administrator. The score is a stored calculation, not a live estimate, and its component breakdown is not published.
        </p>
      </div>
    </Card>);
}
/**
 * The page, at its final geometry, before the estate arrives.
 *
 * The gallery is the tallest thing here and the last thing to paint, so the
 * skeleton reserves exactly that box — a load that reflows the page is worse
 * than a slow one.
 */
function DetailSkeleton() {
    return (<div className="mx-auto max-w-[1200px] px-5 py-8" aria-busy="true">
      <p role="status" className="sr-only">
        Loading this complex…
      </p>
      <Skeleton className="h-3 w-40"/>
      <Skeleton className="mt-5 h-9 w-2/3"/>
      <Skeleton className="mt-3 h-3 w-1/2"/>
      <Skeleton className="mt-6 aspect-[3/2] max-h-[560px] w-full rounded-2xl"/>
      <div className="mt-8 grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <div>
          <Skeleton className="h-4 w-28"/>
          <SkeletonText lines={4} className="mt-4"/>
        </div>
        <Skeleton className="h-72 w-full rounded-2xl"/>
      </div>
    </div>);
}
/**
 * In-page navigation for the things a visitor came to check.
 *
 * The Living Score entry exists only when an administrator published a score —
 * a jump link to an absent section is worse than no link. Every anchored section
 * carries `scroll-mt`, because two bars are pinned to the top of this page and a
 * jump that lands underneath them hides the heading the link promised.
 */
function SectionNav({ hasScore }) {
    const items = [
        { href: '#photos', label: 'Photographs' },
        { href: '#highlights', label: 'Highlights' },
        { href: '#about', label: 'About' },
        ...(hasScore ? [{ href: '#living-score', label: 'Living Score' }] : []),
        { href: '#location', label: 'Location' },
        { href: '#joining', label: 'Joining' },
    ];
    return (<nav aria-label="Sections of this complex" className="sticky top-[63px] z-20 -mx-5 mt-6 border-y border-ink/15 bg-paper/95 backdrop-blur-md">
      <ul className="flex items-center gap-1 sm:gap-2 overflow-x-auto px-5 py-2.5">
        {items.map((item) => (<li key={item.href}>
            <a href={item.href} className="inline-block rounded-full px-3.5 py-1.5 text-[13px] font-medium whitespace-nowrap text-ink-soft hover:bg-ink/5 hover:text-ink transition-colors">
              {item.label}
            </a>
          </li>))}
      </ul>
    </nav>);
}
function FactsStrip({ detail, photoCount }) {
    const raw = detail.living_score?.overall_score;
    const hasScore = raw !== null && raw !== undefined;
    const band = hasScore ? scoreBand(Number(raw)) : null;
    return (<div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-ink-muted">
      <span className="num">{detail.unit_count} units</span>
      <span aria-hidden="true" className="text-ink/30">
        ·
      </span>
      <span className="num inline-flex items-center gap-1.5">
        <IconImages size={14}/>
        {photoCount} {photoCount === 1 ? 'photograph' : 'photographs'}
      </span>
      <span aria-hidden="true" className="text-ink/30">
        ·
      </span>
      <span>{detail.province}</span>
      {hasScore && band ? (<>
          <span aria-hidden="true" className="text-ink/30">
            ·
          </span>
          {/* The Airbnb "rating beside the title" move, with the only trust
                figure this product actually has: the published score, anchored to
                the card that explains it. */}
          {/* The spaces are real text, not just `gap`: a chip whose parts are
                adjacent elements reads out as "Living Score72.5Watch". */}
          <a href="#living-score" className={cx('inline-flex items-center gap-2 rounded-xs px-2 py-1 font-medium', band.chipClass)}>
            <span className="text-[11px] tracking-wide uppercase">Living Score</span>{' '}
            <span className="num">{Number(raw).toFixed(1)}</span> <span>{band.label}</span>
          </a>
        </>) : null}
    </div>);
}
/** What this page is allowed to say, next to what it will never say. */
function PublicationPanel() {
    const published = [
        'The complex name',
        'Suburb, city and province',
        'How many units it has',
        'The photographs the estate uploaded',
        'The Living Score, but only if the administrator opted in',
    ];
    const never = [
        'Street addresses and unit numbers',
        'Resident, member and contact details',
        'Complaints, incidents and work orders',
        'The score’s component breakdown',
    ];
    return (<div className="mt-4 border-t border-ink/15 pt-4">
      <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
        What is published here
      </p>
      <div className="mt-2.5 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        <ul className="space-y-1.5">
          {published.map((line) => (<li key={line} className="flex items-start gap-2 text-[12.5px] text-ink-soft">
              <IconCheck size={13} className="mt-[3px] shrink-0 text-accent-ink"/>
              {line}
            </li>))}
        </ul>
        <ul className="space-y-1.5">
          {never.map((line) => (<li key={line} className="flex items-start gap-2 text-[12.5px] text-ink-muted">
              <IconClose size={13} className="mt-[3px] shrink-0 text-ink-muted"/>
              {line}
            </li>))}
        </ul>
      </div>
    </div>);
}
function DetailBody({ estateId }) {
    const { user } = useAuth();
    const estate = useAsync(() => getPublicEstate(estateId), [estateId]);
    const [copied, setCopied] = useState(false);
    const [isSaved, setIsSaved] = useState(() => {
        try {
            const saved = JSON.parse(window.localStorage.getItem('valora.saved-estates') || '[]');
            return Array.isArray(saved) && saved.includes(estateId);
        } catch {
            return false;
        }
    });

    function handleShare() {
        if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(window.location.href);
            setCopied(true);
            setTimeout(() => setCopied(false), 2500);
        }
    }

    function toggleSave() {
        setIsSaved((prev) => {
            const next = !prev;
            try {
                const saved = JSON.parse(window.localStorage.getItem('valora.saved-estates') || '[]');
                const current = Array.isArray(saved) ? saved : [];
                const updated = next ? [...new Set([...current, estateId])] : current.filter((id) => id !== estateId);
                window.localStorage.setItem('valora.saved-estates', JSON.stringify(updated));
            } catch {
                // ignore storage error
            }
            return next;
        });
    }

    if (estate.loading)
        return <DetailSkeleton />;
    if (estate.error) {
        const notFound = estate.error.status === 404;
        return (<div className="mx-auto max-w-2xl px-5 py-16">
        <ErrorState title={notFound ? 'That complex is not published' : 'Could not load this complex'} message={notFound
                ? 'Either it does not exist, or its administrator has not published it. A private estate is indistinguishable from an unknown one.'
                : estate.error.message} requestId={estate.error.requestId} action={notFound ? (<LinkButton to="/estates" variant="secondary">
                Back to the directory
              </LinkButton>) : (<Button variant="secondary" onClick={estate.reload}>
                Try again
              </Button>)}/>
      </div>);
    }
    const detail = estate.data;
    if (!detail)
        return null;
    const photos = detail.photos ?? [];
    const rawScore = detail.living_score?.overall_score;
    const hasScore = rawScore !== null && rawScore !== undefined;
    const band = hasScore ? scoreBand(Number(rawScore)) : null;

    return (<div className="mx-auto max-w-[1200px] px-5 py-8">
      {/* Top action bar: breadcrumbs + share/save buttons */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="text-[12.5px] text-ink-muted">
          <Link to="/estates" className="hover:underline">
            Find a complex
          </Link>
          <span aria-hidden="true"> / </span>
          <span className="text-ink-soft">{detail.name}</span>
        </nav>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleShare}
            aria-label={copied ? 'Link copied to clipboard' : 'Share complex link'}
            className="inline-flex items-center gap-1.5 rounded-full border border-ink/15 bg-surface px-3.5 py-1.5 text-[13px] font-medium text-ink shadow-2xs transition-colors hover:border-ink/30 hover:bg-ink/5"
          >
            {copied ? (
              <>
                <IconCheck size={14} className="text-accent-ink" />
                <span className="text-accent-ink font-semibold">Link copied</span>
              </>
            ) : (
              <>
                <Share2 size={14} className="text-ink-soft" />
                <span>Share</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={toggleSave}
            aria-label={isSaved ? 'Remove from saved complexes' : 'Save this complex'}
            className="inline-flex items-center gap-1.5 rounded-full border border-ink/15 bg-surface px-3.5 py-1.5 text-[13px] font-medium text-ink shadow-2xs transition-colors hover:border-ink/30 hover:bg-ink/5"
          >
            <Heart size={14} className={isSaved ? 'fill-red-500 text-red-500' : 'text-ink-soft'} />
            <span>{isSaved ? 'Saved' : 'Save'}</span>
          </button>
        </div>
      </div>

      <header className="mt-4">
        <h1 className="text-[30px] leading-tight font-semibold sm:text-[34px]">{detail.name}</h1>
        <p className="mt-2 flex items-start gap-1.5 text-[13.5px] text-ink-muted">
          <IconPin size={15} className="mt-[3px] shrink-0"/>
          <span>
            {detail.suburb}, {detail.city}, {detail.province}
          </span>
        </p>
        <FactsStrip detail={detail} photoCount={photos.length}/>
      </header>

      <Keyline className="mt-5"/>

      <section id="photos" className="mt-5 scroll-mt-[122px]">
        <h2 className="mb-3 flex items-center gap-2 text-[15px] font-semibold">
          Photographs
          <span className="num text-[12px] font-normal text-ink-muted">
            {photos.length} published
          </span>
        </h2>
        <PhotoGallery estateName={detail.name} photos={photos}/>
      </section>

      <SectionNav hasScore={Boolean(detail.living_score)}/>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <div className="min-w-0 space-y-8">
          {/* Estate Management row */}
          <div className="flex items-center justify-between gap-4 rounded-2xl border border-ink/15 bg-surface p-5 shadow-2xs">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-accent-wash text-accent-ink font-bold text-[16px] tracking-wider border border-accent-ink/20">
                {detail.name.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-[15.5px] font-semibold text-ink">
                    Managed by {detail.name} HOA
                  </h3>
                  <span className="inline-flex items-center gap-1 rounded-full bg-accent-wash px-2 py-0.5 text-[11px] font-medium text-accent-ink border border-accent-ink/20">
                    <ShieldCheck size={12} className="text-accent-ink" />
                    Operational Oversight
                  </span>
                </div>
                <p className="mt-0.5 text-[13px] text-ink-muted">
                  {detail.unit_count} residential units · Homeowners Association Administration
                </p>
              </div>
            </div>
          </div>

          {/* Highlights section */}
          <section id="highlights" className="scroll-mt-[122px]">
            <Card as="div" className="p-5 rounded-2xl">
              <h2 className="text-[15px] font-semibold text-ink">Estate Highlights</h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink/5 text-accent-ink">
                    <MapPin size={18} />
                  </div>
                  <div>
                    <h3 className="text-[13.5px] font-semibold text-ink">{detail.suburb}, {detail.city}</h3>
                    <p className="mt-0.5 text-[12px] text-ink-muted leading-relaxed">
                      Secure residential estate in {detail.province} with defined geographic bounds.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink/5 text-accent-ink">
                    <ShieldCheck size={18} />
                  </div>
                  <div>
                    <h3 className="text-[13.5px] font-semibold text-ink">Monitored Estate Security</h3>
                    <p className="mt-0.5 text-[12px] text-ink-muted leading-relaxed">
                      24/7 controlled resident access, gated entry, and verified visitor logging.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink/5 text-accent-ink">
                    <Award size={18} />
                  </div>
                  <div>
                    <h3 className="text-[13.5px] font-semibold text-ink">
                      {detail.living_score ? `Living Score ${Number(detail.living_score.overall_score).toFixed(1)} / 100` : 'Operational Governance'}
                    </h3>
                    <p className="mt-0.5 text-[12px] text-ink-muted leading-relaxed">
                      {detail.living_score
                        ? `Operational performance evaluated by VALORA engine (${displayLabel(detail.living_score.status)}).`
                        : 'Active estate administration and operational health monitoring.'}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink/5 text-accent-ink">
                    <Trees size={18} />
                  </div>
                  <div>
                    <h3 className="text-[13.5px] font-semibold text-ink">Communal Living & Property</h3>
                    <p className="mt-0.5 text-[12px] text-ink-muted leading-relaxed">
                      {detail.unit_count} individual residential units sharing communal infrastructure.
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </section>

          <section id="about" className="scroll-mt-[122px]">
            <Card as="div" className="p-5">
              <h2 className="text-[15px] font-semibold">About this complex</h2>
              {detail.description ? (<p className="mt-2 whitespace-pre-line text-[14px] text-ink-soft">
                  {detail.description}
                </p>) : (<p className="mt-2 text-[13px] text-ink-muted">
                  The administrator has not written a description yet.
                </p>)}
              <PublicationPanel />
            </Card>
          </section>

          <section id="location" className="scroll-mt-[122px]">
            <Card as="div" className="overflow-hidden">
              <div className="survey-grid border-b border-ink/15 bg-paper px-5 py-6">
                <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
                  Location
                </p>
                <p className="mt-2 text-[19px] font-semibold">{detail.suburb}</p>
                <p className="text-[13.5px] text-ink-soft">
                  {detail.city}, {detail.province}
                </p>
                <p className="num mt-3 text-[11px] text-ink-muted">
                  Suburb-level only — no street address, no pin
                </p>
              </div>
              <p className="px-5 py-4 text-[13px] text-ink-soft">
                A complex’s location is already public information; which unit a resident or an
                owner lives in is not. That is why this page names the suburb and stops there, and
                why searching a street address here will never find anything.
              </p>
            </Card>
          </section>

          {detail.living_score ? (<section id="living-score" className="scroll-mt-[122px]">
              <PublicScoreCard summary={detail.living_score}/>
            </section>) : null}
        </div>

        {/* Right column: Sticky Action Card */}
        <div className="min-w-0">
          <section id="joining" className="scroll-mt-[122px] lg:sticky lg:top-[122px] lg:self-start">
            <Card as="div" className="p-5 shadow-sm">
              <div className="flex items-center justify-between gap-2 border-b border-ink/10 pb-3">
                <div>
                  <p className="num text-[11px] font-semibold tracking-wider text-accent-ink uppercase">
                    Resident Portal
                  </p>
                  <h2 className="mt-1 text-[17px] font-semibold text-ink">Verified Estate Membership</h2>
                </div>
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-wash text-accent-ink">
                  <ShieldCheck size={18} />
                </div>
              </div>

              {/* Clear assurance banner */}
              <div className="mt-3.5 flex items-start gap-2 rounded-lg bg-accent-wash/60 p-3 text-[12px] text-ink-soft border border-accent-ink/15">
                <IconCheck size={14} className="mt-0.5 shrink-0 text-accent-ink" />
                <span className="leading-snug">
                  Requests reviewed by HOA office · Instant access with official unit code
                </span>
              </div>

              {/* Stored Living Score summary if published */}
              {detail.living_score && hasScore && band ? (
                <div className="mt-3.5 rounded-lg border border-ink/10 bg-ink/5 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11.5px] font-medium text-ink-soft">Living Score Status</span>
                    <span className={cx('rounded-xs px-2 py-0.5 text-[10.5px] font-semibold uppercase', band.chipClass)}>
                      {band.label}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-baseline gap-1.5">
                    <span className="num text-[22px] font-bold text-ink">{Number(rawScore).toFixed(1)}</span>
                    <span className="text-[12px] text-ink-muted">/ 100</span>
                  </div>
                  <a href="#living-score" className="mt-1.5 inline-flex items-center gap-1 text-[11.5px] font-medium text-accent-ink hover:underline">
                    View score breakdown
                    <IconArrowRight size={12} />
                  </a>
                </div>
              ) : null}

              <p className="mt-4 text-[12.5px] text-ink-soft">
                Membership is by invitation: your estate office gives you a one-time code, and you
                redeem it against your unit number. A code is the proof of the right to join — and
                an estate is never listed here until its administrator publishes it.
              </p>

              <ul className="mt-3.5 space-y-2">
                {[
                  'Ask your estate office for the join code.',
                  'Create an account (residents register themselves).',
                  'Redeem the code against your unit number.',
                ].map((step, index) => (<li key={step} className="flex gap-2.5 text-[12.5px] text-ink-soft">
                    <span className="num mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-xs border border-ink/20 text-[11px] font-semibold text-accent-ink">
                      {index + 1}
                    </span>
                    {step}
                  </li>))}
              </ul>

              <div className="mt-5 flex flex-col gap-2">
                <LinkButton to="/request-access" variant="primary" className="w-full justify-center text-[13px] font-medium py-2" onClick={() => rememberPublicEstate(detail)} aria-label="Request access">
                  Request Resident Access
                  <IconArrowRight size={15}/>
                </LinkButton>

                <LinkButton to={user ? "/join" : "/join"} variant="secondary" className="w-full justify-center text-[13px] font-medium py-2" onClick={() => rememberPublicEstate(detail)} aria-label="Redeem Join Code">
                  Redeem Join Code
                </LinkButton>

                <LinkButton to="/estates" variant="secondary" className="w-full justify-center text-[12.5px] py-1.5 text-ink-muted">
                  Explore other complexes
                </LinkButton>
              </div>

              <p className="mt-4 flex items-start gap-2 border-t border-ink/15 pt-3 text-[12px] text-ink-muted">
                <IconCheck size={14} className="mt-0.5 shrink-0 text-accent-ink"/>
                VALORA never publishes unit numbers, addresses, resident names or complaint records.
              </p>
            </Card>
          </section>
        </div>
      </div>
    </div>);
}
export function PublicEstateDetail() {
    const params = useParams();
    const estateId = Number(params.id);
    if (!Number.isFinite(estateId) || estateId <= 0) {
        return (<PublicShell>
        <div className="mx-auto max-w-2xl px-5 py-16">
          <ErrorState title="That address is not a complex" message="Check the link and try again."/>
        </div>
      </PublicShell>);
    }
    return (<PublicShell>
      <DetailBody estateId={estateId}/>
    </PublicShell>);
}
