import { useState } from 'react';
import { IconSearch, IconWrench } from '../components/Icons';
import { RequireEstate } from '../components/RequireEstate';
import { Button, ErrorState, Field, Input, LoadingState, Select, Textarea } from '../components/ui';
import { Button as BrandButton } from '../components/ui/button';
import { Drawer } from '../components/ui/drawer';
import { DataTable } from '../components/valora/DataTable';
import { CreateWorkOrderDialog } from '../components/valora/CreateWorkOrderDialog';
import { SectionHeading } from '../components/valora/SectionHeading';
import { StatusChip } from '../components/valora/StatusChip';
import { Surface } from '../components/valora/Surface';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api, ApiError } from '../lib/api';
import { workOrderStatus } from '../lib/display';
import { fullDate, money, relativeDays, titleCase } from '../lib/format';
import { useAsync } from '../lib/useAsync';
/**
 * One work order, read as a record.
 *
 * An administrator reviews work orders; the assigned provider is the only writer.
 * The panel says that plainly instead of offering controls the API would refuse,
 * and it keeps the evidence — cost, rating, the dates and the completion notes —
 * in one place.
 */
function WorkOrderDrawer({ order, onClose, }) {
    const { estate } = useEstateScope();
    return (<Drawer open={order !== null} onOpenChange={(open) => {
            if (!open)
                onClose();
        }} title={order ? `WO-${String(order.id).padStart(4, '0')}` : ''} subtitle={order
            ? `Complaint #${order.complaint_id} · provider #${order.provider_id} · ${estate?.estate_name ?? 'this estate'}`
            : ''} badge={order ? <StatusChip status={order.status ?? 'assigned'} size="sm"/> : null} footer={<p className="text-[0.75rem] leading-relaxed text-ink/45">
          Progress, cost and completion evidence are updated by the assigned provider from their own
          account. An administrator sees the record; the server refuses an administrator’s write to it.
        </p>}>
      {order ? (<div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {[
                { label: 'Assigned', value: fullDate(order.assigned_at) },
                { label: 'Job cost', value: money(order.job_cost) },
                { label: 'Estimated completion', value: fullDate(order.estimated_completion_date) },
                { label: 'Completed', value: fullDate(order.actual_completion_date) },
            ].map((row) => (<div key={row.label} className="rounded-xl border border-line p-3.5">
                <p className="text-[0.66rem] font-semibold tracking-[0.12em] text-ink/40 uppercase">
                  {row.label}
                </p>
                <p className="num mt-1.5 text-[0.85rem] font-bold text-ink">{row.value}</p>
              </div>))}
          </div>

          <div>
            <p className="text-[0.68rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">
              Resident rating
            </p>
            <p className="mt-2 text-[0.88rem] text-ink/70">
              {order.resident_rating
                ? `${order.resident_rating} / 5 — the resident’s own rating of the completed work.`
                : 'Not rated yet. The rating becomes possible once the work is marked completed.'}
            </p>
          </div>

          <div>
            <p className="text-[0.68rem] font-semibold tracking-[0.14em] text-ink/40 uppercase">
              Completion notes
            </p>
            <p className="mt-2 text-[0.88rem] leading-relaxed whitespace-pre-line text-ink/70">
              {order.completion_notes ?? 'The provider has not recorded completion notes yet.'}
            </p>
          </div>

          <p className="text-[0.75rem] leading-relaxed text-ink/45">
            Resolution time and the resident rating on this work order are the maintenance and
            satisfaction inputs of the estate’s Living Score.
          </p>
        </div>) : null}
    </Drawer>);
}
/* ------------------------------------------------------------ admin view */
function AdminWorkOrders() {
    const { estateId } = useEstateScope();
    const [status, setStatus] = useState('');
    const [page, setPage] = useState(1);
    const [open, setOpen] = useState(null);
    const [creating, setCreating] = useState(false);
    const workOrders = useAsync(() => api.get('/api/v1/work-orders', {
        estate_id: estateId,
        page,
        size: 20,
        sort: '-created_at',
        status: status || undefined,
    }), [estateId, page, status]);
    const items = workOrders.data?.items ?? [];
    const pages = workOrders.data?.pages ?? 0;
    const columns = [
        {
            key: 'id',
            header: 'Ref',
            width: '110px',
            sortable: true,
            render: (row) => (<span className="num font-medium">WO-{String(row.id).padStart(4, '0')}</span>),
        },
        {
            key: 'complaint_id',
            header: 'Complaint',
            width: '120px',
            sortable: true,
            render: (row) => <span className="num text-ink-muted">#{row.complaint_id}</span>,
        },
        {
            key: 'provider_id',
            header: 'Provider',
            width: '120px',
            sortable: true,
            render: (row) => <span className="num text-ink-muted">#{row.provider_id}</span>,
        },
        {
            key: 'status',
            header: 'Status',
            width: '150px',
            sortable: true,
            render: (row) => <StatusChip status={row.status ?? 'assigned'} size="sm"/>,
        },
        {
            key: 'job_cost',
            header: 'Job cost',
            width: '130px',
            align: 'right',
            sortable: true,
            render: (row) => <span className="num">{money(row.job_cost)}</span>,
        },
        {
            key: 'resident_rating',
            header: 'Rating',
            width: '130px',
            align: 'right',
            sortable: true,
            hideOnMobile: true,
            render: (row) => (<span className="num">{row.resident_rating ? `${row.resident_rating} / 5` : '—'}</span>),
        },
        {
            key: 'assigned_at',
            header: 'Assigned',
            width: '120px',
            align: 'right',
            render: (row) => (<span className="num text-ink-muted">{relativeDays(row.assigned_at)}</span>),
        },
    ];
    return (<>
      <Surface>
        <div className="flex flex-wrap items-end gap-4 border-b border-line pb-4">
          <label className="min-w-[12rem] flex-1">
            <span className="mb-1.5 block text-[0.68rem] font-semibold tracking-[0.1em] text-ink/45 uppercase">
              Status
            </span>
            <Select value={status} onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
        }}>
              <option value="">All statuses</option>
              {Object.entries(workOrderStatus).map(([key, meta]) => (<option key={key} value={key}>
                  {meta.label}
                </option>))}
            </Select>
          </label>
          <p className="max-w-md text-[0.75rem] leading-relaxed text-ink/40">
            Assigned providers update progress from their own account. Administrators see the record;
            they do not edit it.
          </p>
        </div>

        {workOrders.loading ? (<LoadingState label="Loading work orders"/>) : workOrders.error ? (<ErrorState message={workOrders.error.message} requestId={workOrders.error.requestId}/>) : (<div className="pt-4">
            <DataTable columns={columns} rows={items} rowKey={(row) => row.id} searchKeys={['status', 'job_cost', 'completion_notes']} searchPlaceholder="Search this page" initialSort={{ key: 'assigned_at', dir: 'desc' }} onRowClick={(row) => setOpen(row)} emptyTitle="No work orders match these filters" emptyDescription="A work order is raised by assigning a provider to a complaint. Clear the filter, or raise one from a complaint that is still open." emptyAction={<BrandButton variant="default" onClick={() => setCreating(true)}>
                  Raise a work order
                </BrandButton>}/>
          </div>)}

        {items.length > 0 ? (<div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
            <p className="num text-[0.75rem] text-ink/40">
              {workOrders.data?.total ?? 0} work orders · page {workOrders.data?.page ?? 1} of{' '}
              {Math.max(pages, 1)}
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button variant="secondary" disabled={page >= Math.max(pages, 1)} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>) : null}
      </Surface>

      <WorkOrderDrawer order={open} onClose={() => setOpen(null)}/>
      <CreateWorkOrderDialog open={creating} onOpenChange={setCreating} onCreated={() => workOrders.reload()}/>
    </>);
}
/* --------------------------------------------------------- provider view */
function ProviderWorkOrders() {
    const { estateId } = useEstateScope();
    const [reference, setReference] = useState('');
    const [order, setOrder] = useState(null);
    const [lookupError, setLookupError] = useState(null);
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState('in_progress');
    const [cost, setCost] = useState('');
    const [notes, setNotes] = useState('');
    const [estimated, setEstimated] = useState('');
    const [saveError, setSaveError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    async function lookup() {
        const id = Number(reference.replace(/\D/g, ''));
        if (!id) {
            setLookupError(new ApiError(0, 'Enter the numeric reference from your assignment.'));
            return;
        }
        setBusy(true);
        setLookupError(null);
        setSaved(false);
        try {
            const found = await api.get(`/api/v1/work-orders/${id}`, { estate_id: estateId });
            setOrder(found);
            setStatus(found.status ?? 'in_progress');
            setCost(found.job_cost ?? '');
            setNotes(found.completion_notes ?? '');
            setEstimated(found.estimated_completion_date ? found.estimated_completion_date.slice(0, 10) : '');
        }
        catch (cause) {
            setOrder(null);
            setLookupError(cause instanceof ApiError
                ? cause
                : new ApiError(0, 'Could not look up that work order.'));
        }
        finally {
            setBusy(false);
        }
    }
    async function save() {
        if (!order)
            return;
        setSaving(true);
        setSaveError(null);
        setSaved(false);
        try {
            const updated = await api.patch(`/api/v1/work-orders/${order.id}`, {
                status,
                job_cost: cost === '' ? null : Number(cost),
                completion_notes: notes.trim() || null,
                estimated_completion_date: estimated ? new Date(estimated).toISOString() : null,
            }, { estate_id: estateId });
            setOrder(updated);
            setSaved(true);
        }
        catch (cause) {
            setSaveError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not update the work order.'));
        }
        finally {
            setSaving(false);
        }
    }
    return (<div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
      <Surface>
        <h2 className="font-heading text-[1rem] font-bold text-ink">Find your assignment</h2>
        <p className="mt-1.5 text-[0.83rem] text-ink-soft">
          Enter the work order reference from your assignment notification. You can only open work
          assigned to your provider profile.
        </p>
        <div className="mt-4 flex gap-2">
          <Input value={reference} onChange={(event) => setReference(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && lookup()} placeholder="WO-0002 or 2" aria-label="Work order reference"/>
          <Button variant="primary" onClick={lookup} disabled={busy}>
            <IconSearch size={16}/>
            {busy ? 'Looking…' : 'Open'}
          </Button>
        </div>

        {lookupError ? (<div className="mt-4">
            <ErrorState message={lookupError.message} requestId={lookupError.requestId}/>
          </div>) : null}

        <div className="mt-5 border-t border-line pt-4">
          <p className="text-[0.78rem] text-ink-muted">
            Assignments are scoped to the estate you are a member of, and to your own provider
            profile. A work order belonging to another provider returns forbidden, not a record.
          </p>
        </div>
      </Surface>

      <Surface>
        {order ? (<>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="num font-heading text-[1rem] font-bold">
                  WO-{String(order.id).padStart(4, '0')}
                </h2>
                <p className="num mt-1 text-[0.78rem] text-ink-muted">
                  complaint #{order.complaint_id} · provider #{order.provider_id}
                </p>
              </div>
              <StatusChip status={order.status ?? 'assigned'} size="sm"/>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-3 border-y border-line py-3">
              <div>
                <dt className="text-[0.68rem] tracking-wider text-ink-muted uppercase">Assigned</dt>
                <dd className="num mt-0.5 text-[0.83rem]">{fullDate(order.assigned_at)}</dd>
              </div>
              <div>
                <dt className="text-[0.68rem] tracking-wider text-ink-muted uppercase">
                  Current cost
                </dt>
                <dd className="num mt-0.5 text-[0.83rem]">{money(order.job_cost)}</dd>
              </div>
            </dl>

            <div className="mt-4 space-y-4">
              {saveError ? <ErrorState message={saveError.message} requestId={saveError.requestId}/> : null}
              {saved ? (<div className="rounded-xl border-l-2 border-l-mint bg-mint-wash px-3.5 py-2.5 text-[0.83rem] text-mint-ink">
                  Work order updated. The estate's maintenance record now reflects this change.
                </div>) : null}

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Status">
                  <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                    {Object.entries(workOrderStatus).map(([key, meta]) => (<option key={key} value={key}>
                        {meta.label}
                      </option>))}
                  </Select>
                </Field>
                <Field label="Job cost (ZAR)">
                  <Input inputMode="decimal" value={cost} onChange={(event) => setCost(event.target.value)} placeholder="2400.00"/>
                </Field>
              </div>

              <Field label="Estimated completion">
                <Input type="date" value={estimated} onChange={(event) => setEstimated(event.target.value)}/>
              </Field>

              <Field label="Completion notes" hint="What was done, parts used, anything the next contractor should know.">
                <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Replaced the failed section of pipe and pressure-tested the line."/>
              </Field>

              <Button variant="primary" onClick={save} disabled={saving}>
                <IconWrench size={16}/>
                {saving ? 'Saving…' : 'Save update'}
              </Button>
            </div>
          </>) : (<div className="flex h-full min-h-48 flex-col items-center justify-center text-center">
            <span className="text-ink-muted">
              <IconWrench size={26}/>
            </span>
            <p className="mt-3 text-[0.88rem] font-medium">No work order open</p>
            <p className="mt-1 max-w-sm text-[0.83rem] text-ink-muted">
              Open an assignment to update its status, cost and completion evidence.
            </p>
          </div>)}
      </Surface>
    </div>);
}
export function WorkOrders() {
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin';
    return (<RequireEstate>
      <div className="space-y-5">
        <SectionHeading eyebrow="Operations" title="Work orders" description={isAdmin
            ? 'Resolution time, cost and provider performance — the operational quality behind the estate’s health.'
            : 'Update the status, cost and completion evidence for work assigned to you.'}/>

        {isAdmin ? <AdminWorkOrders /> : <ProviderWorkOrders />}

        {!isAdmin ? (<p className="text-[0.75rem] text-ink-muted">
            Note for the pilot: {titleCase('service_provider')} accounts cannot list all work orders
            yet — assignments are opened by reference. A “my assignments” feed is part of the next
            build.
          </p>) : null}
      </div>
    </RequireEstate>);
}
