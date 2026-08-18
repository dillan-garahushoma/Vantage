import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Megaphone, Plus } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { DashboardShell } from "@/components/vantage/DashboardShell";
import { LivingScoreGauge } from "@/components/vantage/LivingScoreGauge";
import {
  COMPLAINT_CATEGORIES,
  COMPLAINT_STATUSES,
  LIVING_SCORE,
  announcements,
  estate,
  myComplaints,
  type Complaint,
} from "@/lib/vantage-data";

export const Route = createFileRoute("/resident")({
  head: () => ({
    meta: [
      { title: "Resident Dashboard | VANTAGE" },
      {
        name: "description",
        content:
          "Log complaints in seconds, track them from logged to resolved and follow your estate's Living Score and HOA announcements.",
      },
      { property: "og:title", content: "Resident Dashboard | VANTAGE" },
      {
        property: "og:description",
        content: "Frictionless complaint logging and full transparency on your estate's health.",
      },
    ],
  }),
  component: ResidentDashboard,
});

const statusTone: Record<string, string> = {
  Logged: "bg-secondary text-secondary-foreground",
  "Under Review": "bg-warning/20 text-warning-foreground",
  Assigned: "bg-primary/12 text-primary",
  "In Progress": "bg-primary/20 text-primary",
  Resolved: "bg-success/18 text-success",
  Closed: "bg-muted text-muted-foreground",
};

function ComplaintCard({ c }: { c: Complaint }) {
  return (
    <Card className="card-hover border-border/70 p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold leading-snug text-foreground">{c.title}</p>
        <span className="shrink-0 text-[11px] text-muted-foreground">{c.id}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge variant="secondary" className="text-[11px]">
          {c.category}
        </Badge>
        <Badge variant="outline" className="text-[11px]">
          {c.priority}
        </Badge>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        {c.logged}
        {c.assignee ? ` · ${c.assignee}` : ""}
      </p>
    </Card>
  );
}

function ResidentDashboard() {
  const [complaints, setComplaints] = useState<Complaint[]>(myComplaints);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(COMPLAINT_CATEGORIES[0]!);

  const submit = () => {
    if (!title.trim()) return;
    setComplaints((prev) => [
      {
        id: `CMP-${1100 + prev.length}`,
        title: title.trim(),
        category,
        unit: estate.unit,
        status: "Logged",
        logged: "Just now",
        priority: "Medium",
      },
      ...prev,
    ]);
    setTitle("");
    setOpen(false);
    toast.success("Complaint logged", {
      description: "The HOA has been notified. You'll see status changes here.",
    });
  };

  return (
    <DashboardShell
      role="Resident"
      title={`Good day — ${estate.unit}, ${estate.name}`}
      subtitle="Log an issue, follow its lifecycle, and see exactly how resolutions move your estate's Living Score."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              { label: "Estimated value", value: estate.valuation, sub: estate.valuationDelta },
              { label: "Rental yield", value: estate.rentalYield, sub: "Suburb median 5.6%" },
              { label: "Open complaints", value: String(complaints.filter((c) => c.status !== "Closed" && c.status !== "Resolved").length), sub: "Median resolution 2.4 days" },
            ].map((s) => (
              <Card key={s.label} className="border-border/70 bg-gradient-surface p-5">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">{s.label}</p>
                <p className="mt-2 font-display text-2xl font-bold text-foreground">{s.value}</p>
                <p className="mt-1 text-xs text-success">{s.sub}</p>
              </Card>
            ))}
          </div>

          {/* Quick action */}
          <Card className="flex flex-wrap items-center justify-between gap-4 border-border/70 bg-gradient-hero p-6">
            <div>
              <h2 className="text-lg font-semibold text-ink-foreground">Something wrong on the estate?</h2>
              <p className="mt-1 text-sm text-ink-foreground/70">
                Two fields, one tap. Resolutions lift the Living Score for everyone.
              </p>
            </div>
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button size="lg">
                  <Plus className="mr-1 h-4 w-4" />
                  Log a Complaint
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Log a complaint</DialogTitle>
                  <DialogDescription>
                    Pick a category and describe the issue — that's all we need.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Category</Label>
                    <div className="flex flex-wrap gap-2">
                      {COMPLAINT_CATEGORIES.map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => setCategory(cat)}
                          className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                            category === cat
                              ? "border-primary bg-primary/12 text-primary"
                              : "border-border text-muted-foreground hover:bg-secondary"
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="complaint-title">What's happening?</Label>
                    <Input
                      id="complaint-title"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Boom gate not opening with my tag"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="complaint-detail">Extra detail (optional)</Label>
                    <Textarea id="complaint-detail" rows={3} placeholder="Location, time of day, anything useful" />
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={submit}>Submit complaint</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </Card>

          {/* Kanban */}
          <div>
            <h2 className="text-lg font-semibold text-foreground">My complaints</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {COMPLAINT_STATUSES.map((status) => {
                const items = complaints.filter((c) => c.status === status);
                return (
                  <div key={status} className="rounded-xl border border-border/70 bg-secondary/40 p-3">
                    <div className="mb-3 flex items-center justify-between">
                      <span
                        className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusTone[status]}`}
                      >
                        {status}
                      </span>
                      <span className="text-xs text-muted-foreground">{items.length}</span>
                    </div>
                    <div className="space-y-3">
                      {items.length === 0 ? (
                        <p className="px-1 py-3 text-xs text-muted-foreground">Nothing here</p>
                      ) : (
                        items.map((c) => <ComplaintCard key={c.id} c={c} />)
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          <Card className="border-border/70 p-6">
            <div className="flex justify-center">
              <LivingScoreGauge score={LIVING_SCORE} size={180} />
            </div>
            <p className="mt-3 text-center text-xs text-muted-foreground">
              +3 points this month — faster resolutions and zero security incidents.
            </p>
          </Card>

          <Card className="border-border/70 p-6">
            <div className="flex items-center gap-2">
              <Megaphone className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Community feed</h2>
            </div>
            <div className="mt-4 space-y-4">
              {announcements.map((a) => (
                <div key={a.id} className="border-b border-border/60 pb-4 last:border-0 last:pb-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-[10px]">
                      {a.tag}
                    </Badge>
                    <span className="text-[11px] text-muted-foreground">{a.time}</span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-foreground">{a.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{a.body}</p>
                </div>
              ))}
            </div>
          </Card>
        </aside>
      </div>
    </DashboardShell>
  );
}
