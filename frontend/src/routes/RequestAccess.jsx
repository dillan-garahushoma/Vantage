import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  SectionTitle,
  Textarea,
} from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstate } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { fullDate } from '../lib/format';
import { listPublicEstates } from '../lib/publicDirectory';
import { clearSelectedPublicEstate, selectedPublicEstate } from '../lib/publicEstateSelection';
import {
  asResidencyStatus,
  listMyResidencyRequests,
  RESIDENCY_STATUS,
  submitResidencyRequest,
} from '../lib/residency';
import { useAsync } from '../lib/useAsync';

function location(item) {
  const parts = [item.suburb, item.city].filter(Boolean);
  return parts.length > 0 ? parts.join(', ') : item.province;
}

/**
 * The approval-based way onto an estate.
 *
 * A resident finds their complex and submits their contact details for review.
 * Nothing is granted here: an estate administrator decides the request. A unit number
 * is optional — residents can submit with their unit number or request approval
 * without one.
 */
export function RequestAccess() {
  const { user } = useAuth();
  const { reload: reloadEstates } = useEstate();
  const [query, setQuery] = useState('');
  const [committed, setCommitted] = useState('');
  const [picked, setPicked] = useState(() => selectedPublicEstate());
  const [unitNo, setUnitNo] = useState(() => selectedPublicEstate()?.unit_no ?? '');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(null);
  const [fieldError, setFieldError] = useState(null);

  const directory = useAsync(
    () => listPublicEstates({ q: committed, page: 1, page_size: 8 }),
    [committed],
  );
  const mine = useAsync(() => listMyResidencyRequests(), []);

  if (!user) return <Navigate to="/register" replace state={{ from: '/request-access' }} />;

  async function search(event) {
    event.preventDefault();
    setCommitted(query.trim());
  }

  async function submit(event, explicitUnitNo) {
    if (event) event.preventDefault();
    if (!picked) {
      setFieldError('Choose your complex first.');
      return;
    }
    const effectiveUnit = explicitUnitNo !== undefined ? explicitUnitNo : unitNo;
    const trimmedUnit = (effectiveUnit ?? '').trim();
    if (trimmedUnit.length > 10) {
      setFieldError('Unit numbers are at most 10 characters.');
      return;
    }
    setFieldError(null);
    setBusy(true);
    setError(null);
    setSubmitted(null);
    try {
      const payload = {
        estate_id: picked.estate_id,
        note: note.trim() || null,
      };
      if (trimmedUnit) {
        payload.unit_no = trimmedUnit;
      }
      await submitResidencyRequest(payload);
      setSubmitted(picked.name);
      setPicked(null);
      clearSelectedPublicEstate();
      setUnitNo('');
      setNote('');
      mine.reload();
      reloadEstates();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause : new ApiError(0, 'Could not submit the request.'),
      );
    } finally {
      setBusy(false);
    }
  }

  const items = directory.data?.items ?? [];
  const requests = mine.data ?? [];

  return (
    <AuthShell
      eyebrow="Resident onboarding"
      title="Ask to join your estate"
      intro="Send your details to the estate office. You will not have access until they approve it. Providing a unit number is optional — you can submit with your unit number or request approval without one."
      points={[
        ['Approval, not self-selection', 'The estate office decides who can enter its workspace.'],
        [
          'Unit number optional',
          'Enter your unit if known, or request approval without a unit and let the office assign it.',
        ],
      ]}
      aside={
        <>
          <p className="mt-4 max-w-md text-[13px] text-ink-muted">
            Already have a join code from your estate office?{' '}
            <Link to="/join" className="font-medium text-accent-ink hover:underline">
              Redeem it instead
            </Link>{' '}
            — a code is approved instantly.
          </p>

          {mine.error ? null : (
            <div className="mt-8">
              <SectionTitle title="Your requests" hint="Newest first" />
              {mine.loading ? (
                <LoadingState label="Loading your requests" />
              ) : requests.length === 0 ? (
                <p className="text-[13px] text-ink-muted">
                  You have not requested access to a complex yet.
                </p>
              ) : (
                <ul className="space-y-2.5">
                  {requests.map((request) => {
                    const status = asResidencyStatus(request.status);
                    const meta = RESIDENCY_STATUS[status];
                    return (
                      <li key={request.request_id}>
                        <Card className="p-3.5">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-[13.5px] font-medium">
                              {request.estate_name ?? `Estate #${request.estate_id}`}
                            </span>
                            <Chip tone={meta.tone}>{meta.label}</Chip>
                          </div>
                          <p className="num mt-1 text-[11.5px] text-ink-muted">
                            {request.unit_no
                              ? `unit ${request.unit_no} · `
                              : 'Unit to be assigned · '}
                            submitted {fullDate(request.created_at)}
                            {request.decided_at ? ` · decided ${fullDate(request.decided_at)}` : ''}
                          </p>
                          <p className="mt-1.5 text-[12.5px] text-ink-soft">{meta.hint}</p>
                          {status === 'approved' ? (
                            <Link
                              to="/app"
                              className="mt-2 inline-flex text-[12.5px] font-medium text-accent-ink hover:underline"
                            >
                              Enter estate
                            </Link>
                          ) : null}
                          {request.decision_note ? (
                            <p className="mt-1 text-[12.5px] text-ink-soft">
                              Note from the estate: {request.decision_note}
                            </p>
                          ) : null}
                        </Card>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </>
      }
    >
      <form className="space-y-4" onSubmit={submit} noValidate>
        {error ? (
          <ErrorState
            title={
              error.status === 409
                ? 'You cannot request this one'
                : error.status === 404
                  ? 'We could not find that'
                  : error.status === 429
                    ? 'Too many attempts'
                    : 'Could not submit the request'
            }
            message={error.message}
            requestId={error.requestId}
            action={
              error.status === 404 && unitNo.trim() ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setUnitNo('');
                    submit(null, '');
                  }}
                >
                  Submit without unit number
                </Button>
              ) : undefined
            }
          />
        ) : null}
        {submitted ? (
          <div className="hairline rounded-xs border-l-2 border-l-accent bg-accent-wash px-3.5 py-3">
            <p className="text-[13.5px] font-medium text-accent-ink">Request sent to {submitted}</p>
            <p className="mt-1 text-[12.5px] text-ink-soft">
              It is awaiting review. You will see the outcome above as soon as an administrator
              decides it.
            </p>
          </div>
        ) : null}

        <div>
          <span className="mb-1.5 block text-[12px] font-medium tracking-wide text-ink-soft uppercase">
            Complex
          </span>
          {picked ? (
            <div className="hairline flex items-center justify-between gap-3 rounded-xs bg-surface px-3 py-2">
              <span className="min-w-0">
                <span className="block truncate text-[13.5px] font-medium">{picked.name}</span>
                <span className="num block truncate text-[11.5px] text-ink-muted">
                  {picked.location}
                </span>
              </span>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setPicked(null);
                  setUnitNo('');
                  clearSelectedPublicEstate();
                }}
              >
                Change
              </Button>
            </div>
          ) : (
            <>
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      setCommitted(query.trim());
                    }
                  }}
                  placeholder="Search by name, suburb or city"
                  aria-label="Search the published complexes"
                />
                <Button type="button" variant="secondary" onClick={search}>
                  Search
                </Button>
              </div>

              <div className="mt-3">
                {directory.loading ? (
                  <LoadingState label="Searching published complexes" />
                ) : directory.error ? (
                  <ErrorState
                    title="Could not load published complexes"
                    message={directory.error.message}
                    requestId={directory.error.requestId}
                    action={
                      <Button variant="secondary" onClick={directory.reload}>
                        Try again
                      </Button>
                    }
                  />
                ) : items.length === 0 ? (
                  <EmptyState
                    title={
                      committed ? 'No published complex matches' : 'No complexes are published yet'
                    }
                    body={
                      committed
                        ? 'Try another name, suburb, city or province. Private and unpublished estates cannot appear in the public selector; ask your estate office for a join code.'
                        : 'The selector only lists estates that have enabled their public profile. You can search again or ask your estate office for a join code.'
                    }
                  />
                ) : (
                  <ul className="space-y-2">
                    {items.map((item) => (
                      <li key={item.estate_id}>
                        <button
                          type="button"
                          onClick={() =>
                            setPicked({
                              estate_id: item.estate_id,
                              name: item.name,
                              location: location(item),
                            })
                          }
                          className="hairline w-full rounded-xs bg-surface px-3 py-2.5 text-left transition-colors hover:border-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                        >
                          <span className="block text-[13.5px] font-medium">{item.name}</span>
                          <span className="num mt-0.5 block text-[11.5px] text-ink-muted">
                            {location(item)} · {item.unit_count ?? 0} units
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>

        <Field
          label="Unit number (optional)"
          error={fieldError && fieldError.includes('unit') ? fieldError : undefined}
          hint="As it appears on your lease (e.g. A-101). Leave blank if unassigned or to request approval without a unit."
        >
          <Input
            name="unit_no"
            value={unitNo}
            maxLength={10}
            onChange={(event) => {
              setUnitNo(event.target.value);
              if (fieldError && fieldError.includes('unit')) setFieldError(null);
            }}
            placeholder="e.g. A-101 (optional)"
            aria-label="Unit number (optional)"
          />
        </Field>

        <Field label="Note to the estate office (optional)" hint="Max 500 characters.">
          <Textarea
            name="note"
            value={note}
            maxLength={500}
            onChange={(event) => setNote(event.target.value)}
            placeholder="I moved in on 1 November and the lease is in my name."
          />
        </Field>

        {fieldError && !fieldError.includes('unit') ? (
          <p className="text-[12px] text-signal-ink">{fieldError}</p>
        ) : null}

        <div className="space-y-2">
          <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
            {busy ? 'Sending request…' : 'Send request for approval'}
          </Button>
          {unitNo.trim() ? (
            <Button
              type="button"
              variant="ghost"
              className="w-full text-[13px] text-ink-muted hover:text-ink"
              disabled={busy}
              onClick={() => {
                setUnitNo('');
                submit(null, '');
              }}
            >
              Request approval without a unit number
            </Button>
          ) : null}
        </div>
      </form>

      <p className="mt-5 text-[12.5px] text-ink-muted">
        Your name and email on this account are what the estate office sees. A unit number is not
        compulsory to request access and can be assigned by the estate office upon review.
      </p>
    </AuthShell>
  );
}
