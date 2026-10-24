import { useState } from 'react';
import { RequireEstate } from '../components/RequireEstate';
import { IconUsers } from '../components/Icons';
import { Button, Card, Chip, Drawer, EmptyState, ErrorState, Field, LoadingState, SectionTitle, Select, TableShell, Td, Th, } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { approveProviderApplication, listEstateMembers, listEstateProperties, listProviderApplications, rejectProviderApplication, removeEstateMember, transferEstateMemberUnit } from '../lib/estateAdmin';
import { roleLabels } from '../lib/display';
import { fullDate, relativeDays } from '../lib/format';
import { useAsync } from '../lib/useAsync';
/** The plain-language role name, with a fallback for a role the UI does not know. */
function roleName(role) {
    return roleLabels[role] ?? role.replace(/[_-]+/g, ' ');
}
const ROLE_FILTERS = ['', 'resident', 'service_provider', 'hoa_admin'];
function roleTone(role) {
    if (role === 'hoa_admin')
        return 'progress';
    if (role === 'service_provider')
        return 'warn';
    return 'neutral';
}
/* ------------------------------------------------ review provider applicants */
function ProviderApplications({ estateId }) {
    const [busyId, setBusyId] = useState(null);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    const applications = useAsync(() => listProviderApplications(estateId, 'pending'), [estateId]);
    async function decide(applicationId, decision) {
        setError(null);
        setNotice('');
        setBusyId(applicationId);
        try {
            if (decision === 'approve')
                await approveProviderApplication(estateId, applicationId);
            else
                await rejectProviderApplication(estateId, applicationId);
            setNotice(decision === 'approve'
                ? 'Setup link sent to the applicant.'
                : 'Application declined.');
            applications.reload();
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not review this application.'));
        }
        finally {
            setBusyId(null);
        }
    }
    const items = applications.data ?? [];
    return (
      <Card as="section" className="p-5">
        <SectionTitle title="Provider applications" hint="Approve an applicant to email a secure account-setup link." />
        {notice ? <p className="mb-3 text-sm text-ink-soft" role="status">{notice}</p> : null}
        {error ? <ErrorState title="Could not review application" message={error.message} requestId={error.requestId} /> : null}
        {applications.loading ? <LoadingState label="Loading provider applications" />
          : applications.error ? <ErrorState title="Could not load applications" message={applications.error.message} requestId={applications.error.requestId} action={<Button variant="secondary" onClick={applications.reload}>Try again</Button>} />
            : items.length === 0 ? <EmptyState title="No applications awaiting review" body="Provider applications for this estate will appear here." />
              : <ul className="divide-y divide-ink/10">
                {items.map((application) => (
                  <li key={application.application_id} className="flex flex-wrap items-start justify-between gap-4 py-4 first:pt-2">
                    <div className="min-w-0">
                      <p className="font-medium">{application.full_name}</p>
                      <p className="text-[13px] text-ink-muted">{application.email} · {application.trade} · {application.phone}</p>
                      {application.note ? <p className="mt-2 max-w-2xl text-[13px] text-ink-soft">{application.note}</p> : null}
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Button variant="secondary" disabled={busyId !== null} onClick={() => decide(application.application_id, 'reject')}>
                        {busyId === application.application_id ? 'Saving…' : 'Decline'}
                      </Button>
                      <Button variant="primary" disabled={busyId !== null} onClick={() => decide(application.application_id, 'approve')}>
                      {busyId === application.application_id ? 'Sending…' : 'Approve and send setup link'}
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>}
      </Card>
    );
}
/* --------------------------------------------------------------- removal */
function RemoveMemberDrawer({ target, estateName, busy, error, onCancel, onConfirm, }) {
    return (<Drawer open={target !== null} onClose={onCancel} title="Move this member out?" subtitle={target ? `${target.full_name ?? target.email ?? `membership #${target.membership_id}`} · ${roleName(target.role)}` : undefined} footer={<div className="flex flex-wrap items-center gap-2">
          <Button variant="danger" onClick={onConfirm} disabled={busy}>
            {busy ? 'Moving out…' : 'Move out of the estate'}
          </Button>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Keep the member
          </Button>
        </div>}>
      {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
      <div className="space-y-3 text-[13.5px] text-ink-soft">
        <p>
          This ends their access to <span className="font-medium text-ink">{estateName}</span>{' '}
          immediately: the estate disappears from their account and every estate-scoped request they
          make is refused.
        </p>
        <p className="text-[13px]">
          What this does <span className="font-medium">not</span> do:
        </p>
        <ul className="ml-4 list-disc space-y-1.5 text-[13px]">
          <li>It does not delete their account — they can still sign in, and a new code can re-add them.</li>
          <li>
            It does not erase history. Complaints they filed, work orders already recorded against
            them, and audit events stay on the estate’s record.
          </li>
          <li>
            It does not cancel a join code they hold. If the code is still live, they can redeem it
            again — rotate the code if that matters.
          </li>
        </ul>
      </div>
    </Drawer>);
}
function TransferUnitDrawer({ target, estateId, onCancel, onDone }) {
    const [propertyId, setPropertyId] = useState('');
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const properties = useAsync(() => target
        ? listEstateProperties(estateId)
        : Promise.resolve(null), [estateId, target?.membership_id]);
    async function submit() {
        if (!target || !propertyId)
            return;
        setBusy(true);
        setError(null);
        try {
            await transferEstateMemberUnit(estateId, target.membership_id, Number(propertyId));
            onDone();
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not move this resident.'));
        }
        finally {
            setBusy(false);
        }
    }
    return (<Drawer open={target !== null} onClose={onCancel} title="Move resident to another unit" subtitle={target?.full_name ?? target?.email ?? undefined} footer={<div className="flex gap-2"><Button variant="ghost" onClick={onCancel} disabled={busy}>Cancel</Button><Button variant="primary" onClick={submit} disabled={busy || !propertyId}>{busy ? 'Moving…' : 'Move resident'}</Button></div>}>
      <div className="space-y-4">
        {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
        <p className="text-sm leading-relaxed text-ink-muted">This changes the resident’s current unit access and preserves an audit trail of the move. It does not erase their maintenance history.</p>
        {properties.loading ? <LoadingState label="Loading units"/> : properties.error ? <ErrorState message={properties.error.message} requestId={properties.error.requestId}/> : <Field label="New unit"><Select value={propertyId} onChange={(event) => setPropertyId(event.target.value)}><option value="">Select a unit</option>{properties.data?.items?.map((property) => <option key={property.id} value={property.id}>{property.unit_no}{property.street_address ? ` · ${property.street_address}` : ''}</option>)}</Select></Field>}
      </div>
    </Drawer>);
}
/* ----------------------------------------------------------------- screen */
function MembersBody() {
    const { estateId, estate } = useEstateScope();
    const { user } = useAuth();
    const scope = estateId ?? 0;
    const isAdmin = user?.role === 'hoa_admin';
    const [role, setRole] = useState('');
    const [page, setPage] = useState(1);
    const [target, setTarget] = useState(null);
    const [transferTarget, setTransferTarget] = useState(null);
    const [busy, setBusy] = useState(false);
    const [removeError, setRemoveError] = useState(null);
    const members = useAsync(() => isAdmin && scope
        ? listEstateMembers(scope, { role: role || undefined, page, page_size: 20 })
        : Promise.resolve(null), [scope, role, page, isAdmin]);
    async function confirmRemove() {
        if (!target || !scope)
            return;
        setBusy(true);
        setRemoveError(null);
        try {
            await removeEstateMember(scope, target.membership_id);
            setTarget(null);
            members.reload();
        }
        catch (cause) {
            setRemoveError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not remove that member.'));
        }
        finally {
            setBusy(false);
        }
    }
    if (!isAdmin) {
        return (<ErrorState title="The estate register is an HOA administrator’s view" message="You are a member of this estate, but not its administrator. Membership records name people, so only the estate office can read them."/>);
    }
    const items = members.data?.items ?? [];
    const pages = members.data?.pages ?? 0;
    return (<div className="space-y-5">
      <header>
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
          Estate register
        </p>
        <h1 className="mt-2 text-[26px] leading-tight font-semibold">Members</h1>
        <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
          Who may act inside this estate. Residents join through approval or a live join code;
          service providers apply and receive account access only after HOA approval.
          Moving someone out revokes estate access.
        </p>
      </header>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="min-w-[14rem] flex-1">
          <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Role
          </span>
          <Select value={role} onChange={(event) => {
            setRole(event.target.value);
            setPage(1);
        }}>
            {ROLE_FILTERS.map((value) => (<option key={value || 'all'} value={value}>
                {value ? roleName(value) : 'All roles'}
              </option>))}
          </Select>
        </label>
        <p className="num pb-2 text-[12.5px] text-ink-muted">
          {members.data?.total ?? 0} {members.data?.total === 1 ? 'member' : 'members'}
        </p>
      </Card>

      {members.loading ? (<LoadingState label="Loading the estate register"/>) : members.error ? (<ErrorState title="Could not read the estate register" message={members.error.message} requestId={members.error.requestId} action={<Button variant="secondary" onClick={members.reload}>
              Try again
            </Button>}/>) : items.length === 0 ? (<EmptyState title={role ? 'Nobody holds that role yet' : 'This estate has no members yet'} body={role
                ? 'Clear the role filter to see everyone on the register.'
                : 'Issue a join code so residents can join, or review provider applications.'}/>) : (<>
          <TableShell>
            <thead>
              <tr>
                <Th>Member</Th>
                <Th className="w-40">Role</Th>
                <Th className="w-24">Unit</Th>
                <Th className="w-36">Joined</Th>
                <Th className="w-32 text-right">Access</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((member) => (<tr key={member.membership_id}>
                  <Td>
                    <span className="font-medium">{member.full_name ?? '—'}</span>
                    <span className="num mt-0.5 block text-[11.5px] text-ink-muted">
                      {member.email ?? 'no email on record'}
                    </span>
                  </Td>
                  <Td>
                    <Chip tone={roleTone(member.role)}>{roleName(member.role)}</Chip>
                  </Td>
                  <Td className="num">{member.unit_no ?? '—'}</Td>
                  <Td>
                    <span className="block text-[13px]">{fullDate(member.joined_at)}</span>
                    <span className="num block text-[11.5px] text-ink-muted">
                      {relativeDays(member.joined_at)}
                    </span>
                  </Td>
                  <Td className="text-right">
                    {member.role === 'hoa_admin' ? (<span className="text-[12px] text-ink-muted">
                        Administrator — remove from the estate profile
                      </span>) : (<div className="flex justify-end gap-2">{member.role === 'resident' ? <Button variant="secondary" onClick={() => setTransferTarget(member)}>Move unit</Button> : null}<Button variant="secondary" onClick={() => {
                        setRemoveError(null);
                        setTarget({
                            membership_id: member.membership_id,
                            full_name: member.full_name ?? null,
                            email: member.email ?? null,
                            role: member.role,
                        });
                    }}>
                        Move out
                      </Button></div>)}
                  </Td>
                </tr>))}
            </tbody>
          </TableShell>

          <div className="flex items-center justify-between gap-3">
            <p className="num text-[12px] text-ink-muted">
              page {members.data?.page ?? 1} of {Math.max(pages, 1)}
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button variant="secondary" disabled={page >= Math.max(pages, 1)} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        </>)}

      <ProviderApplications estateId={scope} />

      <Card as="section" className="p-5">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xs bg-accent-wash text-accent-ink">
            <IconUsers size={18}/>
          </span>
          <div>
            <h2 className="text-[14.5px] font-semibold">How people get in</h2>
            <ul className="mt-2 space-y-1.5 text-[13px] text-ink-soft">
              <li>
                <span className="font-medium">Residents</span> either request access and are approved
                on the Approvals screen, or redeem a join code against their unit number, which is
                instant. Both produce the same membership.
              </li>
              <li>
                <span className="font-medium">Service providers</span> apply to an estate. The HOA
                reviews each application and approves account setup before work can be assigned.
              </li>
              <li>
                <span className="font-medium">Managers</span> are provisioned by an operator and hold
                matching estate membership before they can manage this register.
              </li>
            </ul>
          </div>
        </div>
      </Card>

      <RemoveMemberDrawer target={target} estateName={estate?.estate_name ?? 'this estate'} busy={busy} error={removeError} onCancel={() => setTarget(null)} onConfirm={confirmRemove}/>
      <TransferUnitDrawer target={transferTarget} estateId={scope} onCancel={() => setTransferTarget(null)} onDone={() => { setTransferTarget(null); members.reload(); }}/>
    </div>);
}
export function Members() {
    return (<RequireEstate>
      <MembersBody />
    </RequireEstate>);
}
