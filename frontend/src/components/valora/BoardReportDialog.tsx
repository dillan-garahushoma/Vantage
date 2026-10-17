import { Check, Download } from 'lucide-react'
import { Button } from '../ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Logo } from './Logo'

export interface BoardReportSummary {
  headline: string
  points: string[]
}

export interface BoardReportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  summary: BoardReportSummary
  period: string
  estateName: string
}

export function BoardReportDialog({
  open,
  onOpenChange,
  summary,
  period,
  estateName,
}: BoardReportDialogProps) {
  const exportReport = () => {
    const lines = [
      `VALORA — board report`,
      `${estateName} · ${period}`,
      '',
      summary.headline,
      '',
      ...summary.points.map((p, i) => `${i + 1}. ${p}`),
      '',
      'Generated from measured estate operational signals. Recommendations are clearly separated from measured results.',
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `valora-board-report-${period.toLowerCase().replace(/\s+/g, '-')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="scrollbar-slim max-h-[92vh] w-[94vw] overflow-y-auto rounded-3xl border-line p-0 sm:max-w-[640px]">
        <DialogHeader className="border-b border-line px-6 py-5 text-left">
          <Logo size={22} />
          <DialogTitle className="mt-4 font-heading text-[1.2rem] font-extrabold tracking-[-0.01em] text-ink">
            Board-ready summary
          </DialogTitle>
          <DialogDescription className="text-[0.85rem] leading-relaxed text-ink-muted">
            {summary.headline}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3.5 px-6 py-5">
          {summary.points.map((p) => (
            <div key={p} className="flex gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-mint-wash text-mint">
                <Check className="h-3 w-3" />
              </span>
              <p className="text-[0.86rem] leading-relaxed text-ink/75">{p}</p>
            </div>
          ))}

          <div className="rounded-xl bg-canvas p-4 text-[0.78rem] leading-relaxed text-ink-muted">
            Every figure in this summary traces back to measured signals. VALORA Intelligence
            recommendations are listed separately and labelled as recommendations in the full pack.
          </div>
        </div>

        <div className="flex flex-col gap-2 border-t border-line px-6 py-4 sm:flex-row sm:justify-end">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="h-11 rounded-full border-line px-6 text-[0.85rem] font-semibold hover:bg-canvas"
          >
            Close
          </Button>
          <Button
            onClick={exportReport}
            className="h-11 rounded-full bg-ink px-6 text-[0.85rem] font-semibold text-white hover:bg-brand"
          >
            <Download className="mr-2 h-4 w-4" />
            Export summary
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default BoardReportDialog
