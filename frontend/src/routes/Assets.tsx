import { useState } from 'react'
import {
  Boxes,
  Map as MapIcon,
  Plus,
  List,
  Wrench,
  Activity,
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Surface } from '../components/valora/Surface'
import { DataTable, type DataTableColumn } from '../components/valora/DataTable'
import { DetailDrawer } from '../components/valora/DetailDrawer'
import { EstateMap } from '../components/valora/EstateMap'
import { StatusChip } from '../components/valora/StatusChip'
import { CreateWorkOrderDialog } from '../components/valora/CreateWorkOrderDialog'
import { RequireEstate } from '../components/RequireEstate'
import { useEstateScope } from '../context/EstateContext'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import type { Page, Property } from '../lib/types'
import { zar } from '../lib/format'
import { cn } from '../lib/utils'
import {
  estateAssets,
  estateMapMarkers,
  type AssetRecord,
} from '../lib/estateMockData'

const conditionFilters = ['Healthy', 'Watch', 'At Risk', 'Critical'] as const

function AssetsContent() {
  const { estate, estateId } = useEstateScope()
  const { user } = useAuth()
  const isHoaAdmin = user?.role === 'hoa_admin'

  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null)
  const [workOrderOpen, setWorkOrderOpen] = useState(false)
  const [workOrderDefaults, setWorkOrderDefaults] = useState<{
    title?: string
    asset?: string
    priority?: 'urgent' | 'high' | 'medium' | 'low'
  }>()

  // Real backend properties list
  const { data: propertiesPage } = useAsync<Page<Property>>(
    () => api.get<Page<Property>>('/api/v1/properties', { estate_id: estateId, size: 100 }),
    [estateId],
  )
  const properties = propertiesPage?.items ?? []

  const counts = conditionFilters.map((condition) => ({
    condition,
    count: estateAssets.filter((a) => a.condition === condition).length,
  }))

  const assetColumns: DataTableColumn<AssetRecord & Record<string, unknown>>[] = [
    {
      key: 'name',
      header: 'Asset name',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-semibold text-ink">{row.name}</p>
          <p className="mt-0.5 text-[0.72rem] text-ink-muted">{row.id} · {row.system}</p>
        </div>
      ),
    },
    { key: 'category', header: 'Category', sortable: true },
    { key: 'location', header: 'Location', sortable: true },
    {
      key: 'condition',
      header: 'Condition',
      sortable: true,
      render: (row) => <StatusChip status={row.condition} size="sm" />,
    },
    { key: 'lastService', header: 'Last service' },
    { key: 'nextAction', header: 'Next planned action' },
    {
      key: 'risk',
      header: 'Risk',
      sortable: true,
      render: (row) => <StatusChip status={row.risk} size="sm" />,
    },
  ]

  const unitColumns: DataTableColumn<Property & Record<string, unknown>>[] = [
    {
      key: 'unit_no',
      header: 'Unit',
      sortable: true,
      render: (row) => (
        <span className="font-semibold text-ink">{row.unit_no}</span>
      ),
    },
    { key: 'complex_name', header: 'Complex / Block' },
    { key: 'street_address', header: 'Street address' },
    {
      key: 'size_m2',
      header: 'Size (m²)',
      render: (row) => (row.size_m2 ? `${row.size_m2} m²` : '—'),
    },
    {
      key: 'bedrooms',
      header: 'Beds / Baths',
      render: (row) => `${row.bedrooms ?? '—'} / ${row.bathrooms ?? '—'}`,
    },
  ]

  const handleCreateWorkOrderForAsset = (asset: AssetRecord) => {
    setWorkOrderDefaults({
      title: `Service / Maintenance: ${asset.name}`,
      asset: asset.name,
      priority: asset.condition === 'Critical' ? 'urgent' : asset.condition === 'At Risk' ? 'high' : 'medium',
    })
    setSelectedAsset(null)
    setWorkOrderOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold tracking-[0.18em] text-brand uppercase">
            Assets & infrastructure
          </p>
          <h1 className="mt-2 font-heading text-[1.75rem] font-extrabold tracking-[-0.025em] text-ink sm:text-[2rem]">
            {estate?.estate_name ?? 'Estate'} Infrastructure Register
          </h1>
          <p className="mt-1.5 max-w-2xl text-[0.9rem] leading-relaxed text-ink/60">
            Physical assets, operational plant rooms, reticulation networks and residential units
            with condition telemetry and lifecycle tracking.
          </p>
        </div>
        {isHoaAdmin && (
          <Button
            onClick={() => {
              setWorkOrderDefaults(undefined)
              setWorkOrderOpen(true)
            }}
            className="h-11 shrink-0 rounded-full bg-ink px-5 text-[0.83rem] font-semibold text-white hover:bg-brand"
          >
            <Plus className="mr-1.5 h-4 w-4" />
            Raise work order
          </Button>
        )}
      </div>

      {/* Condition Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {counts.map((c) => {
          const toneClass = {
            Healthy: 'text-mint',
            Watch: 'text-ochre',
            'At Risk': 'text-brick',
            Critical: 'text-brick',
          }[c.condition]

          return (
            <Surface key={c.condition} className="flex items-center justify-between">
              <div>
                <p className="text-[0.78rem] font-medium text-ink-muted">{c.condition}</p>
                <p className={cn('num mt-1 font-heading text-[1.6rem] font-extrabold leading-none', toneClass)}>
                  {c.count}
                </p>
              </div>
              <span className={cn('text-[0.7rem] font-semibold', toneClass)}>
                {Math.round((c.count / estateAssets.length) * 100)}% of equipment
              </span>
            </Surface>
          )
        })}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="equipment" className="space-y-6">
        <TabsList className="h-11 rounded-full border border-line bg-surface p-1">
          <TabsTrigger value="equipment" className="rounded-full px-5 text-[0.82rem] font-semibold">
            <Boxes className="mr-2 h-4 w-4" />
            Infrastructure & Equipment ({estateAssets.length})
          </TabsTrigger>
          <TabsTrigger value="map" className="rounded-full px-5 text-[0.82rem] font-semibold">
            <MapIcon className="mr-2 h-4 w-4" />
            Estate Spatial Map
          </TabsTrigger>
          <TabsTrigger value="units" className="rounded-full px-5 text-[0.82rem] font-semibold">
            <List className="mr-2 h-4 w-4" />
            Residential Units ({properties.length})
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Equipment */}
        <TabsContent value="equipment" className="space-y-4">
          <Surface padded={false}>
            <div className="border-b border-line px-5 py-4 sm:px-6">
              <h2 className="font-heading text-[1rem] font-bold text-ink">
                Operational Equipment Inventory
              </h2>
              <p className="text-[0.78rem] text-ink-muted">
                Click any asset to review telemetry, service log and maintenance actions.
              </p>
            </div>
            <div className="p-2 sm:p-4">
              <DataTable
                columns={assetColumns}
                rows={estateAssets as (AssetRecord & Record<string, unknown>)[]}
                rowKey={(row) => row.id}
                searchKeys={['name', 'category', 'location', 'system']}
                searchPlaceholder="Search plant equipment, PRVs, pumps, solar..."
                onRowClick={(row) => setSelectedAsset(row as AssetRecord)}
              />
            </div>
          </Surface>
        </TabsContent>

        {/* Tab 2: Map */}
        <TabsContent value="map" className="space-y-4">
          <Surface className="p-0 overflow-hidden">
            <div className="border-b border-line px-5 py-4 sm:px-6">
              <h2 className="font-heading text-[1rem] font-bold text-ink">
                Interactive Estate Telemetry Map
              </h2>
              <p className="text-[0.78rem] text-ink-muted">
                Spatial location of high-criticality assets across {estate?.estate_name ?? 'the estate'}.
              </p>
            </div>
            <div className="p-5 sm:p-6">
              <EstateMap markers={estateMapMarkers} height={420} />
            </div>
          </Surface>
        </TabsContent>

        {/* Tab 3: Units */}
        <TabsContent value="units" className="space-y-4">
          <Surface padded={false}>
            <div className="border-b border-line px-5 py-4 sm:px-6">
              <h2 className="font-heading text-[1rem] font-bold text-ink">
                Registered Residential Units
              </h2>
              <p className="text-[0.78rem] text-ink-muted">
                Official property register synchronized from the estate's unit roll.
              </p>
            </div>
            <div className="p-2 sm:p-4">
              <DataTable
                columns={unitColumns}
                rows={properties as (Property & Record<string, unknown>)[]}
                rowKey={(row) => row.id}
                searchKeys={['unit_no', 'complex_name', 'street_address']}
                searchPlaceholder="Filter by unit number or street..."
              />
            </div>
          </Surface>
        </TabsContent>
      </Tabs>

      {/* Asset Detail Drawer */}
      <DetailDrawer
        open={Boolean(selectedAsset)}
        onOpenChange={(open) => !open && setSelectedAsset(null)}
        title={selectedAsset?.name}
        subtitle={selectedAsset ? `${selectedAsset.id} · ${selectedAsset.system}` : ''}
        badge={selectedAsset ? <StatusChip status={selectedAsset.condition} size="sm" /> : null}
        width="sm:max-w-[620px]"
        footer={
          selectedAsset && isHoaAdmin ? (
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setSelectedAsset(null)}
                className="h-10 rounded-full border-line px-5 text-[0.83rem] font-semibold hover:bg-canvas"
              >
                Close
              </Button>
              <Button
                onClick={() => handleCreateWorkOrderForAsset(selectedAsset)}
                className="h-10 rounded-full bg-ink px-5 text-[0.83rem] font-semibold text-white hover:bg-brand"
              >
                <Wrench className="mr-1.5 h-3.5 w-3.5" />
                Raise work order
              </Button>
            </div>
          ) : undefined
        }
      >
        {selectedAsset && (
          <div className="space-y-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Location
                </p>
                <p className="mt-1 text-[0.85rem] font-bold text-ink">{selectedAsset.location}</p>
              </div>
              <div className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Category
                </p>
                <p className="mt-1 text-[0.85rem] font-bold text-ink">{selectedAsset.category}</p>
              </div>
              <div className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink-muted uppercase">
                  Replacement
                </p>
                <p className="num mt-1 text-[0.85rem] font-bold text-ink">
                  {selectedAsset.replacementCostZar ? zar(selectedAsset.replacementCostZar) : '—'}
                </p>
              </div>
            </div>

            <div className="rounded-2xl bg-canvas p-4">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-brand" />
                <p className="text-[0.72rem] font-semibold tracking-[0.14em] text-brand uppercase">
                  Operational Status & Telemetry
                </p>
              </div>
              <p className="mt-2 text-[0.88rem] leading-relaxed text-ink/75">
                Condition evaluated as <strong className="text-ink">{selectedAsset.condition}</strong> based on
                rolling telemetry signals and scheduled lifecycle inspections.
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[0.78rem]">
                <div className="rounded-lg bg-surface p-2.5 border border-line">
                  <span className="text-ink-muted">Last serviced:</span>{' '}
                  <span className="font-semibold text-ink">{selectedAsset.lastService}</span>
                </div>
                <div className="rounded-lg bg-surface p-2.5 border border-line">
                  <span className="text-ink-muted">Next action:</span>{' '}
                  <span className="font-semibold text-ink">{selectedAsset.nextAction}</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-line p-4">
              <h4 className="text-[0.72rem] font-semibold tracking-[0.14em] text-ink-muted uppercase">
                Integrations & Sourcing
              </h4>
              <p className="mt-1.5 text-[0.82rem] text-ink/70">
                Signals from this asset feed directly into the weekly VALORA Intelligence model.
                Any logged work order automatically updates the Living Score Asset Uptime pillar upon completion.
              </p>
            </div>
          </div>
        )}
      </DetailDrawer>

      {/* Work Order Dialog */}
      <CreateWorkOrderDialog
        open={workOrderOpen}
        onOpenChange={setWorkOrderOpen}
        defaults={workOrderDefaults}
      />
    </div>
  )
}

export function Assets() {
  return (
    <RequireEstate>
      <AssetsContent />
    </RequireEstate>
  )
}

export default Assets
