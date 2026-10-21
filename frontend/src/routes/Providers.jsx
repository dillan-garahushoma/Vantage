import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { IconShield, IconStar, IconUsers } from '../components/Icons';
import { RequireEstate } from '../components/RequireEstate';
import { Button, Card, Chip, EmptyState, ErrorState, LoadingState, Select, TableShell, Td, Th, } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { trades } from '../lib/display';
import { titleCase } from '../lib/format';
import { useAsync } from '../lib/useAsync';
function Stars({ rating }) {
    if (rating === null)
        return <span className="num text-ink-muted">—</span>;
    const rounded = Math.round(rating);
    return (<span className="inline-flex items-center gap-0.5" aria-label={`${rating} out of 5`}>
      {[1, 2, 3, 4, 5].map((step) => (<span key={step} className={step <= rounded ? 'text-accent-ink' : 'text-ink/20'}>
          <IconStar size={13} filled={step <= rounded}/>
        </span>))}
      <span className="num ml-1.5 text-[12px]">{rating.toFixed(2)}</span>
    </span>);
}
function ProvidersBody() {
    const { user } = useAuth();
    const isAdmin = user?.role === 'hoa_admin';
    // The triage panel links here with `?trade=…`, so the filter can arrive preset.
    const [searchParams] = useSearchParams();
    const [trade, setTrade] = useState(() => searchParams.get('trade') ?? '');
    const [verifiedOnly, setVerifiedOnly] = useState(false);
    const [emergencyOnly, setEmergencyOnly] = useState(false);
    const [page, setPage] = useState(1);
    const providers = useAsync(() => isAdmin
        ? api.get('/api/v1/providers', {
            page,
            size: 20,
            trade: trade || undefined,
            verified: verifiedOnly ? true : undefined,
            emergency_available: emergencyOnly ? true : undefined,
        })
        : Promise.resolve(null), [page, trade, verifiedOnly, emergencyOnly, isAdmin]);
    if (!isAdmin) {
        return (<ErrorState title="The provider directory is HOA-only" message="Service provider records are visible to the estate's HOA administrator. Residents raise issues through complaints; the HOA assigns a verified provider from here."/>);
    }
    const items = providers.data?.items ?? [];
    const pages = providers.data?.pages ?? 0;
    return (<div className="space-y-5">
      <header>
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
          Verified capability
        </p>
        <h1 className="mt-2 text-[26px] leading-tight font-semibold">Service providers</h1>
        <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
          Better contractors resolve issues faster, and faster resolution lifts the estate’s health.
          Verification and ratings exist so assignment is an evidence-based decision, not word of
          mouth.
        </p>
      </header>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="min-w-[11rem] flex-1">
          <span className="mb-1.5 block text-[11px] font-medium tracking-wider text-ink-muted uppercase">
            Trade
          </span>
          <Select value={trade} onChange={(event) => {
            setTrade(event.target.value);
            setPage(1);
        }}>
            <option value="">All trades</option>
            {trades.map((item) => (<option key={item} value={item}>
                {titleCase(item)}
              </option>))}
          </Select>
        </label>

        <label className="flex items-center gap-2 pb-2 text-[12.5px] text-ink-soft">
          <input type="checkbox" checked={verifiedOnly} onChange={(event) => {
            setVerifiedOnly(event.target.checked);
            setPage(1);
        }} className="h-4 w-4 accent-[#1F6F5C]"/>
          Verified only
        </label>

        <label className="flex items-center gap-2 pb-2 text-[12.5px] text-ink-soft">
          <input type="checkbox" checked={emergencyOnly} onChange={(event) => {
            setEmergencyOnly(event.target.checked);
            setPage(1);
        }} className="h-4 w-4 accent-[#1F6F5C]"/>
          Emergency available
        </label>

        <p className="num pb-2 text-[12.5px] text-ink-muted">
          {providers.data?.total ?? 0} providers
        </p>
      </Card>

      {providers.loading ? (<LoadingState label="Loading providers"/>) : providers.error ? (<ErrorState message={providers.error.message} requestId={providers.error.requestId}/>) : items.length === 0 ? (<EmptyState title="No providers match these filters" body="Clear the filters, or add verified contractors to the directory before assigning work orders."/>) : (<>
          <TableShell>
            <thead>
              <tr>
                <Th>Provider</Th>
                <Th className="w-32">Trade</Th>
                <Th className="w-44">Rating</Th>
                <Th className="w-24 text-right">Reviews</Th>
                <Th className="w-40">Status</Th>
                <Th className="w-36">Contact</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((provider) => (<tr key={provider.id}>
                  <Td>
                    <span className="font-medium">{provider.full_name}</span>
                    <span className="num mt-0.5 block text-[11.5px] text-ink-muted">
                      provider #{provider.id}
                    </span>
                  </Td>
                  <Td className="text-ink-soft">{titleCase(provider.trade)}</Td>
                  <Td>
                    <Stars rating={provider.avg_rating === null ? null : Number(provider.avg_rating)}/>
                  </Td>
                  <Td className="num text-right">{provider.total_reviews ?? 0}</Td>
                  <Td>
                    <span className="flex flex-wrap gap-1.5">
                      {provider.verified ? (<Chip tone="good" glyph="✓">
                          Verified
                        </Chip>) : (<Chip tone="warn" glyph="◷">
                          Unverified
                        </Chip>)}
                      {provider.emergency_available ? <Chip tone="alert" glyph="!">Emergency</Chip> : null}
                    </span>
                  </Td>
                  <Td>
                    <span className="num block text-[12px]">{provider.phone}</span>
                    <span className="block truncate text-[11.5px] text-ink-muted">
                      {provider.email}
                    </span>
                  </Td>
                </tr>))}
            </tbody>
          </TableShell>

          <div className="flex items-center justify-between gap-3">
            <p className="num text-[12px] text-ink-muted">
              page {providers.data?.page ?? 1} of {Math.max(pages, 1)}
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

      <div className="grid gap-4 sm:grid-cols-3">
        {[
            {
                icon: <IconShield size={18}/>,
                title: 'Verification gates assignment',
                body: 'Only verified providers should be assigned work orders, so the record stays defensible.',
            },
            {
                icon: <IconStar size={18}/>,
                title: 'Ratings feed the score',
                body: 'Resident ratings on completed work orders are one of the five Living Score factors.',
            },
            {
                icon: <IconUsers size={18}/>,
                title: 'Scoped to the estate',
                body: 'Provider lists are resolved against your HOA membership in this estate, not a client id.',
            },
        ].map((note) => (<Card key={note.title} className="p-4">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xs bg-accent-wash text-accent-ink">
              {note.icon}
            </span>
            <h3 className="mt-3 text-[14px] font-semibold">{note.title}</h3>
            <p className="mt-1 text-[12.5px] text-ink-soft">{note.body}</p>
          </Card>))}
      </div>
    </div>);
}
export function Providers() {
    return (<RequireEstate>
      <ProvidersBody />
    </RequireEstate>);
}
