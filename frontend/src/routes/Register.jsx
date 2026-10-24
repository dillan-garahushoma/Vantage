import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Building2, Check, Search } from 'lucide-react';
import { Keyline } from '../components/Brand';
import { AuthShell } from '../components/AuthShell';
import { Button, EmptyState, ErrorState, Field, Input, LoadingState } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';
import { listPublicEstates } from '../lib/publicDirectory';
import { clearSelectedPublicEstate, rememberPublicEstate, selectedPublicEstate } from '../lib/publicEstateSelection';
import { useAsync } from '../lib/useAsync';

const ACCOUNT_TYPES = [
  {
    value: 'resident',
    label: 'Resident',
    blurb: 'I live in a complex and want to manage my requests and stay informed.',
  },
  {
    value: 'estate_admin',
    label: 'HOA / estate manager',
    blurb: 'I manage estate operations, residents and maintenance.',
  },
  {
    value: 'service_provider',
    label: 'Service provider',
    blurb: 'I complete maintenance work assigned by an estate.',
  },
  {
    value: 'estate_admin',
    label: 'HOA / estate manager',
    description: 'Create a private workspace for a new estate you manage.',
  },
  {
    value: 'service_provider',
    label: 'Service provider',
    description: 'Apply to an estate. Its HOA reviews your details before account setup.',
  },
];

const PROVINCES = [
  'Eastern Cape',
  'Free State',
  'Gauteng',
  'KwaZulu-Natal',
  'Limpopo',
  'Mpumalanga',
  'North West',
  'Northern Cape',
  'Western Cape',
];

const EMPTY = {
  accountType: 'resident',
  full_name: '',
  email: '',
  password: '',
  phoneno: '',
  unit_no: '',
  estateName: '',
  estateSuburb: '',
  estateCity: '',
  estateProvince: 'Gauteng',
  estateDescription: '',
};

function validate(form, selectedEstate = null) {
  const errors = {};
  if (form.full_name.trim().length < 2) errors.full_name = 'Enter your full name.';
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) errors.email = 'Enter a valid email address.';
  if (form.password.length < 8) errors.password = 'Use at least 8 characters.';
  if (new TextEncoder().encode(form.password).length > 72) errors.password = 'Password must not exceed 72 bytes.';
  if (selectedEstate && form.unit_no.trim().length === 0) {
    errors.unit_no = 'Enter the unit number for the complex you selected.';
  } else if (form.unit_no.trim().length > 10) {
    errors.unit_no = 'Unit numbers are at most 10 characters.';
  }
  return errors;
}

/**
 * Public registration deliberately creates residents only. A selected estate is
 * onboarding context and is never included as proof of access in the auth call.
 */
export function registrationPayload(form) {
  const payload = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    password: form.password,
    account_type: 'resident',
  };
  const phone = form.phoneno.trim();
  if (phone) payload.phoneno = phone;
  const unitNo = form.unit_no.trim();
  if (unitNo) payload.unit_no = unitNo;
  return payload;
}

function ExistingSession({ user, onSwitchAccount, onContinue }) {
  return (
    <AuthShell
      eyebrow="Your VALORA session"
      title="You're already signed in."
      intro="You can continue to your current workspace or safely switch accounts. You don't need to reopen registration to change users."
      cardTitle="Current account"
    >
      <div className="space-y-4">
        <div className="border-l-2 border-accent bg-canvas px-4 py-3">
          <p className="font-medium text-ink">{user.full_name}</p>
          <p className="mt-1 text-sm text-ink-muted">{user.email}</p>
          <p className="mt-2 text-xs text-ink-muted">Access comes from your approved estate membership.</p>
        </div>
        <Button type="button" variant="primary" className="w-full" onClick={onContinue}>
          Continue to VALORA
        </Button>
        <Button type="button" variant="secondary" className="w-full" onClick={onSwitchAccount}>
          Sign out and use another account
        </Button>
      </div>
    </AuthShell>
  );
}

function EstatePicker({ value, onSelect, onClear, query, onQueryChange, committedQuery, onSearch, directory }) {
  const items = directory.data?.items ?? [];

  return (
    <section className="border-y border-ink/15 py-4" aria-labelledby="register-estate-heading">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center bg-accent-wash text-accent-ink">
          <Building2 className="h-4 w-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="register-estate-heading" className="text-sm font-semibold text-ink">
            Which complex do you live in?
            <span className="ml-2 text-xs font-normal text-ink-muted">Optional</span>
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-ink-muted">
            Choose a published complex now to carry it into your access request. Your estate office still has to approve your membership.
          </p>
        </div>
      </div>

      {value ? (
        <div className="mt-4 flex items-start gap-3 border-l-2 border-accent bg-accent-wash/45 px-3.5 py-3">
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent-ink" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-ink">{value.name}</p>
            <p className="mt-0.5 text-xs text-ink-muted">{value.location || 'Location not available'}</p>
            <p className="mt-1 text-xs text-ink-soft">You will confirm your unit and request access after creating your account.</p>
          </div>
          <button type="button" onClick={onClear} className="shrink-0 text-xs font-semibold text-accent-ink underline underline-offset-2">
            Change
          </button>
        </div>
      ) : (
        <>
          <div className="mt-4 flex gap-2">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
              <Input
                aria-label="Search published complexes"
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    onSearch();
                  }
                }}
                placeholder="Complex name, suburb or city"
                className="pl-9"
                autoComplete="off"
              />
            </div>
            <Button type="button" variant="secondary" onClick={onSearch}>
              Search
            </Button>
          </div>

          <div className="mt-3" aria-live="polite">
            {directory.loading ? (
              <LoadingState label="Loading published complexes" />
            ) : directory.error ? (
              <ErrorState
                title="Complexes could not be loaded"
                message={directory.error.message}
                requestId={directory.error.requestId}
                action={<Button type="button" variant="secondary" onClick={directory.reload}>Try again</Button>}
              />
            ) : items.length === 0 ? (
              <EmptyState
                title={committedQuery ? 'No published complex matches' : 'No complexes are published yet'}
                body={committedQuery
                  ? 'Try another name, suburb, city or province. Private or unpublished estates cannot appear in this public selector.'
                  : 'The selector only lists complexes whose administrators have enabled their public profile. You can continue and ask your estate office for a join code.'}
              />
            ) : (
              <ul className="divide-y divide-ink/10">
                {items.map((item) => (
                  <li key={item.estate_id}>
                    <button
                      type="button"
                      onClick={() => onSelect({
                        estate_id: item.estate_id,
                        name: item.name,
                        location: [item.suburb, item.city, item.province].filter(Boolean).join(', '),
                        suburb: item.suburb,
                        city: item.city,
                        province: item.province,
                      })}
                      className="group flex w-full items-center justify-between gap-3 py-3 text-left transition-colors hover:bg-accent-wash/35 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
                    >
                      <span className="flex min-w-0 items-start gap-3">
                        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center bg-ink/5 text-ink-muted">
                          <Building2 className="h-4 w-4" aria-hidden="true" />
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-ink group-hover:text-accent-ink">{item.name}</span>
                          <span className="mt-0.5 block truncate text-xs text-ink-muted">
                            {[item.suburb, item.city, item.province].filter(Boolean).join(', ')}
                            {item.unit_count != null ? ` · ${item.unit_count} units` : ''}
                          </span>
                        </span>
                      </span>
                      <ArrowRight className="h-4 w-4 shrink-0 text-ink-muted group-hover:text-accent-ink" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export function Register() {
  const { user, register, logout } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [estateQuery, setEstateQuery] = useState('');
  const [committedEstateQuery, setCommittedEstateQuery] = useState('');
  const [selectedEstate, setSelectedEstate] = useState(() => selectedPublicEstate());
  const directory = useAsync(
    () => listPublicEstates({ q: committedEstateQuery, page: 1, page_size: 6 }),
    [committedEstateQuery],
  );

  function update(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
    setError(null);
  }

  function switchAccount() {
    logout();
    setSwitchingAccount(true);
    setError(null);
  }

  function clearEstate() {
    setSelectedEstate(null);
    clearSelectedPublicEstate();
    setErrors((previous) => ({ ...previous, unit_no: undefined }));
  }

  function chooseEstate(estate) {
    setSelectedEstate(estate);
    rememberPublicEstate(estate, form.unit_no);
    setErrors((previous) => ({ ...previous, unit_no: undefined }));
    setError(null);
  }

  function switchAccount() {
    logout();
    navigate('/login', { replace: true });
  }

  async function submit(event) {
    event.preventDefault();
    if (form.accountType !== 'resident') return;
    const found = validate(form, selectedEstate);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    setError(null);
    try {
      if (selectedEstate) {
        rememberPublicEstate(selectedEstate, form.unit_no.trim());
      } else {
        clearSelectedPublicEstate();
      }
      await register(registrationPayload(form));
      navigate(selectedEstate ? '/request-access' : '/welcome', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Registration failed.'));
    } finally {
      setBusy(false);
    }
  }

  if (user) {
    return (
      <ExistingSession
        user={user}
        onSwitchAccount={switchAccount}
        onContinue={() => navigate('/welcome', { replace: true })}
      />
    );
  }

  const selectedPath = ACCOUNT_TYPES.find((item) => item.value === form.accountType);

  return (
    <AuthShell
      eyebrow="Estate access"
      step={1}
      totalSteps={3}
      stepLabels={['Account', 'Join estate', "You're in"]}
      title="Find your way into VALORA."
      intro="Choose the path that fits your role. Residents can create an account here; estate management and provider access must be provisioned by an authorised administrator."
    >
      <div className="space-y-5">
        <fieldset>
          <legend className="mb-3 text-sm font-semibold text-ink">How will you use VALORA?</legend>
          <div className="space-y-2">
            {ACCOUNT_TYPES.map((item) => {
              const id = `account_type_${item.value}`;
              const selected = form.accountType === item.value;
              return (
                <label
                  key={item.value}
                  className={[
                    'block cursor-pointer border px-3.5 py-3 transition-colors duration-150',
                    'focus-within:outline-2 focus-within:outline-dotted focus-within:outline-accent focus-within:outline-offset-2',
                    selected ? 'border-accent bg-accent-wash/60' : 'border-ink/15 bg-surface hover:border-ink/35',
                  ].join(' ')}
                >
                  <span className="flex items-start gap-3">
                    <input
                      id={id}
                      type="radio"
                      name="account_type"
                      value={item.value}
                      aria-describedby={`${id}_blurb`}
                      checked={selected}
                      onChange={() => {
                        update('accountType', item.value);
                        setErrors({});
                        setError(null);
                      }}
                      className="mt-1 h-4 w-4 shrink-0 accent-accent"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-ink">{item.label}</span>
                      <span id={`${id}_blurb`} className="mt-1 block text-xs leading-relaxed text-ink-muted">
                        {item.blurb}
                      </span>
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <Keyline />

        {form.accountType === 'resident' ? (
          <>
            <form className="space-y-4" onSubmit={submit} noValidate>
              {error ? (
                <ErrorState title="Could not create the account" message={error.message} requestId={error.requestId} />
              ) : null}

              <Field label="Full name" error={errors.full_name}>
                <Input name="full_name" autoComplete="name" value={form.full_name}
                  onChange={(event) => update('full_name', event.target.value)} placeholder="Thandi Nkosi" required />
              </Field>

              <Field label="Email address" error={errors.email}>
                <Input type="email" name="email" autoComplete="email" value={form.email}
                  onChange={(event) => update('email', event.target.value)} placeholder="you@example.co.za" required />
              </Field>

              <Field label="Password" error={errors.password} hint="At least 8 characters.">
                <Input type="password" name="password" autoComplete="new-password" value={form.password}
                  onChange={(event) => update('password', event.target.value)} required />
              </Field>

              <EstatePicker
                value={selectedEstate}
                onSelect={chooseEstate}
                onClear={clearEstate}
                query={estateQuery}
                onQueryChange={setEstateQuery}
                committedQuery={committedEstateQuery}
                onSearch={() => setCommittedEstateQuery(estateQuery.trim())}
                directory={directory}
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Phone (optional)">
                  <Input name="phoneno" autoComplete="tel" value={form.phoneno}
                    onChange={(event) => update('phoneno', event.target.value)} placeholder="082 000 0000" />
                </Field>
                <Field label="Unit number" error={errors.unit_no} hint={selectedEstate ? 'Required for the access request; the estate office confirms it.' : 'Optional now, or confirm it when requesting estate access.'}>
                  <Input name="unit_no" value={form.unit_no} maxLength={10}
                    onChange={(event) => update('unit_no', event.target.value)} placeholder="A-101" />
                </Field>
              </div>

              <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
                {busy ? 'Creating account…' : 'Create resident account'}
              </Button>
            </form>

            <p className="text-[13px] text-ink-muted">
              Already registered? <Link to="/login" className="font-medium text-accent-ink hover:underline">Sign in</Link>.
            </p>
          </>
        ) : (
          <div role="status" className="border-l-2 border-accent bg-canvas p-4">
            <p className="text-sm font-semibold text-ink">
              {form.accountType === 'estate_admin' ? 'Estate management access is authorised by VALORA.' : 'Provider access is assigned by the estate.'}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">
              {form.accountType === 'estate_admin'
                ? 'To protect resident and operational records, an HOA administrator account must be provisioned and attached to its estate. Contact the VALORA team to arrange access.'
                : 'Service-provider accounts must be linked to an approved provider profile and estate membership. Ask your estate office to invite or provision your account.'}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link to="/contact" className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-ink">
                Contact VALORA
              </Link>
              <Link to="/login" className="inline-flex items-center justify-center border border-ink/15 bg-surface px-4 py-2 text-sm font-medium text-ink hover:border-ink/35">
                Already have access? Sign in
              </Link>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-ink-muted">
              Selecting this path does not grant a role or estate access by itself.
            </p>
          </div>
        )}
        <p className="text-xs text-ink-muted">
          {selectedPath?.label} selected. Access is always checked against your account and estate membership.
        </p>
      </div>
    </AuthShell>
  );
}
