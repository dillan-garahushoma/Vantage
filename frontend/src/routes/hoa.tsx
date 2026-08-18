import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { BadgeCheck, Clock3, Megaphone, TrendingUp, Users } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DashboardShell } from "@/components/vantage/DashboardShell";
import { LivingScoreGauge } from "@/components/vantage/LivingScoreGauge";
import {
  COMPLAINT_STATUSES,
  LIVING_SCORE,
  estate,
  pipelineComplaints,
  serviceProviders,
  type Complaint,
  type ComplaintStatus,
} from "@/lib/vantage-data";

export const Route = createFileRoute("/hoa")({
  head: () => ({
    meta: [
      { title: "HOA Admin Dashboard | VANTAGE" },
      {
        name: "description",
        content:
          "Manage the complaint pipeline, assign verified service providers and publish announcements — while tracking the estate's Living Score.",
      },
      { property: "og:title", content: "HOA Admin Dashboard | VANTAGE" },
      {
        property: "og:description",
        content: "Efficient community management with live score impact for every resolution.",
      },
    ],
  }),
  component: HoaDashboard,
});

const metrics = [
  { icon: Clock3, label: "Avg resolution time", value: "2.4 days", sub: "-1.7 days vs last quarter" },
  { icon: TrendingUp, label: "Complaint frequency", value: "18 / 100 units", sub: "90-day rolling" },
  { icon: Users, label: "Resident satisfaction", value: "4.0 / 5", sub: "63 surveys" },
  { icon: BadgeCheck, label: "Verified providers", value: "4 of 5", sub: "1 pending verification" },
];

function HoaDashboard() {
  const [complaints, setComplaints] = useState<Complaint[]>(pipelineComplaints);

  const update = (id: string, status: ComplaintStatus) => {
    setComplaints((prev) => prev.map((c) => (c.id === id ? { ...c, status } : c)));
    toast.success(`${id} moved to ${status}`);
  };

  const assign = (id: string, provider: string) => {
    setComplaints((prev) =>
      prev.map((c) => (c.id === id ? { ...c, assignee: provider, status: "Assigned" } : c)),
    );
    toast.success(`${id} assigned to ${provider}`);
  };

  return (
    <DashboardShell
      role="HOA Admin"
      title={`${estate.name} operations`}
      subtitle={`${estate.units} units · ${estate.suburb}. Every resolution you close feeds the estate's Living Score within 24 hours.`}
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map(({ icon: Icon, label, value, sub }) => (
              <Card key={label} className="card-hover border-border/70 bg-gradient-surface p-5">
                <Icon className="h-4 w-4 text-primary" />
                <p className="mt-3 text-xs uppercase tracking-widest text-muted-foreground">{label}</p>
                <p className="mt-1 font-display text-xl font-bold text-foreground">{value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
              </Card>
            ))}
          </div>

          <Tabs defaultValue="pipeline">
            <TabsList>
              <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
              <TabsTrigger value="providers">Providers</TabsTrigger>
              <TabsTrigger value="announce">Announcements</TabsTrigger>
            </TabsList>

            <TabsContent value="pipeline" className="mt-4 space-y-3">
              {complaints.map((c) => (
                <Card key={c.id} className="border-border/70 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-56 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-muted-foreground">{c.id}</span>
                        <Badge variant="secondary" className="text-[10px]">
                          {c.category}
                        </Badge>
                        <Badge
                          variant={c.priority === "High" ? "destructive" : "outline"}
                          className="text-[10px]"
                        >
                          {c.priority}
                        </Badge>
                      </div>
                      <p className="mt-1.5 text-sm font-semibold text-foreground">{c.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {c.unit} · {c.logged}
                        {c.assignee ? ` · ${c.assignee}` : " · unassigned"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Select value={c.status} onValueChange={(v) => update(c.id, v as ComplaintStatus)}>
                        <SelectTrigger className="w-40" aria-label={`Status for ${c.id}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {COMPLAINT_STATUSES.map((s) => (
                            <SelectItem key={s} value={s}>
                              {s}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={c.assignee ?? ""} onValueChange={(v) => assign(c.id, v)}>
                        <SelectTrigger className="w-48" aria-label={`Assign ${c.id}`}>
                          <SelectValue placeholder="Assign provider" />
                        </SelectTrigger>
                        <SelectContent>
                          {serviceProviders.map((p) => (
                            <SelectItem key={p.name} value={p.name}>
                              {p.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </Card>
              ))}
            </TabsContent>

            <TabsContent value="providers" className="mt-4 grid gap-3 sm:grid-cols-2">
              {serviceProviders.map((p) => (
                <Card key={p.name} className="card-hover border-border/70 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.trade}</p>
                    </div>
                    {p.verified ? (
                      <Badge className="bg-success/18 text-success">Verified</Badge>
                    ) : (
                      <Badge variant="outline" className="text-warning-foreground">
                        Pending
                      </Badge>
                    )}
                  </div>
                  <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                    <span>★ {p.rating.toFixed(1)} · {p.jobs} jobs</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 px-2 text-primary"
                      onClick={() => toast.success(`${p.name} ready for assignment`)}
                    >
                      {p.verified ? "Assign task" : "Verify"}
                    </Button>
                  </div>
                </Card>
              ))}
            </TabsContent>

            <TabsContent value="announce" className="mt-4">
              <Card className="border-border/70 p-6">
                <div className="flex items-center gap-2">
                  <Megaphone className="h-4 w-4 text-primary" />
                  <h2 className="text-sm font-semibold text-foreground">Publish to all residents</h2>
                </div>
                <form
                  className="mt-4 space-y-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    toast.success("Announcement published to 148 units");
                  }}
                >
                  <div className="space-y-2">
                    <Label htmlFor="ann-title">Title</Label>
                    <Input id="ann-title" placeholder="e.g. Water tank cleaning on Saturday" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ann-body">Message</Label>
                    <Textarea id="ann-body" rows={4} placeholder="What residents need to know" required />
                  </div>
                  <Button type="submit">Publish announcement</Button>
                </form>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <aside className="space-y-6">
          <Card className="border-border/70 p-6">
            <div className="flex justify-center">
              <LivingScoreGauge score={LIVING_SCORE} size={170} />
            </div>
            <p className="mt-3 text-center text-xs text-muted-foreground">
              Close the 2 overdue civils items to reach 84.
            </p>
          </Card>
          <Card className="border-border/70 bg-gradient-hero p-6">
            <p className="text-xs uppercase tracking-widest text-ink-foreground/60">AI recommendation</p>
            <p className="mt-2 text-sm text-ink-foreground">
              Reassign waste collection to a second provider on Mondays — waste complaints cluster at
              41% of Monday volume and cost ~2 score points.
            </p>
          </Card>
        </aside>
      </div>
    </DashboardShell>
  );
}
