import { PreviewNotice } from '../components/valora/PreviewNotice';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, } from 'recharts';
import { HeartHandshake, MessageSquare, Star, Megaphone } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Surface } from '../components/valora/Surface';
import { ChartCard } from '../components/valora/ChartCard';
import { ChartTooltip } from '../components/valora/ChartTooltip';
import { RequireEstate } from '../components/RequireEstate';
import { useEstateScope } from '../context/EstateContext';
import { communitySentimentTrend, requestsByTheme, satisfactionDrivers, } from '../lib/estateMockData';
function CommunityContent() {
    const { estate } = useEstateScope();
    return (<div className="space-y-6">
      <PreviewNotice detail="Satisfaction, participation and sentiment figures are samples, not a survey of this estate."/>
      {/* Header */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold tracking-[0.18em] text-brand uppercase">
            Resident experience
          </p>
          <h1 className="mt-2 font-heading text-[1.75rem] font-extrabold tracking-[-0.025em] text-ink sm:text-[2rem]">
            Residents rate {estate?.estate_name ?? 'the estate'} 4.4 out of 5
          </h1>
          <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-relaxed text-ink/60">
            Sentiment, operational service themes and resident satisfaction feedback. Individual responses
            remain anonymous and strictly protected.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/app/announcements">
            <Button variant="outline" className="h-11 rounded-full border-line px-5 text-[0.83rem] font-semibold hover:bg-canvas">
              <Megaphone className="mr-2 h-4 w-4"/>
              Announcements
            </Button>
          </Link>
          <Link to="/app/complaints">
            <Button className="h-11 rounded-full bg-ink px-5 text-[0.83rem] font-semibold text-white hover:bg-brand">
              <MessageSquare className="mr-2 h-4 w-4"/>
              Community Requests
            </Button>
          </Link>
        </div>
      </div>

      {/* Top Experience Stats */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              Overall Pulse
            </span>
            <Star className="h-4 w-4 fill-brand text-brand"/>
          </div>
          <p className="num mt-2 font-heading text-[1.6rem] font-extrabold text-ink">4.4 / 5</p>
          <p className="mt-1 text-[0.72rem] font-semibold text-mint">+0.3 over 90 days</p>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              Participation
            </span>
            <HeartHandshake className="h-4 w-4 text-brand"/>
          </div>
          <p className="num mt-2 font-heading text-[1.6rem] font-extrabold text-ink">76%</p>
          <p className="mt-1 text-[0.72rem] text-ink-muted">312 verified resident votes</p>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              First-Time Resolution
            </span>
            <MessageSquare className="h-4 w-4 text-mint"/>
          </div>
          <p className="num mt-2 font-heading text-[1.6rem] font-extrabold text-ink">88.2%</p>
          <p className="mt-1 text-[0.72rem] font-semibold text-mint">Exceeds 85% target</p>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              Active Communications
            </span>
            <Megaphone className="h-4 w-4 text-brand"/>
          </div>
          <p className="num mt-2 font-heading text-[1.6rem] font-extrabold text-ink">4</p>
          <p className="mt-1 text-[0.72rem] text-ink-muted">Published estate notices</p>
        </Surface>
      </div>

      {/* Sentiment Chart & Request Themes */}
      <div className="grid gap-6 xl:grid-cols-3">
        {/* Sentiment Trend */}
        <ChartCard className="xl:col-span-2" title="Resident satisfaction & operational request volume" description="Monthly pulse satisfaction average versus logged maintenance/service requests" height={280} footer="Pulse data is captured on a rolling 30-day window. Higher satisfaction correlates strongly with rapid work order closure.">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={communitySentimentTrend} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="comm-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.22}/>
                  <stop offset="100%" stopColor="#7C3AED" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#EFEBFB" vertical={false}/>
              <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: '#1F1733', opacity: 0.5, fontSize: 11 }}/>
              <YAxis yAxisId="left" domain={[3.5, 5.0]} tickLine={false} axisLine={false} tick={{ fill: '#1F1733', opacity: 0.5, fontSize: 11 }}/>
              <YAxis yAxisId="right" orientation="right" hide domain={[0, 60]}/>
              <Tooltip content={<ChartTooltip formatter={(val, entry) => entry.dataKey === 'score' ? `${Number(val).toFixed(1)} / 5` : `${val} tickets`}/>}/>
              <Area yAxisId="left" type="monotone" dataKey="score" name="Satisfaction" stroke="#7C3AED" strokeWidth={2.4} fill="url(#comm-fill)"/>
              <Area yAxisId="right" type="monotone" dataKey="requests" name="Requests logged" stroke="#A78BFA" strokeWidth={1.8} strokeDasharray="4 4" fill="none"/>
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Requests by Theme */}
        <Surface className="flex flex-col">
          <div className="border-b border-line pb-3">
            <h3 className="font-heading text-[1rem] font-bold text-ink">Service Themes</h3>
            <p className="text-[0.76rem] text-ink-muted">Most common resident inquiries and requests</p>
          </div>

          <div className="mt-4 flex-1 space-y-3.5">
            {requestsByTheme.map((theme) => (<div key={theme.theme} className="space-y-1.5">
                <div className="flex items-center justify-between text-[0.8rem]">
                  <span className="font-semibold text-ink">{theme.theme}</span>
                  <span className="num font-bold text-ink-muted">{theme.percentage}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-line-soft">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${theme.percentage}%` }}/>
                </div>
              </div>))}
          </div>

          <p className="mt-4 border-t border-line pt-3 text-[0.74rem] text-ink-muted">
            Aggregated from open and closed complaints over the last 90 days.
          </p>
        </Surface>
      </div>

      {/* Satisfaction Drivers */}
      <Surface>
        <div className="border-b border-line pb-3">
          <h3 className="font-heading text-[1rem] font-bold text-ink">Key Satisfaction Drivers</h3>
          <p className="text-[0.76rem] text-ink-muted">
            Individual estate touchpoints evaluated by residents in quarterly surveys
          </p>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {satisfactionDrivers.map((driver) => (<div key={driver.driver} className="rounded-xl border border-line p-4 transition-colors hover:bg-canvas">
              <p className="text-[0.84rem] font-semibold text-ink">{driver.driver}</p>
              <div className="mt-3 flex items-baseline justify-between">
                <span className="num font-heading text-[1.25rem] font-extrabold text-ink">
                  {driver.score} / 5
                </span>
                <span className={driver.change.startsWith('+')
                ? 'num text-[0.76rem] font-bold text-mint'
                : 'num text-[0.76rem] font-medium text-ink-muted'}>
                  {driver.change}
                </span>
              </div>
            </div>))}
        </div>
      </Surface>
    </div>);
}
export function Community() {
    return (<RequireEstate>
      <CommunityContent />
    </RequireEstate>);
}
export default Community;
