import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { Photo, PhotoFallback } from '../components/Photo';
import { PublicShell } from '../components/PublicShell';
import { IconArrowRight, IconPin, IconSearch, IconShield, IconSparkle, IconStar } from '../components/Icons';
import { Card, Chip, LinkButton, Skeleton } from '../components/ui';
import { listPublicEstates, photoAlt, publicPhotoUrl } from '../lib/publicDirectory';
import { useAsync } from '../lib/useAsync';

const REGIONS = ['All Estates', 'Western Cape', 'Gauteng', 'KwaZulu-Natal'];

const VALUE_CHAIN = [
  {
    step: '01',
    title: 'Residents report what is actually wrong',
    body: 'A burst pipe, a dead streetlight, a gate that will not close. Each complaint is logged with a category, a priority and a timestamp instead of disappearing into a WhatsApp group.',
  },
  {
    step: '02',
    title: 'The HOA resolves it, visibly',
    body: 'Complaints move through a fixed lifecycle — logged, reviewed, assigned, in progress, resolved, rated. Every transition is retained as evidence, so responsiveness is provable rather than claimed.',
  },
  {
    step: '03',
    title: 'Operational data becomes community health',
    body: 'Resolution times, complaint frequency, security incidents, provider performance and resident satisfaction are weighted into one comparable estate-level figure.',
  },
  {
    step: '04',
    title: 'Evidence supports accountable maintenance',
    body: 'The stored record shows what was reported, who acted, how long it took and whether the resident rated the completed repair.',
  },
];

const COMPARISON = [
  ['Which issues need attention now?', 'Scattered messages and emails', 'yes'],
  ['Complaint history and resolution time', 'Emails and meeting minutes', 'yes'],
  ['Maintenance quality and resident ratings', 'Word of mouth', 'yes'],
  ['Security incident frequency', 'Separate incident records', 'yes'],
  ['Resident satisfaction after completed repairs', 'Rarely connected to the repair', 'yes'],
  ['Estate living quality, scored', 'No shared operational measure', 'yes'],
];

function Section({ id, eyebrow, title, intro, children }) {
  return (
    <section id={id} className="mx-auto max-w-[1200px] px-5 py-14">
      <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">{eyebrow}</p>
      <h2 className="mt-3 max-w-2xl text-[26px] leading-tight font-semibold sm:text-[32px]">
        {title}
      </h2>
      {intro ? <p className="mt-3 max-w-2xl text-[15px] text-ink-soft">{intro}</p> : null}
      <div className="mt-8">{children}</div>
    </section>
  );
}

function FeaturedEstates() {
  const [selectedRegion, setSelectedRegion] = useState('All Estates');
  const [savedIds, setSavedIds] = useState(new Set());
  const queryParam = selectedRegion === 'All Estates' ? undefined : selectedRegion;
  const directory = useAsync(
    () => listPublicEstates({ page: 1, page_size: 6, q: queryParam }),
    [selectedRegion]
  );
  const estates = directory.data?.items ?? [];

  const toggleSave = (id, e) => {
    e.preventDefault();
    e.stopPropagation();
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <section aria-labelledby="featured-estates" className="border-y border-ink/15 bg-paper">
      <div className="mx-auto max-w-[1200px] px-5 py-14">
        {/* Header & Category Pills (inspired by Airbnb discovery carousel) */}
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent" />
              <p className="num text-[11px] font-semibold tracking-[0.18em] text-accent-ink uppercase">
                Published complex catalogue
              </p>
            </div>
            <h2 id="featured-estates" className="mt-2 text-[28px] font-semibold tracking-tight sm:text-[34px]">
              Find your residential complex
            </h2>
            <p className="mt-2 max-w-xl text-[14.5px] text-ink-soft">
              Verified South African residential estates with auditable operational records and published Living Scores.
            </p>
          </div>

          <Link
            to={selectedRegion === 'All Estates' ? '/estates' : `/estates?q=${encodeURIComponent(selectedRegion)}`}
            className="inline-flex items-center gap-1.5 text-[13.5px] font-medium text-accent-ink hover:underline"
          >
            Explore full directory <IconArrowRight size={15} />
          </Link>
        </div>

        {/* Region filter pills */}
        <div className="mt-7 flex flex-wrap items-center gap-2">
          {REGIONS.map((region) => (
            <button
              key={region}
              type="button"
              onClick={() => setSelectedRegion(region)}
              className={`rounded-full px-4 py-1.5 text-[13px] font-medium transition-all ${
                selectedRegion === region
                  ? 'bg-ink text-paper shadow-sm'
                  : 'border border-ink/15 bg-surface text-ink-soft hover:border-ink/30 hover:text-ink'
              }`}
            >
              {region}
            </button>
          ))}
        </div>

        {directory.loading ? (
          <div aria-busy="true" className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, index) => (
              <div key={index} className="overflow-hidden rounded-2xl border border-ink/15 bg-surface">
                <Skeleton className="aspect-[4/3] w-full" />
                <div className="p-5">
                  <Skeleton className="h-5 w-2/3" />
                  <Skeleton className="mt-2 h-4 w-1/2" />
                  <Skeleton className="mt-4 h-4 w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : directory.error ? (
          <div className="mt-8 rounded-2xl border border-ink/15 bg-surface p-8 text-center">
            <p className="text-[14.5px] text-ink-soft">
              The public catalogue could not be reached right now.{' '}
              <Link to="/estates" className="font-medium text-accent-ink underline">
                Open directory
              </Link>
              .
            </p>
          </div>
        ) : estates.length === 0 ? (
          <div className="mt-8 rounded-2xl border border-ink/15 bg-surface p-10 text-center">
            <p className="text-[15px] font-medium text-ink">No published complexes in this region yet</p>
            <p className="mt-1.5 text-[13.5px] text-ink-soft">
              Complexes appear here once the HOA administration authorizes their public profile.
            </p>
            <button
              onClick={() => setSelectedRegion('All Estates')}
              className="mt-4 inline-flex items-center gap-2 rounded-xs border border-ink/20 bg-surface px-4 py-2 text-[13px] font-medium text-ink hover:bg-ink/5"
            >
              View all estates
            </button>
          </div>
        ) : (
          <ul
            className={
              estates.length === 1
                ? 'mt-8'
                : 'mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3'
            }
          >
            {estates.map((estate) => {
              const isSaved = savedIds.has(estate.estate_id);
              if (estates.length === 1) {
                // Editorial Featured Single-Estate Card
                return (
                  <li
                    key={estate.estate_id}
                    className="group relative grid overflow-hidden rounded-2xl border border-ink/15 bg-surface shadow-xs transition-shadow hover:shadow-md md:grid-cols-[1.1fr_0.9fr]"
                  >
                    <div className="flex flex-col justify-between p-6 sm:p-8">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center gap-1 rounded-full bg-accent-wash px-2.5 py-0.5 text-[11px] font-semibold tracking-wide text-accent-ink uppercase">
                            <IconSparkle size={12} />
                            Featured Complex
                          </span>
                          <span className="text-[12px] text-ink-muted">· {estate.unit_count} units</span>
                        </div>
                        <h3 className="mt-3 text-[26px] font-semibold tracking-tight sm:text-[32px]">
                          <Link
                            to={`/estates/${estate.estate_id}`}
                            className="after:absolute after:inset-0 after:content-[''] hover:underline"
                          >
                            {estate.name}
                          </Link>
                        </h3>
                        <p className="mt-2 flex items-center gap-1.5 text-[13.5px] text-ink-muted">
                          <IconPin size={15} className="shrink-0 text-accent-ink" />
                          {estate.suburb}, {estate.city}, {estate.province}
                        </p>
                        {estate.description ? (
                          <p className="mt-4 line-clamp-3 text-[14.5px] leading-relaxed text-ink-soft">
                            {estate.description}
                          </p>
                        ) : null}
                      </div>

                      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-ink/10 pt-5">
                        <span className="inline-flex items-center gap-1.5 text-[13.5px] font-semibold text-accent-ink">
                          View complex overview <IconArrowRight size={15} />
                        </span>
                        <span className="rounded-full bg-ink/5 px-3 py-1 text-[12px] font-medium text-ink-soft">
                          HOA Verified
                        </span>
                      </div>
                    </div>

                    <div className="relative min-h-[280px] overflow-hidden bg-ink/5 md:min-h-[360px]">
                      {estate.cover_photo_public_id ? (
                        <Photo
                          src={publicPhotoUrl(estate.cover_photo_public_id, 'thumb')}
                          alt={photoAlt(estate.name, null)}
                          width={600}
                          height={450}
                          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                          fallbackLabel="No photograph yet"
                        />
                      ) : (
                        <PhotoFallback label="No photograph yet" className="h-full" />
                      )}
                      <button
                        type="button"
                        onClick={(e) => toggleSave(estate.estate_id, e)}
                        className="absolute top-4 right-4 z-10 rounded-full bg-surface/90 p-2 text-ink shadow-sm backdrop-blur-xs transition-colors hover:text-red-500"
                        title={isSaved ? 'Saved' : 'Save complex'}
                      >
                        <IconStar size={16} filled={isSaved} />
                      </button>
                    </div>
                  </li>
                );
              }

              // Standard Airbnb-style catalog card
              return (
                <li
                  key={estate.estate_id}
                  className="group relative flex flex-col overflow-hidden rounded-2xl border border-ink/10 bg-surface shadow-xs transition-all duration-200 hover:-translate-y-1 hover:border-ink/25 hover:shadow-lg"
                >
                  {/* Photo container with top overlays */}
                  <div className="relative aspect-[4/3] w-full overflow-hidden bg-ink/5">
                    {estate.cover_photo_public_id ? (
                      <Photo
                        src={publicPhotoUrl(estate.cover_photo_public_id, 'thumb')}
                        alt={photoAlt(estate.name, null)}
                        width={480}
                        height={360}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
                        fallbackLabel="No photograph yet"
                      />
                    ) : (
                      <PhotoFallback label="No photograph yet" className="h-full w-full" />
                    )}

                    {/* Airbnb-style pill badge overlay */}
                    <div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 rounded-full bg-surface/95 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-ink shadow-sm backdrop-blur-xs">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                      <span>Verified Estate</span>
                    </div>

                    {/* Bookmark / save button */}
                    <button
                      type="button"
                      onClick={(e) => toggleSave(estate.estate_id, e)}
                      className="absolute top-3 right-3 z-10 rounded-full bg-surface/90 p-2 text-ink-muted shadow-sm backdrop-blur-xs transition-colors hover:text-red-500"
                      title={isSaved ? 'Saved' : 'Save'}
                    >
                      <IconStar size={15} filled={isSaved} />
                    </button>
                  </div>

                  {/* Body details */}
                  <div className="flex flex-1 flex-col p-5">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-[17px] font-semibold text-ink">
                        <Link
                          to={`/estates/${estate.estate_id}`}
                          className="after:absolute after:inset-0 after:content-[''] hover:underline"
                        >
                          {estate.name}
                        </Link>
                      </h3>
                      <span className="num shrink-0 text-[12px] font-medium text-ink-muted">
                        {estate.unit_count} units
                      </span>
                    </div>

                    <p className="mt-1.5 flex items-center gap-1.5 text-[13px] text-ink-muted">
                      <IconPin size={13} className="shrink-0 text-accent-ink" />
                      <span>
                        {estate.suburb}, {estate.city}
                      </span>
                    </p>

                    {estate.description ? (
                      <p className="mt-3 line-clamp-2 text-[13px] leading-relaxed text-ink-soft">
                        {estate.description}
                      </p>
                    ) : null}

                    <div className="mt-auto flex items-center justify-between gap-3 border-t border-ink/10 pt-4">
                      <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent-ink">
                        View details <IconArrowRight size={14} />
                      </span>
                      <span className="text-[11.5px] text-ink-muted">HOA Oversight</span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

export function Landing() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const handleHeroSearch = (e) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (q) {
      navigate(`/estates?q=${encodeURIComponent(q)}`);
    } else {
      navigate('/estates');
    }
  };

  return (
    <PublicShell>
      {/* ------------------------------------------------------------ hero */}
      <section className="relative isolate flex min-h-[620px] items-center overflow-hidden bg-ink lg:min-h-[min(760px,calc(100svh-72px))]">
        <img
          src="/estate-hero.jpg"
          alt=""
          aria-hidden="true"
          fetchPriority="high"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-ink/60" aria-hidden="true" />
        <div className="relative z-10 mx-auto w-full max-w-[1200px] px-5 py-16 lg:py-20">
          <div className="max-w-[700px]">
            <h1 className="max-w-[680px] text-[40px] leading-[1.04] font-semibold tracking-tight text-white sm:text-[56px]">
              Understand how your complex is being cared for.
            </h1>
            <p className="mt-5 max-w-xl text-[16px] leading-relaxed text-paper/90">
              VALORA turns maintenance, repairs and resident feedback into a clear record of what needs attention and what has changed.
            </p>
            {/* The owner asked for a rounded, see-through search bar, so this control is a
            glass pill rather than the soft-radius surface `DESIGN.md` tiles elsewhere. The
            fill is translucent white over the hero photograph, which is why the text,
            placeholder and icon are white and the focus ring is white rather than violet. */}
            <form onSubmit={handleHeroSearch} className="mt-8 flex min-h-14 max-w-xl items-center gap-3 rounded-full border border-white/25 bg-white/10 p-1.5 pl-5 backdrop-blur-md transition-colors focus-within:border-white/45 focus-within:bg-white/15 focus-within:ring-2 focus-within:ring-white/60">
              <IconSearch size={18} className="shrink-0 text-white/75"/>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search complex, suburb or city"
                aria-label="Search complex, suburb or city"
                className="min-w-0 flex-1 bg-transparent text-[14px] text-white placeholder:text-white/70 focus:outline-none"/>
              {/* Below `sm` the label gives way to the arrow alone: a pill carrying the
              full label left the input about 105px on a 390px phone, which truncated the
              placeholder. `aria-label` keeps the accessible name at every width. */}
              <button
                type="submit"
                aria-label="Find a complex"
                className="flex min-h-11 w-11 shrink-0 items-center justify-center gap-2 rounded-full bg-accent px-0 text-[13px] font-medium text-white transition-colors hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white sm:w-auto sm:px-5"
              >
                <span className="hidden sm:inline">Find a complex</span>
                <IconArrowRight size={16}/>
              </button>
            </form>
            <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13.5px] text-paper">
              <Link to="/estates" className="font-medium underline underline-offset-4 hover:text-white">
                Browse all complexes
              </Link>
              <Link to="/login" className="text-paper/90 hover:text-white hover:underline">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </section>

      <FeaturedEstates />

      {/* ------------------------------------------------------ value chain */}
      <Section
        id="how"
        eyebrow="How the operational record works"
        title="Every feature supports the next maintenance decision"
        intro="VALORA is a management system: what happens in a community becomes measurable health, then evidence for better maintenance decisions."
      >
        <ol className="grid gap-5 md:grid-cols-2">
          {VALUE_CHAIN.map((link) => (
            <li key={link.step}>
              <Card className="h-full rounded-2xl p-6 transition-colors hover:border-ink/25">
                <div className="flex items-center gap-3">
                  <span className="num text-[13px] font-semibold text-accent-ink">{link.step}</span>
                  <span className="h-px flex-1 bg-ink/15" />
                </div>
                <h3 className="mt-3 text-[17px] font-semibold text-ink">{link.title}</h3>
                <p className="mt-2 text-[14px] leading-relaxed text-ink-soft">{link.body}</p>
              </Card>
            </li>
          ))}
        </ol>
      </Section>

      {/* ------ living score teaser ------ */}
      <section className="border-y border-ink/15 bg-surface">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-6 px-5 py-10">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent" />
              <p className="num text-[11px] font-semibold tracking-[0.18em] text-accent-ink uppercase">
                Estate health metric
              </p>
            </div>
            <h2 className="mt-2 text-[24px] font-semibold leading-snug text-ink sm:text-[28px]">
              Every score shows its working
            </h2>
            <p className="mt-2 max-w-xl text-[14.5px] leading-relaxed text-ink-soft">
              The Living Score is a weighted composite from 0–100, built from five operational pillars over a rolling 90-day window. The calculation is deterministic and inspectable.
            </p>
          </div>
          <Link
            to="/methodology"
            className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-ink/20 bg-surface px-5 py-3 text-[13.5px] font-medium text-ink transition-colors hover:border-accent hover:text-accent-ink"
          >
            Read the methodology
            <IconArrowRight size={15} />
          </Link>
        </div>
      </section>

      {/* ------ who it is for: role stories ------ */}
      <Section
        eyebrow="Who uses VALORA"
        title="Built for everyone with a stake in the estate"
      >
        <div className="grid gap-5 sm:grid-cols-3">
          {[
            {
              role: 'Residents',
              tagline: 'Report an issue and watch it move.',
              body: 'Log a maintenance request once. Track it through review, assignment, repair and resident rating — all from one screen.',
              cta: 'Get started as a resident',
              to: '/register',
              primary: true,
            },
            {
              role: 'HOA Administrators',
              tagline: 'One command view for everything.',
              body: 'Complaints, work orders, contractors, announcements and estate health — all managed inside one estate-scoped workspace.',
              cta: 'Contact your estate admin',
              to: '/contact',
              primary: false,
            },
            {
              role: 'Service Providers',
              tagline: 'Apply to work with an estate.',
              body: 'The HOA reviews your application. If approved, you receive a secure account setup link and access to assigned work.',
              cta: 'Apply as a provider',
              to: '/provider/apply',
              primary: false,
            },
          ].map((item) => (
            <Card key={item.role} className="flex flex-col rounded-2xl p-6">
              <p className="num text-[11px] font-semibold tracking-[0.16em] text-accent-ink uppercase">
                {item.role}
              </p>
              <h3 className="mt-2 text-[17px] font-semibold text-ink">{item.tagline}</h3>
              <p className="mt-2 flex-1 text-[13.5px] leading-relaxed text-ink-soft">{item.body}</p>
              <Link
                to={item.to}
                className={
                  item.primary
                    ? 'mt-5 inline-flex items-center gap-1.5 text-[13.5px] font-semibold text-accent-ink hover:underline'
                    : 'mt-5 inline-flex items-center gap-1.5 text-[13.5px] text-ink-muted hover:text-ink'
                }
              >
                {item.cta}
                <IconArrowRight size={14} />
              </Link>
            </Card>
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------------- why different */}
      <section className="border-t border-ink/15 bg-surface">
        <div className="mx-auto max-w-[1200px] px-5 py-14">
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            More than a unit register
          </p>
          <h2 className="mt-3 max-w-2xl text-[26px] leading-tight font-semibold sm:text-[32px]">
            The operational record exists inside the community that runs on it
          </h2>

          {/* Scrolls sideways on phones instead of clipping the "On VALORA" column;
              the table keeps a readable minimum rather than squeezing three
              columns into 320px. */}
          <div className="scrollbar-slim mt-8 overflow-x-auto rounded-2xl border border-ink/15 bg-surface">
            <table className="w-full min-w-[540px] border-collapse text-left text-[13.5px]">
              <thead>
                <tr>
                  <th className="border-b border-ink/15 bg-paper px-5 py-3 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    Operational question
                  </th>
                  <th className="border-b border-ink/15 bg-paper px-5 py-3 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    Without a shared system
                  </th>
                  <th className="border-b border-ink/15 bg-paper px-5 py-3 text-right text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    On VALORA
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map(([question, today, answer]) => (
                  <tr key={question} className="hover:bg-ink/[0.02]">
                    <td className="border-b border-ink/10 px-5 py-3.5 font-medium text-ink">{question}</td>
                    <td className="border-b border-ink/10 px-5 py-3.5 text-ink-muted">{today}</td>
                    <td className="border-b border-ink/10 px-5 py-3.5 text-right">
                      {answer === 'yes' ? (
                        <Chip tone="good" glyph="✓">
                          Visible
                        </Chip>
                      ) : (
                        <Chip tone="alert" glyph="✕">
                          Not visible
                        </Chip>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------- close */}
      <section className="bg-ink text-paper">
        <div className="mx-auto max-w-[1200px] px-5 py-16">
          <Keyline className="opacity-40" />
          <h2 className="mt-6 max-w-2xl text-[28px] leading-tight font-semibold sm:text-[34px]">
            Ready to see your estate's real operational data?
          </h2>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-paper/75">
            Public registration always creates a resident — privileged estate roles are granted
            through an existing membership, never self-selected. If your estate has not been
            provisioned yet, your account will show that it is awaiting approval.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <LinkButton to="/register" variant="primary" className="px-6 py-2.5">
              Get started as a resident
              <IconArrowRight size={17} />
            </LinkButton>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg border border-paper/30 px-6 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-paper/10"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
