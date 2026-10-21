import { useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from 'recharts';
import { RequireEstate } from '../components/RequireEstate';
import { Button, ErrorState, LoadingState, SectionTitle, cx } from '../components/ui';
import { LivingScoreFactors, LivingScorePanel } from '../components/LivingScore';
import { HealthPillars } from '../components/valora/HealthPillars';
import { ScoreCard } from '../components/valora/ScoreCard';
import { SectionHeading } from '../components/valora/SectionHeading';
import { Surface } from '../components/valora/Surface';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { getLivingScore, getLivingScoreHistory, recalculateLivingScore } from '../lib/analytics';
import { StatusChip } from '../components/valora/StatusChip';
import { pillarBand } from '../lib/display';
import { ratio, shortDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';
/**
 * Estate health: the full stored Living Score, its pillars and its trajectory.
 *
 * Every figure is read from a snapshot the engine stored. The screen never
 * derives a score, a weight or a trend of its own — the component scores, the
 * published weights, the engine version and the calculation date all come back
 * from `/api/v1/analytics/living-score` exactly as they were written, and the
 * chart is a series of those stored numbers.
 */
function EstateHealthBody() {
    const { estateId, estate, livingScore } = useEstateScope();
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin';
    const snapshot = useAsync(() => (estateId === null ? Promise.resolve(null) : getLivingScore(estateId)), [estateId]);
    const history = useAsync(() => (estateId === null ? Promise.resolve(null) : getLivingScoreHistory(estateId, 24)), [estateId]);
    const [recalculating, setRecalculating] = useState(false);
    const [recalculateError, setRecalculateError] = useState(null);
    async function recalculate() {
        if (estateId === null || recalculating)
            return;
        setRecalculating(true);
        setRecalculateError(null);
        try {
            await recalculateLivingScore(estateId);
            snapshot.reload();
            history.reload();
        }
        catch (cause) {
            setRecalculateError(cause instanceof ApiError
                ? cause
                : new ApiError(0, cause instanceof Error ? cause.message : 'Something went wrong.'));
        }
        finally {
            setRecalculating(false);
        }
    }
    const stored = snapshot.data;
    const scored = stored !== null &&
        stored.status === 'scored' &&
        stored.overall_score !== null &&
        stored.overall_score !== undefined;
    // The pillars the engine published, in its own order and with its own weights.
    const pillars = (stored?.components ?? []).map((component) => ({
        key: component.key,
        name: component.label,
        score: component.score === null || component.score === undefined ? 0 : Number(component.score),
        weight: Number(component.weight) * 100,
        summary: component.explanation || undefined,
        measured: component.status === 'measured' && component.score !== null,
    }));
    const unhealthy = pillars.filter((pillar) => pillar.measured && pillarBand(pillar.score).tone !== 'positive');
    // A trajectory: stored snapshots, oldest first, with their stored dates.
    const trajectory = [...(history.data?.snapshots ?? [])]
        .reverse()
        .filter((row) => row.overall_score !== null)
        .map((row) => ({
        date: shortDate(row.as_of),
        score: Number(row.overall_score),
    }));
    return (<div className="space-y-5">
      <SectionHeading eyebrow="Estate" title="Estate health" description="The stored Living Score for this estate, the five weighted pillars behind it and how it has moved over time." action={isAdmin ? (<Button variant="secondary" onClick={recalculate} disabled={recalculating}>
              {recalculating ? 'Recalculating…' : 'Recalculate now'}
            </Button>) : null}/>

      {snapshot.loading ? (<LoadingState label="Loading the stored Living Score"/>) : snapshot.error && snapshot.error.status !== 404 ? (<ErrorState message={snapshot.error.message} requestId={snapshot.error.requestId} action={<Button variant="secondary" onClick={snapshot.reload}>
              Try again
            </Button>}/>) : (<>
          <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
            <ScoreCard empty={!scored} value={scored ? ratio(stored?.overall_score) : undefined} status={livingScore.label} change={livingScore.trend ?? undefined} spark={livingScore.history} label={`Living Score · ${estate?.estate_name ?? 'this estate'}`} description={scored
                ? `A stored calculation over a rolling 90-day window, produced by engine version ${stored?.engine_version}. It is never recalculated on read, so this figure cannot move on its own.`
                : 'This estate has no publishable score yet: the engine will not publish a number from too little of the estate’s operations.'}/>

            <Surface>
              <SectionTitle title="The five pillars" hint="The engine’s own components, scores and published weights"/>
              {pillars.length > 0 ? (<HealthPillars pillars={pillars} expandedDefault showWeights/>) : (<p className="py-3 text-[0.85rem] text-ink-muted">
                  No pillar breakdown has been stored yet. Each of the factors below begins reporting
                  once the estate has enough operational history.
                </p>)}
            </Surface>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
            <Surface>
              <SectionTitle title="Stored trajectory" hint="Every point is a snapshot the engine wrote, never a value the browser interpolated"/>
              {trajectory.length > 1 ? (<div className="h-[240px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trajectory} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                      <defs>
                        <linearGradient id="healthFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.28}/>
                          <stop offset="100%" stopColor="#7C3AED" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#6B6480' }}/>
                      <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#6B6480' }}/>
                      <ChartTooltip contentStyle={{
                    borderRadius: 12,
                    border: '1px solid #E9E3FF',
                    fontSize: 12,
                    boxShadow: '0 10px 28px -14px rgba(31,23,51,0.12)',
                }}/>
                      <Area type="monotone" dataKey="score" stroke="#7C3AED" strokeWidth={2} fill="url(#healthFill)"/>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>) : (<p className="py-3 text-[0.85rem] text-ink-muted">
                  A trajectory appears once there are at least two stored snapshots to compare. The
                  history endpoint returns what the engine wrote and nothing else.
                </p>)}
            </Surface>

            <Surface>
              <SectionTitle title="What the score weighs" hint="Published model parameters, not a calculation made here"/>
              <LivingScoreFactors />
            </Surface>
          </div>

          <LivingScorePanel snapshot={stored} loading={false} error={null} onRetry={snapshot.reload} onRecalculate={isAdmin ? recalculate : undefined} recalculating={recalculating} recalculateError={recalculateError}/>

          <p className={cx('text-[0.72rem] text-ink/35')}>
            Scope: {estate?.estate_name ?? 'no estate selected'}. The stored snapshot is read once per
            estate and shared with the shell; the recalculate action is the only control here that
            writes, and the server decides who may use it.
          </p>
        </>)}

      {unhealthy.length > 0 ? (<p className="flex flex-wrap items-center gap-2 text-[0.78rem] text-ink/45">
          <StatusChip status="Watch" size="sm"/>
          {unhealthy.length} measured pillar{unhealthy.length === 1 ? '' : 's'} below the healthy band,
          which is why the composite label reads “{livingScore.label}”.
        </p>) : null}
    </div>);
}
export function EstateHealth() {
    return (<RequireEstate>
      <EstateHealthBody />
    </RequireEstate>);
}
