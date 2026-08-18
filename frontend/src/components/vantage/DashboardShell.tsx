import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Building2, Home, LineChart, ShieldCheck } from "lucide-react";

const navItems = [
  { to: "/", label: "Home", icon: Home },
  { to: "/resident", label: "Resident", icon: Building2 },
  { to: "/hoa", label: "HOA Admin", icon: ShieldCheck },
  { to: "/investor", label: "Investor", icon: LineChart },
];

export function VantageMark({ tone = "light" }: { tone?: "light" | "dark" }) {
  return (
    <Link to="/" className="flex items-center gap-2">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-accent text-primary-foreground">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.4">
          <path d="M4 20 L12 5 L20 20" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span
        className={`font-display text-lg font-bold tracking-tight ${
          tone === "dark" ? "text-ink-foreground" : "text-foreground"
        }`}
      >
        VANTAGE
      </span>
    </Link>
  );
}

export function DashboardShell({
  role,
  title,
  subtitle,
  children,
}: {
  role: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b border-border/80 bg-card/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <VantageMark />
          <nav className="flex items-center gap-1 overflow-x-auto">
            {navItems.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: true }}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground data-[status=active]:bg-secondary data-[status=active]:text-primary"
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">{role}</p>
          <h1 className="mt-1 text-3xl font-bold text-foreground">{title}</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  );
}
