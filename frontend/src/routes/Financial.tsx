import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Check, FileText, TrendingUp, Wallet, ShieldCheck, DollarSign } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Surface } from '../components/valora/Surface'
import { ChartCard } from '../components/valora/ChartCard'
import { ChartTooltip } from '../components/valora/ChartTooltip'
import { ProviderScorecard } from '../components/valora/ProviderScorecard'
import { BoardReportDialog } from '../components/valora/BoardReportDialog'
import { StatusChip } from '../components/valora/StatusChip'
import { RequireEstate } from '../components/RequireEstate'
import { useEstateScope } from '../context/EstateContext'
import { zar, zarShort } from '../lib/format'
import {
  defaultBoardSummary,
  financeSummary,
  financialDecisions,
  providerScorecards,
  spendByCategory,
} from '../lib/estateMockData'

function FinancialContent() {
  const { estate } = useEstateScope()
  const [decisions, setDecisions] = useState(financialDecisions)
  const [reportOpen, setReportOpen] = useState(false)
  const [activeDecisionToast, setActiveDecisionToast] = useState<string | null>(null)

  const handleDecide = (id: string, outcome: 'Approved' | 'In review') => {
    setDecisions((list) =>
      list.map((d) => (d.id === id ? { ...d, status: outcome } : d)),
    )
    const target = decisions.find((d) => d.id === id)
    setActiveDecisionToast(
      outcome === 'Approved'
        ? `${target?.title ?? 'Item'} approved (${zar(target?.amount ?? 0)} authorised).`
        : `${target?.title ?? 'Item'} deferred to monthly review.`,
    )
    setTimeout(() => setActiveDecisionToast(null), 4000)
  }

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {activeDecisionToast && (
        <div className="flex items-center justify-between rounded-2xl border border-line bg-surface p-4 shadow-lift">
          <div className="flex items-center gap-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-mint-wash text-mint">
              <Check className="h-4 w-4" />
            </span>
            <p className="text-[0.84rem] font-semibold text-ink">{activeDecisionToast}</p>
          </div>
          <Button
            variant="ghost"
            onClick={() => setActiveDecisionToast(null)}
            className="h-8 text-[0.75rem] font-medium"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold tracking-[0.18em] text-brand uppercase">
            Financial & service performance
          </p>
          <h1 className="mt-2 font-heading text-[1.75rem] font-extrabold tracking-[-0.025em] text-ink sm:text-[2rem]">
            {zar(financeSummary.ytdActual)} of {zar(financeSummary.ytdBudget)} spent
          </h1>
          <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-relaxed text-ink/60">
            {financeSummary.variance}% favorable variance under year-to-date budget, with{' '}
            <strong className="text-ink">{financeSummary.levyCollection}%</strong> levy collection and{' '}
            {zar(financeSummary.arrears)} in active arrears.
          </p>
        </div>
        <Button
          onClick={() => setReportOpen(true)}
          className="h-11 shrink-0 rounded-full bg-ink px-5 text-[0.83rem] font-semibold text-white hover:bg-brand"
        >
          <FileText className="mr-2 h-4 w-4" />
          Generate board report
        </Button>
      </div>

      {/* Top 4 Financial Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              YTD Spend
            </span>
            <Wallet className="h-4 w-4 text-brand" />
          </div>
          <p className="num mt-2 font-heading text-[1.5rem] font-extrabold text-ink">
            {zarShort(financeSummary.ytdActual)}
          </p>
          <p className="mt-1 text-[0.72rem] text-mint font-semibold">
            -{financeSummary.variance}% under budget
          </p>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              Levy Collection
            </span>
            <ShieldCheck className="h-4 w-4 text-mint" />
          </div>
          <p className="num mt-2 font-heading text-[1.5rem] font-extrabold text-ink">
            {financeSummary.levyCollection}%
          </p>
          <p className="mt-1 text-[0.72rem] text-ink-muted">Target threshold 95.0%</p>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              Capital Reserve
            </span>
            <TrendingUp className="h-4 w-4 text-brand" />
          </div>
          <p className="num mt-2 font-heading text-[1.5rem] font-extrabold text-ink">
            {zarShort(financeSummary.reserveFund)}
          </p>
          <p className="mt-1 text-[0.72rem] text-mint font-semibold">Fully funded 10-yr plan</p>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between">
            <span className="text-[0.72rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
              Arrears Exposure
            </span>
            <DollarSign className="h-4 w-4 text-ochre" />
          </div>
          <p className="num mt-2 font-heading text-[1.5rem] font-extrabold text-ink">
            {zar(financeSummary.arrears)}
          </p>
          <p className="mt-1 text-[0.72rem] text-ink-muted">4 units under notice</p>
        </Surface>
      </div>

      {/* Spend Breakdown & Financial Decisions */}
      <div className="grid gap-6 xl:grid-cols-3">
        {/* Chart */}
        <ChartCard
          className="xl:col-span-2"
          title="Operating expenditure by service category"
          description="Actual expenditure against budgeted allocation across operational cost centers"
          height={280}
          footer="All figures represent confirmed invoices and approved contract drawdowns for the fiscal period."
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={spendByCategory} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="#EFEBFB" vertical={false} />
              <XAxis
                dataKey="category"
                tickLine={false}
                axisLine={false}
                tick={{ fill: '#1F1733', opacity: 0.5, fontSize: 11 }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fill: '#1F1733', opacity: 0.5, fontSize: 11 }}
                tickFormatter={(v) => zarShort(v)}
              />
              <Tooltip
                content={
                  <ChartTooltip
                    formatter={(val) => zar(Number(val))}
                  />
                }
              />
              <Bar dataKey="budget" name="Budget" fill="#E9E3FF" radius={[6, 6, 0, 0]} />
              <Bar dataKey="actual" name="Actual spend" fill="#7C3AED" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Governance Decisions Panel */}
        <Surface className="flex flex-col">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <div>
              <h3 className="font-heading text-[1rem] font-bold text-ink">Pending Decisions</h3>
              <p className="text-[0.76rem] text-ink-muted">Capital allocations awaiting board action</p>
            </div>
            <span className="num rounded-full bg-brand-wash px-2.5 py-0.5 text-[0.7rem] font-bold text-brand">
              {decisions.filter((d) => d.status === 'In review').length} in review
            </span>
          </div>

          <div className="mt-4 flex-1 space-y-3.5">
            {decisions.map((decision) => (
              <div
                key={decision.id}
                className="rounded-xl border border-line p-3.5 transition-colors hover:bg-canvas"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-[0.84rem] font-semibold text-ink leading-snug">
                    {decision.title}
                  </h4>
                  <StatusChip status={decision.status} size="sm" />
                </div>
                <div className="mt-2 flex items-center justify-between text-[0.75rem]">
                  <span className="num font-bold text-ink">{zar(decision.amount)}</span>
                  <span className="text-ink-muted">{decision.date}</span>
                </div>
                <p className="mt-1 text-[0.73rem] text-ink-muted">{decision.impact}</p>

                {decision.status === 'In review' && (
                  <div className="mt-3 flex justify-end gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDecide(decision.id, 'In review')}
                      className="h-8 rounded-full border-line text-[0.72rem] font-medium"
                    >
                      Defer
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleDecide(decision.id, 'Approved')}
                      className="h-8 rounded-full bg-ink text-white hover:bg-brand text-[0.72rem] font-semibold"
                    >
                      Approve
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Surface>
      </div>

      {/* Provider Performance Scorecards */}
      <div>
        <div className="mb-4">
          <h2 className="font-heading text-[1.1rem] font-bold text-ink">
            Contracted Service Provider Performance
          </h2>
          <p className="text-[0.82rem] text-ink-muted">
            SLA achievement, variance and resident feedback across major estate contracts.
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {providerScorecards.map((p) => (
            <ProviderScorecard key={p.id} provider={p} />
          ))}
        </div>
      </div>

      {/* Board Report Dialog */}
      <BoardReportDialog
        open={reportOpen}
        onOpenChange={setReportOpen}
        summary={defaultBoardSummary}
        period="Rolling 90 Days"
        estateName={estate?.estate_name ?? 'Silverleaf Reserve'}
      />
    </div>
  )
}

export function Financial() {
  return (
    <RequireEstate>
      <FinancialContent />
    </RequireEstate>
  )
}

export default Financial
