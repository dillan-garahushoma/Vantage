import { Link } from 'react-router-dom';
import { Keyline } from './Brand';
import { PublicShell } from './PublicShell';
import { Button } from './ui';

/**
 * AuthShell — the one layout for every account screen.
 *
 * A split screen, not a card on a background: the left panel carries page
 * context on paper, the right panel holds the active form on the surface ground,
 * and one hairline divides them. Below `lg` the panels stack, still divided.
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
  progress = null,
  aside = null,
  children,
  footer = null,
}) {
  return (
    <PublicShell>
      {/*
        A true split screen: the claim and the form are two panels with their own
        ground, divided by one hairline. The claim sits directly on paper rather
        than inside a translucent card, which was reading as a box floating over a
        blurred photograph instead of as the page's own left column.
      */}
      <div className="grid min-h-[calc(100vh-64px)] bg-paper lg:grid-cols-2">
        <section className="flex min-w-0 flex-col justify-center border-b border-line px-5 py-10 sm:px-8 lg:border-b-0 lg:px-12 lg:py-16">
          <div className="mx-auto w-full max-w-[480px] lg:mx-0 lg:ml-auto">
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
            <h1 className="mt-3 font-display text-[34px] leading-[1.08] font-normal tracking-[-0.01em] text-ink sm:text-[40px]">
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
          </div>
        </section>

        <section className="flex min-w-0 flex-col justify-center bg-surface px-5 py-10 sm:px-8 lg:border-l lg:border-line lg:px-12 lg:py-16">
          <div className="mx-auto w-full max-w-[480px] lg:mx-0">
            {progress}
            {cardTitle ? (
              <h2 className="text-[16px] font-semibold text-ink">{cardTitle}</h2>
            ) : null}
            {/* With no title above it, a keyline becomes a stray rule floating at
                the top of the panel, so it only appears when it divides something. */}
            {cardTitle || progress ? (
              <Keyline className={cardTitle ? 'mt-3 mb-5' : 'mb-5'} />
            ) : null}
            {children}
            {footer}
          </div>
        </section>
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
