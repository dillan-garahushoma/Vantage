import { Link } from 'react-router-dom';
import { Wordmark } from './Brand';
import { IconArrowLeft, IconCheck } from './Icons';

/**
 * OnboardingShell — A clean, focused layout for the pre-estate-membership journey.
 *
 * Provides a steady progress thread across:
 *   Step 1: Account (Register)
 *   Step 2: Join Estate (Join or RequestAccess)
 *   Step 3: Complete (WelcomeSuccess)
 *
 * Removes sidebar, topbar, and distracting chrome so users focus entirely on the task at hand.
 */
export function OnboardingShell({
  step = 1,
  totalSteps = 3,
  stepLabels = ['Account', 'Join estate', "You're in"],
  title,
  subtitle,
  backTo = null,
  children,
}) {
  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col justify-between">
      {/* Top bar */}
      <header className="border-b border-line bg-surface/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-3.5">
          <Wordmark to="/" />
          {backTo ? (
            <Link
              to={backTo}
              className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-muted transition-colors hover:text-ink"
            >
              <IconArrowLeft size={15} />
              Back
            </Link>
          ) : (
            <Link
              to="/"
              className="text-[13px] font-medium text-ink-muted transition-colors hover:text-ink"
            >
              Cancel
            </Link>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 px-4 py-8 sm:py-12">
        <div className="mx-auto max-w-md">
          {/* Step progress indicator */}
          <div className="mb-8" aria-label={`Step ${step} of ${totalSteps}`}>
            <div className="flex items-center justify-between">
              {Array.from({ length: totalSteps }).map((_, idx) => {
                const stepNum = idx + 1;
                const isCompleted = stepNum < step;
                const isCurrent = stepNum === step;
                const label = stepLabels[idx] ?? `Step ${stepNum}`;

                return (
                  <div key={stepNum} className="flex flex-1 items-center last:flex-none">
                    <div className="flex flex-col items-center">
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full text-[12px] font-bold transition-all ${
                          isCompleted
                            ? 'bg-mint text-white'
                            : isCurrent
                            ? 'bg-accent text-white ring-4 ring-accent-wash shadow-sm'
                            : 'border border-line bg-surface text-ink-muted'
                        }`}
                      >
                        {isCompleted ? <IconCheck size={14} /> : stepNum}
                      </div>
                      <span
                        className={`mt-1.5 text-[10.5px] font-medium uppercase tracking-wider ${
                          isCurrent
                            ? 'text-accent-ink font-semibold'
                            : isCompleted
                            ? 'text-ink-soft'
                            : 'text-ink-muted/70'
                        }`}
                      >
                        {label}
                      </span>
                    </div>

                    {/* Progress track connector line */}
                    {idx < totalSteps - 1 ? (
                      <div className="mx-2 mb-4 h-0.5 flex-1 bg-line overflow-hidden rounded-full">
                        <div
                          className={`h-full transition-all duration-300 ${
                            isCompleted ? 'bg-mint w-full' : 'w-0'
                          }`}
                        />
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Heading */}
          {title ? (
            <div className="mb-6 text-center">
              <h1 className="text-[26px] font-bold tracking-tight text-ink sm:text-[30px]">
                {title}
              </h1>
              {subtitle ? (
                <p className="mt-2 text-[14px] text-ink-soft">{subtitle}</p>
              ) : null}
            </div>
          ) : null}

          {/* Card body */}
          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft sm:p-7">
            {children}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-line py-4 text-center text-[12px] text-ink-muted">
        VALORA · Operational Complex Management
      </footer>
    </div>
  );
}
