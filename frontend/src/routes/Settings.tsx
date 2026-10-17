import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Save, BookOpen, Building2, ArrowRight, ShieldCheck, Check } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Switch } from '../components/ui/switch'
import { Surface } from '../components/valora/Surface'
import { DetailDrawer } from '../components/valora/DetailDrawer'
import { StatusChip } from '../components/valora/StatusChip'
import { RequireEstate } from '../components/RequireEstate'
import { useEstateScope } from '../context/EstateContext'
import { zar } from '../lib/format'
import {
  estateSettings,
  scoreMethodology,
} from '../lib/estateMockData'

function SettingsContent() {
  const { estate } = useEstateScope()
  const [profile, setProfile] = useState({
    name: estate?.estate_name ?? 'Silverleaf Reserve',
    units: '412',
    suburb: estate?.suburb ?? 'Durban North',
    city: estate?.city ?? 'eThekwini',
    province: estate?.province ?? 'KwaZulu-Natal',
    agent: 'Broll Property Intel',
    loadshedding: 'Stage 0 · Excluded Municipal Grid',
  })
  const [notifications, setNotifications] = useState(estateSettings.notifications)
  const [methodOpen, setMethodOpen] = useState(false)
  const [savedToast, setSavedToast] = useState(false)

  const update = (key: keyof typeof profile, val: string) => {
    setProfile((prev) => ({ ...prev, [key]: val }))
  }

  const handleSave = () => {
    setSavedToast(true)
    setTimeout(() => setSavedToast(false), 3500)
  }

  const toggle = (key: string) => {
    setNotifications((list) =>
      list.map((n) => (n.key === key ? { ...n, on: !n.on } : n)),
    )
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {savedToast && (
        <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 shadow-lift">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-mint-wash text-mint">
            <Check className="h-4 w-4" />
          </span>
          <p className="text-[0.84rem] font-semibold text-ink">
            Estate profile configuration saved successfully.
          </p>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold tracking-[0.18em] text-brand uppercase">
            Estate profile
          </p>
          <h1 className="mt-2 font-heading text-[1.75rem] font-extrabold tracking-[-0.025em] text-ink sm:text-[2rem]">
            {profile.name}
          </h1>
          <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-relaxed text-ink/60">
            Estate governance details, notification routing and Living Score methodology rules.
          </p>
        </div>
        <Button
          onClick={handleSave}
          className="h-11 shrink-0 rounded-full bg-ink px-5 text-[0.83rem] font-semibold text-white hover:bg-brand"
        >
          <Save className="mr-2 h-4 w-4" />
          Save preferences
        </Button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          {/* Estate Details Surface */}
          <Surface>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-canvas text-brand">
                <Building2 className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-heading text-[1rem] font-bold text-ink">Estate details</h2>
                <p className="text-[0.78rem] text-ink-muted">
                  Used across reports, official notices and board summaries
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div>
                <Label className="text-[0.78rem] font-semibold text-ink/70">Estate legal name</Label>
                <Input
                  value={profile.name}
                  onChange={(e) => update('name', e.target.value)}
                  className="mt-1.5 h-11 rounded-xl border-line bg-surface text-[0.87rem]"
                />
              </div>
              <div>
                <Label className="text-[0.78rem] font-semibold text-ink/70">Registered homes / units</Label>
                <Input
                  value={profile.units}
                  onChange={(e) => update('units', e.target.value)}
                  className="mt-1.5 h-11 rounded-xl border-line bg-surface text-[0.87rem]"
                />
              </div>
              <div>
                <Label className="text-[0.78rem] font-semibold text-ink/70">Suburb</Label>
                <Input
                  value={profile.suburb}
                  onChange={(e) => update('suburb', e.target.value)}
                  className="mt-1.5 h-11 rounded-xl border-line bg-surface text-[0.87rem]"
                />
              </div>
              <div>
                <Label className="text-[0.78rem] font-semibold text-ink/70">Municipality / City</Label>
                <Input
                  value={profile.city}
                  onChange={(e) => update('city', e.target.value)}
                  className="mt-1.5 h-11 rounded-xl border-line bg-surface text-[0.87rem]"
                />
              </div>
              <div>
                <Label className="text-[0.78rem] font-semibold text-ink/70">Managing agency</Label>
                <Input
                  value={profile.agent}
                  onChange={(e) => update('agent', e.target.value)}
                  className="mt-1.5 h-11 rounded-xl border-line bg-surface text-[0.87rem]"
                />
              </div>
              <div>
                <Label className="text-[0.78rem] font-semibold text-ink/70">Loadshedding status</Label>
                <Input
                  value={profile.loadshedding}
                  onChange={(e) => update('loadshedding', e.target.value)}
                  className="mt-1.5 h-11 rounded-xl border-line bg-surface text-[0.87rem]"
                />
              </div>
            </div>

            <div className="mt-6 grid gap-4 border-t border-line pt-5 sm:grid-cols-3">
              <div>
                <p className="text-[0.68rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Established
                </p>
                <p className="num mt-1 text-[0.92rem] font-bold text-ink">2018</p>
              </div>
              <div>
                <p className="text-[0.68rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Average Levy
                </p>
                <p className="num mt-1 text-[0.92rem] font-bold text-ink">{zar(3450)} / mo</p>
              </div>
              <div>
                <p className="text-[0.68rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Reserve Fund Target
                </p>
                <p className="num mt-1 text-[0.92rem] font-bold text-ink">{zar(4500000)}</p>
              </div>
            </div>
          </Surface>

          {/* Operational Notifications */}
          <Surface>
            <h2 className="font-heading text-[1rem] font-bold text-ink">Operational notifications</h2>
            <p className="mt-1 text-[0.82rem] text-ink-muted">
              Configure telemetry thresholds and weekly alerts pushed to the management office
            </p>

            <ul className="mt-5 divide-y divide-line-soft">
              {notifications.map((n) => (
                <li key={n.key} className="flex items-start justify-between gap-6 py-4 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-[0.88rem] font-semibold text-ink">{n.label}</p>
                    <p className="mt-1 text-[0.8rem] leading-relaxed text-ink/60">{n.detail}</p>
                  </div>
                  <Switch
                    checked={n.on}
                    onCheckedChange={() => toggle(n.key)}
                    aria-label={n.label}
                    className="mt-1 shrink-0"
                  />
                </li>
              ))}
            </ul>
          </Surface>

          {/* Living Score Methodology Banner */}
          <Surface>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-heading text-[1rem] font-bold text-ink">
                  How the Living Score is calculated
                </h2>
                <p className="mt-1 text-[0.82rem] text-ink-muted">
                  Mathematical weights, 90-day rolling evaluation and snapshot immutability
                </p>
              </div>
              <Button
                onClick={() => setMethodOpen(true)}
                variant="outline"
                className="h-10 rounded-full border-line px-5 text-[0.8rem] font-semibold hover:bg-canvas"
              >
                <BookOpen className="mr-2 h-4 w-4" />
                View methodology
              </Button>
            </div>
          </Surface>
        </div>

        {/* Right Rail */}
        <div className="space-y-6">
          <Surface>
            <h2 className="font-heading text-[1rem] font-bold text-ink">Contracted providers</h2>
            <p className="mt-1 text-[0.82rem] text-ink-muted">Active service contractors on file</p>

            <ul className="mt-4 space-y-2.5">
              {estateSettings.providers.map((p) => (
                <li key={p.name} className="rounded-xl border border-line p-3.5">
                  <p className="text-[0.85rem] font-semibold text-ink">{p.name}</p>
                  <p className="mt-0.5 text-[0.76rem] text-ink-muted">{p.category}</p>
                  <div className="mt-2">
                    <StatusChip status="Healthy" size="sm" />
                  </div>
                </li>
              ))}
            </ul>

            <Link
              to="/app/financial"
              className="mt-4 inline-flex items-center gap-1.5 text-[0.8rem] font-semibold text-brand hover:text-ink"
            >
              Performance scorecards & SLAs <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Surface>

          <Surface className="bg-canvas/50">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-brand" />
              <h2 className="font-heading text-[0.92rem] font-bold text-ink">Data and privacy</h2>
            </div>
            <ul className="mt-3 space-y-2.5 text-[0.8rem] leading-relaxed text-ink/70">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft" />
                Resident feedback is reported in aggregate only; individual votes are never revealed.
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft" />
                Incident records preserve operational facts; resident PII is strictly protected.
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-soft" />
                VALORA Intelligence accesses physical signals and operational logs — never resident chat.
              </li>
            </ul>
          </Surface>
        </div>
      </div>

      {/* Methodology Drawer */}
      <DetailDrawer
        open={methodOpen}
        onOpenChange={setMethodOpen}
        title="Living Score Methodology"
        subtitle="Operational standard, weighting and audit compliance"
        width="sm:max-w-[620px]"
      >
        <div className="space-y-5">
          {scoreMethodology.map((s) => (
            <div key={s.title} className="rounded-2xl border border-line p-5">
              <p className="font-heading text-[0.95rem] font-bold text-ink">{s.title}</p>
              <p className="mt-2 text-[0.84rem] leading-relaxed text-ink/70">{s.body}</p>
            </div>
          ))}
        </div>
      </DetailDrawer>
    </div>
  )
}

export function Settings() {
  return (
    <RequireEstate>
      <SettingsContent />
    </RequireEstate>
  )
}

export default Settings
