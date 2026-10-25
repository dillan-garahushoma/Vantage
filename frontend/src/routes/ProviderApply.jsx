import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { Button, ErrorState, Field, Input, LoadingState, Select } from '../components/ui';
import { api, ApiError } from '../lib/api';
import { listPublicEstates } from '../lib/publicDirectory';
import { useAsync } from '../lib/useAsync';

const EMPTY = { estate_id: '', full_name: '', email: '', trade: '', phone: '', note: '' };

export function ProviderApply() {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const navigate = useNavigate();
  const directory = useAsync(() => listPublicEstates({ page: 1, page_size: 100 }), []);

  function update(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }));
    setError(null);
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.applyAsProvider({
        ...form,
        estate_id: Number(form.estate_id),
      });
      setSubmitted(true);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not submit your application.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Provider application"
      title={submitted ? 'Application sent' : 'Apply to work with an estate'}
      intro={submitted
        ? 'The estate administrator will review your details. If approved, VALORA will email you a secure link to set up your account.'
        : 'Choose the estate you want to work with. Its HOA reviews your application before any account or estate access is created.'}
      cardTitle={submitted ? 'Awaiting HOA review' : 'Your application'}
      footer={!submitted ? (
        <p className="mt-5 text-[13px] text-ink-muted">
          Already have an account? <Link to="/login" className="font-medium text-accent-ink hover:underline">Sign in</Link>.
        </p>
      ) : null}
    >
      {submitted ? (
        <div className="space-y-4">
          <p role="status" className="rounded-sm bg-accent-wash px-3 py-3 text-[13px] text-accent-ink">
            No account has been created yet. The HOA must approve your application first.
          </p>
          <Button type="button" variant="primary" className="w-full" onClick={() => navigate('/')}>
            Return home
          </Button>
        </div>
      ) : directory.loading ? (
        <LoadingState label="Loading estates accepting applications" />
      ) : directory.error ? (
        <ErrorState
          title="Could not load estates"
          message={directory.error.message}
          requestId={directory.error.requestId}
          action={<Button variant="secondary" onClick={directory.reload}>Try again</Button>}
        />
      ) : (
        <form className="space-y-4" onSubmit={submit}>
          {error ? (
            <ErrorState
              title={error.status === 409 ? 'Application not accepted' : 'Could not submit your application'}
              message={error.message}
              requestId={error.requestId}
            />
          ) : null}
          <Field label="Estate">
            <Select required value={form.estate_id} onChange={(event) => update('estate_id', event.target.value)}>
              <option value="">Choose an estate</option>
              {directory.data?.items?.map((estate) => (
                <option key={estate.estate_id} value={estate.estate_id}>
                  {estate.name} · {estate.suburb}, {estate.city}
                </option>
              ))}
            </Select>
            {directory.data?.items?.length === 0 ? (
              <span className="mt-1 block text-[12px] text-ink-muted">
                No estates are currently listed for provider applications.
              </span>
            ) : null}
          </Field>
          <Field label="Full name">
            <Input required autoComplete="name" value={form.full_name} onChange={(event) => update('full_name', event.target.value)} />
          </Field>
          <Field label="Email address">
            <Input required type="email" autoComplete="email" value={form.email} onChange={(event) => update('email', event.target.value)} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Trade">
              <Input required value={form.trade} onChange={(event) => update('trade', event.target.value)} placeholder="Plumbing" />
            </Field>
            <Field label="Phone">
              <Input required type="tel" autoComplete="tel" value={form.phone} onChange={(event) => update('phone', event.target.value)} />
            </Field>
          </div>
          <Field label="Note (optional)">
            <textarea
              value={form.note}
              maxLength={500}
              rows={3}
              onChange={(event) => update('note', event.target.value)}
              className="w-full resize-y rounded-xs border border-line bg-surface px-3 py-2 text-[14px] text-ink focus:border-accent focus:outline-none"
            />
          </Field>
          <Button type="submit" variant="primary" className="w-full min-h-11" disabled={busy || !directory.data?.items?.length}>
            {busy ? 'Submitting…' : 'Submit application'}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
