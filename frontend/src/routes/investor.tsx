import { createFileRoute } from "@tanstack/react-router";
import { Info, Search } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ReTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DashboardShell } from "@/components/vantage/DashboardShell";
import { LivingScoreGauge } from "@/components/vantage/LivingScoreGauge";
import {
  LIVING_SCORE,
  estate,
  roiProjection,
  scoreBreakdown,
  scoreTrend,
} from "@/lib/vantage-data";

export const Route = createFileRoute("/investor")({
  head: () => ({
    meta: [
      { title: "Investor Dashboard | VANTAGE" },
      {
        name: "description",
        content:
          "AI valuations, explainable Living Score breakdowns, complaint trend analysis and 10-year ROI projections for managed estates.",
      },
      { property: "og:title", content: "Investor Dashboard | VANTAGE" },
      {
        property: "og:description",
        content: "Data-driven property decisions backed by real community health metrics.",
      },
    ],
  }),
  component: InvestorDashboard,
});

const chartTooltip = {
  contentStyle: {
    background: "var(--color-card)",
    border: "1px solid var(--color-border)",
    borderRadius: "10px",
    fontSize: "12px",
    color: "var(--color-card-foreground)",
  },
};

function InvestorDashboard() {
  return (
    <DashboardShell
      role="Investor"
      title={`${estate.name} · ${estate.suburb}`}
      subtitle="Valuation and yield adjusted for how the estate is actually run. Hover any factor to see why the score is what it is."
    >
      <TooltipProvider delayDuration={120}>
        <div className="space-y-6">
          {/* Search + profile */}
          <Card className="flex flex-wrap items-center gap-3 border-border/70 p-4">
            <div className="flex flex-1 items-center gap-2 rounded-lg bg-secondary px-3 py-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search another estate, address or suburb"
                className="border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
                aria-label="Search properties"
              />
            </div>
            <Button>Search</Button>
          </Card>

          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                {[
                  { label: "AI valuation", value: estate.valuation, sub: estate.valuationDelta },
                  { label: "Rental yield", value: estate.rentalYield, sub: "Suburb median 5.6%" },
                  { label: "10-yr ROI", value: "+96%", sub: "vs +45% suburb baseline" },
                ].map((s) => (
                  <Card key={s.label} className="card-hover border-border/70 bg-gradient-surface p-5">
                    <p className="text-xs uppercase tracking-widest text-muted-foreground">{s.label}</p>
                    <p className="mt-2 font-display text-2xl font-bold text-foreground">{s.value}</p>
                    <p className="mt-1 text-xs text-success">{s.sub}</p>
                  </Card>
                ))}
              </div>

              {/* Breakdown */}
              <Card className="border-border/70 p-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-foreground">Living Score breakdown</h2>
                  <Badge variant="secondary">90-day rolling</Badge>
                </div>
                <div className="mt-5 space-y-5">
                  {scoreBreakdown.map((f) => (
                    <div key={f.label}>
                      <div className="flex items-center justify-between text-sm">
                        <Tooltip>
                          <TooltipTrigger className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                            {f.label}
                            <Info className="h-3.5 w-3.5" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">{f.why}</TooltipContent>
                        </Tooltip>
                        <span className="font-semibold text-foreground">
                          {f.value}
                          <span className="ml-2 text-xs font-normal text-muted-foreground">
                            weight {f.weight}
                          </span>
                        </span>
                      </div>
                      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-gradient-accent transition-all duration-700"
                          style={{ width: `${f.value}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Trends */}
              <div className="grid gap-6 xl:grid-cols-2">
                <Card className="border-border/70 p-6">
                  <h2 className="text-sm font-semibold text-foreground">Living Score trend</h2>
                  <div className="mt-4 h-56">
                    <ResponsiveContainer width="100%" height="100%" debounce={0} minWidth={0}>
                      <AreaChart data={scoreTrend}>
                        <defs>
                          <linearGradient id="scoreArea" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.35} />
                            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                        <XAxis dataKey="month" stroke="var(--color-muted-foreground)" fontSize={11} />
                        <YAxis domain={[50, 100]} stroke="var(--color-muted-foreground)" fontSize={11} />
                        <ReTooltip {...chartTooltip} />
                        <Area
                          type="monotone"
                          dataKey="score"
                          stroke="var(--color-primary)"
                          strokeWidth={2.5}
                          fill="url(#scoreArea)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                <Card className="border-border/70 p-6">
                  <h2 className="text-sm font-semibold text-foreground">Complaints per month</h2>
                  <div className="mt-4 h-56">
                    <ResponsiveContainer width="100%" height="100%" debounce={0} minWidth={0}>
                      <BarChart data={scoreTrend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                        <XAxis dataKey="month" stroke="var(--color-muted-foreground)" fontSize={11} />
                        <YAxis stroke="var(--color-muted-foreground)" fontSize={11} />
                        <ReTooltip {...chartTooltip} />
                        <Bar dataKey="complaints" fill="var(--color-chart-2)" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>

              {/* ROI */}
              <Card className="border-border/70 p-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-foreground">
                    10-year value projection ($100k units)
                  </h2>
                  <span className="text-xs text-muted-foreground">
                    Score-adjusted vs suburb baseline
                  </span>
                </div>
                <div className="mt-4 h-64">
                  <ResponsiveContainer width="100%" height="100%" debounce={0} minWidth={0}>
                    <LineChart data={roiProjection}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                      <XAxis dataKey="year" stroke="var(--color-muted-foreground)" fontSize={11} />
                      <YAxis stroke="var(--color-muted-foreground)" fontSize={11} />
                      <ReTooltip {...chartTooltip} />
                      <Line
                        type="monotone"
                        dataKey="value"
                        name="Riverbend"
                        stroke="var(--color-primary)"
                        strokeWidth={3}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="benchmark"
                        name="Suburb"
                        stroke="var(--color-chart-4)"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>

            <aside className="space-y-6">
              <Card className="border-border/70 p-6">
                <div className="flex justify-center">
                  <LivingScoreGauge score={LIVING_SCORE} size={190} />
                </div>
                <p className="mt-3 text-center text-xs text-muted-foreground">
                  Top 12% of estates in {estate.suburb}.
                </p>
              </Card>

              <Card className="border-border/70 bg-gradient-hero p-6">
                <p className="text-xs uppercase tracking-widest text-ink-foreground/60">
                  Why this valuation
                </p>
                <ul className="mt-3 space-y-2 text-sm text-ink-foreground/85">
                  <li>+2.1% from resolution times under 3 days</li>
                  <li>+1.4% from zero security incidents in 90 days</li>
                  <li>-0.6% from complaint frequency above suburb median</li>
                </ul>
              </Card>

              <Card className="border-border/70 p-6">
                <h2 className="text-sm font-semibold text-foreground">Watchlist</h2>
                <div className="mt-3 space-y-3">
                  {[
                    { name: "Sunridge Park", score: 74 },
                    { name: "Willowmead Estate", score: 66 },
                    { name: "Kingsley Gardens", score: 58 },
                  ].map((w) => (
                    <div key={w.name} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{w.name}</span>
                      <Badge variant="secondary">{w.score}</Badge>
                    </div>
                  ))}
                </div>
              </Card>
            </aside>
          </div>
        </div>
      </TooltipProvider>
    </DashboardShell>
  );
}
