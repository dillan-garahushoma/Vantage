import { Link } from 'react-router-dom';
import { Keyline } from './Brand';
import { PublicShell } from './PublicShell';
import { Card } from './ui';

/**
 * AuthShell — the one layout for every account screen.
 *
 * Lifted from the sign-in page, which is where residents arrive first: an
 * eyebrow and a display-serif claim on the left, the form in a card on the
 * right. Register, join, request-access, recovery and the completion screen
 * all render inside it, so moving between them never changes the chrome —
 * only the step thread and the words.
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
      <div className="mx-auto grid max-w-[1040px] gap-10 px-5 py-12 lg:grid-cols-[1fr_1.02fr] lg:items-start lg:py-14">
        <div className="min-w-0">
          {backTo ? (
            <Link
              to={backTo}
              className="mb-5 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-ink-muted transition-colors hover:text-ink"
            >
              <span aria-hidden="true">←</span>
              {backLabel}
            </Link>
          ) : null}

          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">{eyebrow}</p>
          <h1 className="mt-3 font-display text-[34px] leading-[1.08] font-normal tracking-[-0.01em] sm:text-[40px]">
            {title}
          </h1>
          {intro ? <p className="mt-3 max-w-md text-[14.5px] text-ink-soft">{intro}</p> : null}

          {step ? (
            <StepThread step={step} totalSteps={totalSteps} labels={stepLabels} />
          ) : null}

          {points.length > 0 ? (
            <ul className="mt-7 max-w-md space-y-3">
              {points.map(([term, detail]) => (
                <li key={term} className="flex gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rotate-45 bg-accent" aria-hidden="true" />
                  <p className="text-[13px] text-ink-soft">
                    <span className="font-medium text-ink">{term}.</span> {detail}
                  </p>
                </li>
              ))}
            </ul>
          ) : null}

          {aside}
        </div>

        <Card className="min-w-0 self-start p-6">
          {cardTitle ? <h2 className="text-[16px] font-semibold">{cardTitle}</h2> : null}
          <Keyline className={cardTitle ? 'mt-3 mb-5' : 'mb-5'} />
          {children}
          {footer}
        </Card>
      </div>
    </PublicShell>
  );
}

/**
 * The three onboarding steps, kept as a thread rather than a banner: the
 * resident can see the whole journey from the account screen onwards.
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
                      ? 'num flex h-6 w-6 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-white'
                      : 'num flex h-6 w-6 items-center justify-center rounded-full border border-ink/20 bg-surface text-[11px] font-medium text-ink-muted'
                }
              >
                {done ? '✓' : number}
              </span>
              {number < totalSteps ? (
                <span className={`my-1 w-px flex-1 ${done ? 'bg-mint/40' : 'bg-ink/15'}`} aria-hidden="true" />
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
