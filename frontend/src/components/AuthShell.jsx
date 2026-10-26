import { Link } from 'react-router-dom';
import { Keyline } from './Brand';
import { PublicShell } from './PublicShell';
import { Button } from './ui';

/**
 * AuthShell — the one layout for every account screen.
 *
 * One accessible form column beside an explicitly illustrative architectural
 * panel. All role-specific onboarding fields and actions remain in the caller.
 *
 * `aside` is the left column's extra content (the resident's request history,
 * for instance); `footer` sits under the form inside the card.
 */
export function AuthShell({
  eyebrow,
  title,
  intro,
  points = [],
  step = null,
  totalSteps = 3,
  stepLabels = ['Account', 'Join estate', "You're in"],
  backTo = null,
  backLabel = 'Back',
  cardTitle = null,
  aside = null,
  children,
  footer = null,
}) {
  return (
    <PublicShell>
      <div className="min-h-[calc(100vh-64px)] bg-paper px-4 py-6 sm:px-6 sm:py-10">
        <div className="mx-auto grid max-w-[1080px] overflow-hidden rounded-2xl border border-line bg-surface shadow-soft lg:grid-cols-[1.1fr_0.9fr]">
          <section className="min-w-0 px-6 py-8 sm:px-12 sm:py-10">
            {backTo ? (
              <Link
                to={backTo}
                className="mb-5 inline-flex min-h-11 items-center gap-1.5 text-[13px] font-medium text-ink-soft transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                <span aria-hidden="true">←</span>
                {backLabel}
              </Link>
            ) : null}

            <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">{eyebrow}</p>
            <h1 className="mt-3 font-heading text-[28px] leading-tight font-semibold tracking-tight text-ink sm:text-[32px]">
              {title}
            </h1>
            {intro ? (
              <p className="mt-3 max-w-md text-[14.5px] leading-6 text-ink-soft">{intro}</p>
            ) : null}

            {step ? (
              <StepThread step={step} totalSteps={totalSteps} labels={stepLabels} />
            ) : null}

            {points.length > 0 ? (
              <ul className="mt-7 max-w-md space-y-3">
                {points.map(([term, detail]) => (
                  <li key={term} className="flex gap-3">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rotate-45 bg-accent" aria-hidden="true" />
                    <p className="text-[13px] leading-5 text-ink-soft">
                      <span className="font-medium text-ink">{term}.</span> {detail}
                    </p>
                  </li>
                ))}
              </ul>
            ) : null}

            {aside}
            <div className="mt-6 min-w-0">
              {cardTitle ? (
                <h2 className="text-[16px] font-semibold text-ink">{cardTitle}</h2>
              ) : null}
              <Keyline className={cardTitle ? 'mt-3 mb-5' : 'mb-5'} />
              {children}
              {footer}
            </div>
          </section>
          <aside className="relative hidden min-h-[620px] overflow-hidden bg-brand-wash lg:block" aria-label="About VALORA">
            <img src="/estate-hero.jpg" alt="Illustrative residential architecture" className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#241532]/90 via-[#241532]/5 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 p-9 text-white">
              <p className="text-[11px] font-medium tracking-[0.15em] text-white/75 uppercase">Made for your community</p>
              <h2 className="mt-3 max-w-xs font-heading text-3xl font-semibold leading-tight text-white">More than a home.<br />A connected community.</h2>
              <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/80">Report an issue. Follow the repair. Stay informed about the place you call home.</p>
              <p className="mt-8 text-[11px] text-white/65">Illustrative architecture · your estate appears after sign-in.</p>
            </div>
          </aside>
        </div>
      </div>
    </PublicShell>
  );
}

export function SignedInAccountActions({ user, onSwitch, continueTo = '/welcome' }) {
  const account = user?.email || user?.full_name || 'your account';

  return (
    <div className="space-y-4">
      <p role="status" className="rounded-sm bg-accent-wash px-3 py-3 text-[13px] text-accent-ink">
        Signed in as <span className="font-medium">{account}</span>
      </p>
      <Link
        to={continueTo}
        className="flex min-h-11 items-center justify-center rounded-sm bg-accent px-4 py-2.5 text-center text-[14px] font-medium text-white transition-colors hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Continue to workspace
      </Link>
      <Button
        type="button"
        variant="secondary"
        className="w-full min-h-11"
        onClick={onSwitch}
      >
        Sign out and switch accounts
      </Button>
    </div>
  );
}

/**
 * The onboarding steps, kept as a thread rather than a banner.
 */
function StepThread({ step, totalSteps, labels }) {
  return (
    <ol className="mt-7 max-w-md" aria-label={`Step ${step} of ${totalSteps}`}>
      {Array.from({ length: totalSteps }).map((_, index) => {
        const number = index + 1;
        const done = number < step;
        const current = number === step;
        return (
          <li key={number} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={
                  done
                    ? 'num flex h-6 w-6 items-center justify-center rounded-full bg-mint text-[11px] font-semibold text-white'
                    : current
                      ? 'num flex h-6 w-6 items-center justify-center rounded-full bg-brand-soft text-[11px] font-semibold text-white'
                      : 'num flex h-6 w-6 items-center justify-center rounded-full border border-line bg-surface text-[11px] font-medium text-ink-muted'
                }
              >
                {done ? '✓' : number}
              </span>
              {number < totalSteps ? (
                <span
                  className={`my-1 w-px flex-1 ${done ? 'bg-mint/40' : 'bg-line'}`}
                  aria-hidden="true"
                />
              ) : null}
            </div>
            <p
              className={
                current
                  ? 'pb-4 text-[12.5px] font-medium text-ink'
                  : done
                    ? 'pb-4 text-[12.5px] text-ink-soft'
                    : 'pb-4 text-[12.5px] text-ink-muted'
              }
            >
              {labels[index] ?? `Step ${number}`}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
