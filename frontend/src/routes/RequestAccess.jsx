import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { Button, Card, Chip, EmptyState, ErrorState, Field, Input, LoadingState, SectionTitle, Textarea, } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstate } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { fullDate } from '../lib/format';
import { listPublicEstates } from '../lib/publicDirectory';
import { clearSelectedPublicEstate, selectedPublicEstate } from '../lib/publicEstateSelection';
import { asResidencyStatus, listMyResidencyRequests, RESIDENCY_STATUS, submitResidencyRequest, } from '../lib/residency';
import { useAsync } from '../lib/useAsync';
function location(item) {
    const parts = [item.suburb, item.city].filter(Boolean);
    return parts.length > 0 ? parts.join(', ') : item.province;
}
/**
 * The approval-based way onto an estate.
 *
 * A resident finds their complex, names their unit, and submits. Nothing is
 * granted here: the request is recorded pending and an estate administrator
 * decides it. The estate is chosen from the published directory, because the
 * resident has no membership to resolve an estate from yet — and the server
 * re-checks that the estate and the unit exist regardless of what was picked.
 */
export function RequestAccess() {
    const { user } = useAuth();
    const { reload: reloadEstates } = useEstate();
    const [query, setQuery] = useState('');
    const [committed, setCommitted] = useState('');
    const [picked, setPicked] = useState(() => selectedPublicEstate());
    const [unitNo, setUnitNo] = useState('');
    const [note, setNote] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [submitted, setSubmitted] = useState(null);
    const [fieldError, setFieldError] = useState(null);
    const directory = useAsync(() => listPublicEstates({ q: committed, page: 1, page_size: 8 }), [committed]);
    const mine = useAsync(() => listMyResidencyRequests(), []);
    if (!user)
        return <Navigate to="/login" replace state={{ from: '/request-access' }}/>;
    async function search(event) {
        event.preventDefault();
        setCommitted(query.trim());
    }
    async function submit(event) {
        event.preventDefault();
        if (!picked) {
            setFieldError('Choose your complex first.');
            return;
        }
        if (unitNo.trim().length === 0) {
            setFieldError('Enter your unit number.');
            return;
        }
        setFieldError(null);
        setBusy(true);
        setError(null);
        setSubmitted(null);
        try {
            await submitResidencyRequest({
                estate_id: picked.estate_id,
                unit_no: unitNo.trim(),
                note: note.trim() || null,
            });
            setSubmitted(picked.name);
            setPicked(null);
            clearSelectedPublicEstate();
            setUnitNo('');
            setNote('');
            // The request may have just been approved for a unit that was already
            // granted; reloading keeps the rest of the app honest either way.
            mine.reload();
            reloadEstates();
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not submit the request.'));
        }
        finally {
            setBusy(false);
        }
    }
    const items = directory.data?.items ?? [];
    const requests = mine.data ?? [];
    return (<PublicShell>
      <div className="mx-auto grid max-w-[1040px] gap-10 px-5 py-14 lg:grid-cols-[1fr_1.05fr]">
        <div className="min-w-0">
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Resident onboarding
          </p>
          <h1 className="mt-3 text-[32px] leading-tight font-semibold">
            Ask to join your estate
          </h1>
          <p className="mt-3 max-w-md text-[14.5px] text-ink-soft">
            Send your details to the estate office. They review the request against their unit
            register, then approve or decline it. You will not have access until they approve it.
          </p>
          <p className="mt-3 max-w-md text-[13px] text-ink-muted">
            Already have a join code from your estate office?{' '}
            <Link to="/join" className="font-medium text-accent-ink hover:underline">
              Redeem it instead
            </Link>{' '}
            — a code is approved instantly.
          </p>

          {mine.error ? null : (<div className="mt-8">
              <SectionTitle title="Your requests" hint="Newest first"/>
              {mine.loading ? (<LoadingState label="Loading your requests"/>) : requests.length === 0 ? (<p className="text-[13px] text-ink-muted">
                  You have not requested access to a complex yet.
                </p>) : (<ul className="space-y-2.5">
                  {requests.map((request) => {
                    const status = asResidencyStatus(request.status);
                    const meta = RESIDENCY_STATUS[status];
                    return (<li key={request.request_id}>
                        <Card className="p-3.5">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-[13.5px] font-medium">
                              {request.estate_name ?? `Estate #${request.estate_id}`}
                            </span>
                            <Chip tone={meta.tone}>{meta.label}</Chip>
                          </div>
                          <p className="num mt-1 text-[11.5px] text-ink-muted">
                            unit {request.unit_no} · submitted {fullDate(request.created_at)}
                            {request.decided_at ? ` · decided ${fullDate(request.decided_at)}` : ''}
                          </p>
                          <p className="mt-1.5 text-[12.5px] text-ink-soft">{meta.hint}</p>
                          {request.decision_note ? (<p className="mt-1 text-[12.5px] text-ink-soft">
                              Note from the estate: {request.decision_note}
                            </p>) : null}
                        </Card>
                      </li>);
                })}
                </ul>)}
            </div>)}
        </div>

        <Card className="min-w-0 self-start p-6">
          <h2 className="text-[16px] font-semibold">Find your complex</h2>
          <Keyline className="mt-3"/>

          <form className="mt-5 space-y-4" onSubmit={submit} noValidate>
            {error ? (<ErrorState title={error.status === 409
                ? 'You cannot request this one'
                : error.status === 404
                    ? 'We could not find that'
                    : error.status === 429
                        ? 'Too many attempts'
                        : 'Could not submit the request'} message={error.message} requestId={error.requestId}/>) : null}
            {submitted ? (<div className="hairline rounded-xs border-l-2 border-l-accent bg-accent-wash px-3.5 py-3">
                <p className="text-[13.5px] font-medium text-accent-ink">
                  Request sent to {submitted}
                </p>
                <p className="mt-1 text-[12.5px] text-ink-soft">
                  It is awaiting review. You will see the outcome above as soon as an administrator
                  decides it.
                </p>
              </div>) : null}

            <div>
              <span className="mb-1.5 block text-[12px] font-medium tracking-wide text-ink-soft uppercase">
                Complex
              </span>
              {picked ? (<div className="hairline flex items-center justify-between gap-3 rounded-xs bg-surface px-3 py-2">
                  <span className="min-w-0">
                    <span className="block truncate text-[13.5px] font-medium">{picked.name}</span>
                    <span className="num block truncate text-[11.5px] text-ink-muted">
                      {picked.location}
                    </span>
                  </span>
                  <Button type="button" variant="ghost" onClick={() => setPicked(null)}>
                    Change
                  </Button>
                </div>) : (<>
                  <div className="flex gap-2">
                    <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name, suburb or city" aria-label="Search the published complexes"/>
                    <Button type="button" variant="secondary" onClick={search}>
                      Search
                    </Button>
                  </div>

                  <div className="mt-3">
                    {directory.loading ? (<LoadingState label="Searching complexes"/>) : directory.error ? (<ErrorState message={directory.error.message} requestId={directory.error.requestId} action={<Button variant="secondary" onClick={directory.reload}>
                            Try again
                          </Button>}/>) : items.length === 0 ? (<EmptyState title="No published complex matches" body="Only complexes that publish a public profile appear here. If yours is missing, ask your estate office for a join code."/>) : (<ul className="space-y-2">
                        {items.map((item) => (<li key={item.estate_id}>
                            <button type="button" onClick={() => setPicked({
                        estate_id: item.estate_id,
                        name: item.name,
                        location: location(item),
                    })} className="hairline w-full rounded-xs bg-surface px-3 py-2.5 text-left transition-colors hover:border-accent">
                              <span className="block text-[13.5px] font-medium">{item.name}</span>
                              <span className="num mt-0.5 block text-[11.5px] text-ink-muted">
                                {location(item)} · {item.unit_count ?? 0} units
                              </span>
                            </button>
                          </li>))}
                      </ul>)}
                  </div>
                </>)}
            </div>

            <Field label="Unit number" error={fieldError && fieldError.includes('unit') ? fieldError : undefined} hint="As it appears on your lease, for example A-101.">
              <Input name="unit_no" value={unitNo} maxLength={10} onChange={(event) => setUnitNo(event.target.value)} placeholder="A-101"/>
            </Field>

            <Field label="Note to the estate office (optional)" hint="Max 500 characters.">
              <Textarea name="note" value={note} maxLength={500} onChange={(event) => setNote(event.target.value)} placeholder="I moved in on 1 November and the lease is in my name."/>
            </Field>

            {fieldError && !fieldError.includes('unit') ? (<p className="text-[12px] text-signal-ink">{fieldError}</p>) : null}

            <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
              {busy ? 'Sending request…' : 'Send request for approval'}
            </Button>
          </form>

          <p className="mt-5 text-[12.5px] text-ink-muted">
            Your name and email on this account are what the estate office sees. There is nothing
            else to fill in, and no code to find.
          </p>
        </Card>
      </div>
    </PublicShell>);
}
