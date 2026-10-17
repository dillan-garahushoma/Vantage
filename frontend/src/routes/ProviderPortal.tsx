import { useState } from 'react'
import { Zap, FileText, Camera, Check, Clock, UserRound } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Surface } from '../components/valora/Surface'
import { WorkOrderCard, type WorkOrderItem } from '../components/valora/WorkOrderCard'
import { DetailDrawer } from '../components/valora/DetailDrawer'
import { StatusChip } from '../components/valora/StatusChip'
import { RequireEstate } from '../components/RequireEstate'
import { useEstateScope } from '../context/EstateContext'
import { useAuth } from '../context/AuthContext'
import { zar } from '../lib/format'

const demoAssignedOrders: WorkOrderItem[] = [
  {
    id: 'WO-2026-088',
    reference: 'WO-088',
    title: 'Replace Pool Pump 02 bearing & seals',
    description: 'Bearing and mechanical seal replacement on secondary clubhouse pool pump. Pre-season overhaul.',
    status: 'in_progress',
    location: 'Clubhouse Plant Room',
    provider: 'KZN Lift & Pump Services',
    dueDate: '24 Oct 2026',
    cost: 14200,
  },
  {
    id: 'WO-2026-084',
    reference: 'WO-084',
    title: 'Block C PRV Station pressure valve inspection',
    description: 'Diagnose morning pressure fluctuation. Replace worn diaphragm valve.',
    status: 'assigned',
    location: 'Block C Plant Room',
    provider: 'KZN Lift & Pump Services',
    dueDate: '28 Oct 2026',
    cost: 8600,
  },
  {
    id: 'WO-2026-079',
    reference: 'WO-079',
    title: 'Borehole Reticulation flow rate calibration',
    description: 'Routine quarterly flow measurement and controller sensor test.',
    status: 'completed',
    location: 'Reticulation Borehole 1',
    provider: 'KZN Lift & Pump Services',
    dueDate: '12 Oct 2026',
    cost: 4500,
  },
]

function ProviderPortalContent() {
  const { estate } = useEstateScope()
  const { user } = useAuth()
  const [selectedOrder, setSelectedOrder] = useState<WorkOrderItem | null>(null)
  const [checkedIn, setCheckedIn] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [photos, setPhotos] = useState<string[]>([
    'Pump_02_vibration_gauge.jpg',
    'Bearing_assembly_dismantle.jpg',
  ])

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3500)
  }

  const toggleCheckIn = () => {
    const next = !checkedIn
    setCheckedIn(next)
    showToast(
      next
        ? 'Arrival recorded: Estate control has been notified that your technician is on site.'
        : 'Departure recorded: You are no longer marked on site.',
    )
  }

  const handleAddPhoto = () => {
    const photoName = `Site_proof_${Date.now().toString().slice(-4)}.jpg`
    setPhotos((prev) => [...prev, photoName])
    showToast(`Photo "${photoName}" attached to active work order.`)
  }

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 shadow-lift">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-mint-wash text-mint">
            <Check className="h-4 w-4" />
          </span>
          <p className="text-[0.84rem] font-semibold text-ink">{toastMessage}</p>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold tracking-[0.18em] text-brand uppercase">
            Contractor & Provider Portal
          </p>
          <h1 className="mt-2 font-heading text-[1.75rem] font-extrabold tracking-[-0.025em] text-ink sm:text-[2rem]">
            {user?.full_name ?? 'KZN Lift & Pump Services'}
          </h1>
          <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-relaxed text-ink/60">
            Active job dispatch, site attendance check-in and completion records for {estate?.estate_name ?? 'Silverleaf Reserve'}.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            onClick={toggleCheckIn}
            variant={checkedIn ? 'outline' : 'default'}
            className={
              checkedIn
                ? 'h-11 rounded-full border-mint text-mint hover:bg-mint-wash px-6 text-[0.83rem] font-semibold'
                : 'h-11 rounded-full bg-ink px-6 text-[0.83rem] font-semibold text-white hover:bg-brand'
            }
          >
            <Clock className="mr-2 h-4 w-4" />
            {checkedIn ? 'Check out of site' : 'Check in on site'}
          </Button>
          <Button
            onClick={handleAddPhoto}
            variant="outline"
            className="h-11 rounded-full border-line px-5 text-[0.83rem] font-semibold hover:bg-canvas"
          >
            <Camera className="mr-2 h-4 w-4" />
            Upload proof photo
          </Button>
        </div>
      </div>

      {/* SLA & Rating Pills */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-[0.82rem] font-semibold text-ink">
          <Zap className="h-4 w-4 text-ochre" />
          4.8 / 5 Verified Estate Rating
        </span>
        <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-[0.82rem] font-semibold text-mint">
          <Check className="h-4 w-4" />
          96% Contract SLA Compliance
        </span>
        <span className="rounded-full border border-line bg-surface px-4 py-2 text-[0.82rem] font-medium text-ink-muted">
          Active Estate Vendor #PRV-01
        </span>
      </div>

      {/* Work Orders List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-heading text-[1.1rem] font-bold text-ink">Assigned Work Orders</h2>
            <p className="text-[0.82rem] text-ink-muted">
              Select any job to review scope, upload completion notes, or view estate contacts
            </p>
          </div>
          <span className="num rounded-full bg-brand-wash px-3 py-1 text-[0.72rem] font-semibold text-brand">
            {demoAssignedOrders.length} assigned
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {demoAssignedOrders.map((order) => (
            <WorkOrderCard
              key={order.id}
              workOrder={order}
              onClick={() => setSelectedOrder(order)}
            />
          ))}
        </div>
      </div>

      {/* Proof of Work Gallery */}
      <Surface>
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div>
            <h3 className="font-heading text-[1rem] font-bold text-ink">Recent Site Photographs</h3>
            <p className="text-[0.78rem] text-ink-muted">Images attached to active work orders</p>
          </div>
          <Button
            size="sm"
            onClick={handleAddPhoto}
            className="h-8 rounded-full bg-ink text-[0.75rem] font-semibold text-white hover:bg-brand"
          >
            <Camera className="mr-1.5 h-3.5 w-3.5" />
            Attach photo
          </Button>
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          {photos.map((photo, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-xl border border-line bg-canvas px-3.5 py-2 text-[0.78rem] font-medium text-ink"
            >
              <FileText className="h-4 w-4 text-brand" />
              <span>{photo}</span>
              <span className="text-[0.68rem] text-mint font-semibold">Verified</span>
            </div>
          ))}
        </div>
      </Surface>

      {/* Job Detail Drawer */}
      <DetailDrawer
        open={Boolean(selectedOrder)}
        onOpenChange={(open) => !open && setSelectedOrder(null)}
        title={selectedOrder?.title}
        subtitle={selectedOrder ? `${selectedOrder.reference} · ${selectedOrder.location}` : ''}
        badge={selectedOrder ? <StatusChip status={selectedOrder.status} size="sm" /> : null}
        width="sm:max-w-[620px]"
        footer={
          selectedOrder ? (
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setSelectedOrder(null)}
                className="h-10 rounded-full border-line px-5 text-[0.83rem] font-semibold hover:bg-canvas"
              >
                Close
              </Button>
              <Button
                onClick={() => {
                  showToast(`Work order ${selectedOrder.reference} marked as completed and sent for review.`)
                  setSelectedOrder(null)
                }}
                className="h-10 rounded-full bg-ink px-5 text-[0.83rem] font-semibold text-white hover:bg-brand"
              >
                Mark as resolved
              </Button>
            </div>
          ) : undefined
        }
      >
        {selectedOrder && (
          <div className="space-y-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Location
                </p>
                <p className="mt-1 text-[0.85rem] font-bold text-ink">{selectedOrder.location}</p>
              </div>
              <div className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Target Date
                </p>
                <p className="mt-1 text-[0.85rem] font-bold text-ink">{selectedOrder.dueDate}</p>
              </div>
              <div className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Authorized Cost
                </p>
                <p className="num mt-1 text-[0.85rem] font-bold text-ink">
                  {typeof selectedOrder.cost === 'number' ? zar(selectedOrder.cost) : selectedOrder.cost}
                </p>
              </div>
            </div>

            <div className="rounded-2xl bg-canvas p-4">
              <p className="text-[0.72rem] font-semibold tracking-[0.14em] text-brand uppercase">
                Job Description & Scope
              </p>
              <p className="mt-2 text-[0.88rem] leading-relaxed text-ink/75">
                {selectedOrder.description}
              </p>
            </div>

            <div className="rounded-xl border border-line p-4">
              <div className="flex items-center gap-2">
                <UserRound className="h-4 w-4 text-brand" />
                <h4 className="text-[0.78rem] font-semibold text-ink">Estate Contact</h4>
              </div>
              <p className="mt-1.5 text-[0.82rem] text-ink/70">
                Thandi Mokoena · Estate General Manager<br />
                Control Office: 031 555 0192 · gate@silverleaf.co.za
              </p>
            </div>
          </div>
        )}
      </DetailDrawer>
    </div>
  )
}

export function ProviderPortal() {
  return (
    <RequireEstate>
      <ProviderPortalContent />
    </RequireEstate>
  )
}

export default ProviderPortal
