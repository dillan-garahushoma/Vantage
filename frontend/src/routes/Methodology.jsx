import { Link } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { LivingScoreFactors } from '../components/LivingScore';
import { PublicShell } from '../components/PublicShell';
import { IconArrowRight } from '../components/Icons';

export function Methodology() {
  return (
    <PublicShell>
      <div className="mx-auto max-w-[820px] px-5 py-14">
        {/* Breadcrumb */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-[13px] text-ink-muted transition-colors hover:text-ink"
        >
          ← Back to VALORA
        </Link>

        {/* Header */}
        <p className="mt-8 num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
          Living Score · Methodology
        </p>
        <h1 className="mt-3 text-[34px] font-semibold leading-tight tracking-tight sm:text-[42px]">
          How the Living Score is calculated
        </h1>
        <p className="mt-4 max-w-2xl text-[15px] text-ink-soft leading-relaxed">
          The Living Score is a weighted composite index from 0 to 100, recalculated per estate
          over a rolling 90-day window. It is deliberately explainable: a number without its
          contributing factors is marketing, not intelligence.
        </p>

        <Keyline className="my-10" />

        {/* Five pillars */}
        <h2 className="text-[22px] font-semibold text-ink">The five weighted pillars</h2>
        <p className="mt-2 text-[14px] text-ink-soft">
          Each pillar measures a distinct dimension of estate management quality. The weights are
          fixed — they do not change per estate or per time period.
        </p>
        <div className="mt-6">
          <LivingScoreFactors />
        </div>

        <Keyline className="my-10" />

        {/* Calculation rules */}
        <h2 className="text-[22px] font-semibold text-ink">Calculation rules</h2>
        <ol className="mt-4 space-y-4">
          {[
            'A score requires measured pillars covering at least 50% of the total weight. Pillars without sufficient evidence are excluded and the backend normalises the remaining weights. Below that coverage, the result is "Insufficient data", not zero.',
            'The engine runs over a rolling 90-day window. Data older than 90 days does not contribute to the current score.',
            'Recalculation creates a new stored snapshot. Existing snapshots remain unchanged, whether recalculation is requested by a manager or an operator.',
            'Resolution times, incident frequency, provider ratings and satisfaction signals feed their respective pillars — never into each other\'s weight.',
          ].map((rule, i) => (
            <li key={i} className="flex gap-4">
              <span className="num mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-wash text-[11px] font-bold text-accent-ink">
                {i + 1}
              </span>
              <p className="text-[14px] text-ink-soft leading-relaxed">{rule}</p>
            </li>
          ))}
        </ol>

        <p className="mt-8 text-[12.5px] text-ink-muted border-t border-line pt-5">
          Living Score engine v1.0.0 uses deterministic rules over recorded estate activity.
          AI assistance does not calculate or change the score. Historical snapshots keep their recorded engine version.
        </p>

        <Keyline className="my-10" />

        {/* CTA */}
        <div className="flex flex-wrap items-center gap-4">
          <Link
            to="/register"
            className="inline-flex items-center gap-2 rounded-xs bg-accent px-5 py-2.5 text-[13.5px] font-medium text-white transition-opacity hover:opacity-90"
          >
            Get started as a resident
            <IconArrowRight size={15}/>
          </Link>
          <Link to="/" className="text-[13.5px] text-ink-muted hover:text-ink hover:underline">
            ← Back to VALORA
          </Link>
        </div>
      </div>
    </PublicShell>
  );
}
