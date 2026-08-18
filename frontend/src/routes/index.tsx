import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowRight, Building2, LineChart, Search, ShieldCheck, Sparkles } from "lucide-react";
import heroImage from "@/assets/hero-estate.jpg";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { VantageMark } from "@/components/vantage/DashboardShell";
import { LivingScoreGauge } from "@/components/vantage/LivingScoreGauge";
import { LIVING_SCORE, scoreBreakdown } from "@/lib/vantage-data";
import { KimiPanel } from '@/components/kimi/KimiPanel';

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "VANTAGE — Property Health Intelligence & Living Score" },
      {
        name: "description",
        content:
          "VANTAGE links community operations to property value. Get an AI valuation, a 0-100 Living Score and 10-year ROI insight for any estate.",
      },
      { property: "og:title", content: "VANTAGE — Property Health Intelligence" },
      {
        property: "og:description",
        content:
          "Know more than what a property costs. Know why it's worth it. AI valuations backed by real community health data.",
      },
    ],
  }),
  component: Landing,
});

const pillars = [
  {
    icon: Building2,
    title: "Community Operations",
    body: "Every complaint, work order and resolution is captured with a timestamp.",
  },
  {
    icon: ShieldCheck,
    title: "Community Health",
    body: "Operations roll up into security, maintenance and satisfaction signals.",
  },
  {
    icon: Sparkles,
    title: "Living Score",
    body: "A 90-day rolling 0-100 score that explains itself, factor by factor.",
  },
  {
    icon: LineChart,
    title: "Investment Intelligence",
    body: "Valuation, rental yield and 10-year ROI adjusted for how well an estate is run.",
  },
];

function Landing() {
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <header className="absolute inset-x-0 top-0 z-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6">
          <VantageMark tone="dark" />
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="text-ink-foreground hover:bg-white/10">
              <Link to="/resident">Sign in</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/investor">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative isolate overflow-hidden bg-gradient-hero">
        <img
          src={heroImage}
          alt="Aerial view of a well-managed gated residential estate at dusk"
          width={1600}
          height={1008}
          className="absolute inset-0 h-full w-full object-cover opacity-25"
        />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-4 pb-20 pt-32 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:items-center lg:pb-28 lg:pt-40">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-ink-foreground">
              <Sparkles className="h-3.5 w-3.5" />
              AI Property Health Intelligence
            </span>
            <h1 className="mt-6 text-4xl font-bold leading-[1.05] text-ink-foreground sm:text-5xl lg:text-6xl">
              Know more than what a property costs.
              <span className="block text-accent">Know why it's worth it.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-ink-foreground/75 sm:text-lg">
              VANTAGE measures how an estate is actually run — response times, security,
              maintenance, resident satisfaction — and turns it into a Living Score that moves
              valuations.
            </p>

            <form
              className="mt-8 max-w-xl"
              onSubmit={(e) => {
                e.preventDefault();
                setSearched(query.trim().length > 0);
              }}
            >
              <div className="flex flex-col gap-2 rounded-2xl border border-white/15 bg-card/95 p-2 shadow-elevated sm:flex-row">
                <div className="flex flex-1 items-center gap-2 px-3">
                  <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter an address or suburb"
                    className="border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
                    aria-label="Address or suburb"
                  />
                </div>
                <Button type="submit" size="lg" className="sm:w-auto">
                  Free estimate
                </Button>
              </div>
            </form>

            {searched && (
              <Card className="mt-4 max-w-xl border-border/60 p-5 shadow-card">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-muted-foreground">
                      Estimated value
                    </p>
                    <p className="font-display text-3xl font-bold text-foreground">$398K – $427K</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {query} · confidence 82%
                    </p>
                  </div>
                  <div className="rounded-xl bg-secondary px-4 py-3 text-center">
                    <p className="text-xs uppercase tracking-widest text-muted-foreground">
                      Living Score
                    </p>
                    <p className="font-display text-2xl font-bold text-primary">Locked</p>
                  </div>
                </div>
                <Button asChild className="mt-4 w-full sm:w-auto">
                  <Link to="/investor">
                    Sign up to unlock the Living Score & ROI
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>
              </Card>
            )}
          </div>

          <Card className="border-border/50 bg-card/95 p-7 shadow-elevated backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              Riverbend Estate · Live
            </p>
            <div className="mt-4 flex justify-center">
              <LivingScoreGauge score={LIVING_SCORE} size={210} />
            </div>
            <ul className="mt-5 space-y-3">
              {scoreBreakdown.slice(0, 4).map((f) => (
                <li key={f.label}>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="text-muted-foreground">{f.label}</span>
                    <span className="font-semibold text-foreground">{f.value}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-gradient-accent transition-all duration-700"
                      style={{ width: `${f.value}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <KimiPanel />
      </section>
 
      {/* Chain of value */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <h2 className="max-w-2xl text-3xl font-bold text-foreground sm:text-4xl">
          A well-managed estate is a more valuable estate.
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          VANTAGE follows one chain — and shows you every link of it.
        </p>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {pillars.map(({ icon: Icon, title, body }, i) => (
            <Card key={title} className="card-hover border-border/70 bg-gradient-surface p-6">
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-secondary text-primary">
                  <Icon className="h-4.5 w-4.5" />
                </span>
                <span className="text-xs font-semibold text-muted-foreground">
                  0{i + 1}
                </span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-foreground">{title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{body}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Roles */}
      <section className="border-y border-border bg-secondary/50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <h2 className="text-3xl font-bold text-foreground">Built for every side of the estate</h2>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {[
              {
                to: "/resident",
                icon: Building2,
                title: "Residents",
                body: "Log a complaint in under 3 clicks and watch it move to resolved.",
                cta: "Open resident dashboard",
              },
              {
                to: "/hoa",
                icon: ShieldCheck,
                title: "HOA Admins",
                body: "Run the pipeline, assign verified providers, lift the score.",
                cta: "Open admin dashboard",
              },
              {
                to: "/investor",
                icon: LineChart,
                title: "Investors",
                body: "Valuations, score breakdowns and 10-year ROI projections.",
                cta: "Open investor dashboard",
              },
            ].map(({ to, icon: Icon, title, body, cta }) => (
              <Card key={to} className="card-hover flex flex-col justify-between border-border/70 p-6">
                <div>
                  <Icon className="h-6 w-6 text-primary" />
                  <h3 className="mt-4 text-xl font-semibold text-foreground">{title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{body}</p>
                </div>
                <Button asChild variant="ghost" className="mt-5 justify-start px-0 text-primary">
                  <Link to={to}>
                    {cta}
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <footer className="bg-ink py-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
          <VantageMark tone="dark" />
          <p className="text-sm text-ink-foreground/60">
            © {new Date().getFullYear()} VANTAGE Property Health Intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}
