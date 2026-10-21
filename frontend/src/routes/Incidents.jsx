import { RequireEstate } from '../components/RequireEstate';
import { ErrorState } from '../components/ui';
import { Button } from '../components/ui/button';
import { DataTable } from '../components/valora/DataTable';
import { SectionHeading } from '../components/valora/SectionHeading';
import { StatusChip } from '../components/valora/StatusChip';
import { Surface } from '../components/valora/Surface';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { api } from '../lib/api';
import { displayLabel, relativeDays, fullDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';
/**
 * Incidents on record.
 *
 * The list is what the estate recorded — incidents are the security input of the
 * Living Score, so this screen exists to show them rather than to work them.
 * Categories, severities and statuses are read from the records and rendered
 * through `displayLabel`/`StatusChip`, never against a hand-typed vocabulary, so
 * a value the backend adds appears here without a frontend change.
 *
 * The filters run over the page the API returned; estate scoping and paging stay
 * on the server.
 */
function IncidentsBody() {
    const { estateId, estate } = useEstateScope();
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin';
    const incidents = useAsync(() => estateId === null
        ? Promise.resolve(null)
        : api.get('/api/v1/incidents', {
            estate_id: estateId,
            size: 100,
            sort: '-occurred_at',
        }), [estateId]);
    const rows = incidents.data?.items ?? [];
    const columns = [
        {
            key: 'id',
            header: 'Ref',
            width: '90px',
            render: (row) => <span className="num font-medium">#{row.id}</span>,
        },
        {
            key: 'category',
            header: 'Category',
            sortable: true,
            render: (row) => displayLabel(row.category),
        },
        {
            key: 'severity',
            header: 'Severity',
            sortable: true,
            width: '130px',
            render: (row) => <StatusChip status={row.severity} size="sm"/>,
        },
        {
            key: 'status',
            header: 'Status',
            sortable: true,
            width: '140px',
            render: (row) => <StatusChip status={row.status} size="sm"/>,
        },
        {
            key: 'occurred_at',
            header: 'Occurred',
            sortable: true,
            width: '140px',
            render: (row) => (<span className="num text-ink-muted" title={fullDate(row.occurred_at)}>
          {relativeDays(row.occurred_at)}
        </span>),
        },
        ...(isAdmin
            ? [
                {
                    key: 'property_id',
                    header: 'Unit',
                    align: 'right',
                    width: '100px',
                    hideOnMobile: true,
                    render: (row) => (<span className="num text-ink-muted">
                {row.property_id === null ? 'estate-wide' : `unit #${row.property_id}`}
              </span>),
                },
            ]
            : []),
        {
            key: 'resolved_at',
            header: 'Resolved',
            width: '140px',
            hideOnMobile: !isAdmin,
            render: (row) => (<span className="num text-ink-muted">
          {row.resolved_at ? relativeDays(row.resolved_at) : '—'}
        </span>),
        },
    ];
    return (<div className="space-y-5">
      <SectionHeading eyebrow="Operations" title="Incidents" description="Security and safety incidents recorded for this estate. They are the security input of the Living Score, so they are kept exactly as they were logged."/>

      {isAdmin ? (<Surface className="bg-ink text-white">
          <p className="text-[0.88rem] font-semibold">Recording an incident</p>
          <p className="mt-1 max-w-2xl text-[0.82rem] leading-relaxed text-white/70">
            An incident is written by an estate administrator through the API
            (<code className="num text-[0.78rem]">POST /api/v1/incidents</code>). The capture form is
            not built yet, so this screen is the estate’s record as it stands — and the estate it is
            scoped to ({estate?.estate_name ?? 'none selected'}) is resolved from your membership on
            every read, never from the request.
          </p>
        </Surface>) : null}

      {incidents.loading ? (<p className="text-[0.85rem] text-ink-muted">Loading incidents…</p>) : incidents.error ? (<ErrorState message={incidents.error.message} requestId={incidents.error.requestId} action={<Button variant="secondary" onClick={incidents.reload}>
              Try again
            </Button>}/>) : (<Surface>
          <DataTable columns={columns} rows={rows} rowKey={(row) => row.id} searchKeys={['category', 'severity', 'status']} searchPlaceholder="Search category, severity or status" initialSort={{ key: 'occurred_at', dir: 'desc' }} emptyTitle="No incidents on record" emptyDescription="Nothing has been logged for this estate. An incident is only ever created deliberately — nothing here is inferred from other activity."/>
        </Surface>)}

      <p className="text-[0.72rem] text-ink/35">
        Scope: {estate?.estate_name ?? 'no estate selected'}
        {isAdmin ? '' : ' · unit numbers are shown to estate administrators only'}
      </p>
    </div>);
}
export function Incidents() {
    return (<RequireEstate>
      <IncidentsBody />
    </RequireEstate>);
}
