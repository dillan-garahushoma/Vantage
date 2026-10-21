import { useState } from 'react';
import { RequireEstate } from '../components/RequireEstate';
import { IconPlus, IconUsers } from '../components/Icons';
import { Button, Card, Chip, Drawer, EmptyState, ErrorState, Field, Input, LoadingState, SectionTitle, Select, TableShell, Td, Th, } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { addProviderMember, listEstateMembers, removeEstateMember } from '../lib/estateAdmin';
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
/* ------------------------------------------------------- add a provider */
function AddProviderCard({ estateId, onAdded }) {
    const [email, setEmail] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [added, setAdded] = useState(null);
    async function submit(event) {
        event.preventDefault();
        setError(null);
        setAdded(null);
        setBusy(true);
        try {
            const member = await addProviderMember(estateId, email);
            setAdded(member.full_name ?? member.email ?? email);
            setEmail('');
            onAdded();
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not add that provider.'));
        }
        finally {
            setBusy(false);
        }
    }
    const title = error?.status === 409
        ? 'That provider is already a member'
        : error?.status === 429
            ? 'Too many lookup attempts'
            : error?.status === 404
                ? 'No registered provider with that email'
                : 'Could not add that provider';
    return (<Card as="section" className="p-5">
      <SectionTitle title="Add a service provider" hint="They register themselves; you link their account to this estate by email."/>
      <form onSubmit={submit} className="space-y-3">
        {error ? (<ErrorState title={title} message={error.status === 404
                ? `${error.message} A provider must first create their own VALORA account, and that account must carry a trade profile. Residents are not added here — they request access for approval, or join with a code.`
                : error.message} requestId={error.requestId}/>) : null}
        {added ? (<p className="text-[13px] text-accent-ink">
            {added} can now be assigned work in this estate.
          </p>) : null}

        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[16rem] flex-1">
            <Field label="Provider email" hint="Only an account that registered as a service provider, with a trade profile, can be added.">
              <Input name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="plumber@example.co.za" autoComplete="off"/>
            </Field>
          </div>
          <Button type="submit" variant="primary" disabled={busy || email.trim().length === 0}>
            <IconPlus size={16}/>
            {busy ? 'Adding…' : 'Add provider'}
          </Button>
        </div>
      </form>
    </Card>);
}
/* --------------------------------------------------------------- removal */
function RemoveMemberDrawer({ target, estateName, busy, error, onCancel, onConfirm, }) {
    return (<Drawer open={target !== null} onClose={onCancel} title="Remove this member?" subtitle={target ? `${target.full_name ?? target.email ?? `membership #${target.membership_id}`} · ${roleName(target.role)}` : undefined} footer={<div className="flex flex-wrap items-center gap-2">
          <Button variant="danger" onClick={onConfirm} disabled={busy}>
            {busy ? 'Removing…' : 'Remove from the estate'}
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
/* ----------------------------------------------------------------- screen */
function MembersBody() {
    const { estateId, estate } = useEstateScope();
    const { user } = useAuth();
    const scope = estateId ?? 0;
    const isAdmin = user?.role === 'hoa_admin';
    const [role, setRole] = useState('');
    const [page, setPage] = useState(1);
    const [target, setTarget] = useState(null);
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
          Who may act inside this estate, and how they got in. A resident gets here either by being
          approved on the Approvals screen or by redeeming a live join code against their unit; a
          provider you add by email is added immediately. Removing someone here is the revocation.
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
                : 'Issue a join code so residents can join, or add a service provider by email.'}/>) : (<>
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
                      </span>) : (<Button variant="secondary" onClick={() => {
                        setRemoveError(null);
                        setTarget({
                            membership_id: member.membership_id,
                            full_name: member.full_name ?? null,
                            email: member.email ?? null,
                            role: member.role,
                        });
                    }}>
                        Remove
                      </Button>)}
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

      <AddProviderCard estateId={scope} onAdded={() => {
            setRole('');
            setPage(1);
            members.reload();
        }}/>

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
                <span className="font-medium">Service providers</span> register themselves, then you
                add their email here. Only then can they be assigned work.
              </li>
              <li>
                <span className="font-medium">HOA administrators</span> come with the estate itself —
                the account that registered the estate is its first administrator.
              </li>
            </ul>
          </div>
        </div>
      </Card>

      <RemoveMemberDrawer target={target} estateName={estate?.estate_name ?? 'this estate'} busy={busy} error={removeError} onCancel={() => setTarget(null)} onConfirm={confirmRemove}/>
    </div>);
}
export function Members() {
    return (<RequireEstate>
      <MembersBody />
    </RequireEstate>);
}
