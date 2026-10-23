import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { AuthShell } from '../components/AuthShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';

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
];

const EMPTY = {
  accountType: 'resident',
  full_name: '',
  email: '',
  password: '',
  phoneno: '',
  unit_no: '',
};

function validate(form) {
  const errors = {};
  if (form.full_name.trim().length < 2) errors.full_name = 'Enter your full name.';
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) errors.email = 'Enter a valid email address.';
  if (form.password.length < 8) errors.password = 'Use at least 8 characters.';
  if (new TextEncoder().encode(form.password).length > 72) errors.password = 'Password must not exceed 72 bytes.';
  return errors;
}

/**
 * Public registration deliberately creates residents only.
 * The selected account path is UI guidance; it never grants a privileged role.
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

export function Register() {
  const { user, register, logout } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  function update(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  function switchAccount() {
    logout();
    navigate('/login', { replace: true });
  }

  async function submit(event) {
    event.preventDefault();
    if (form.accountType !== 'resident') return;
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    setError(null);
    try {
      await register(registrationPayload(form));
      navigate('/welcome', { replace: true });
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

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Phone (optional)">
                  <Input name="phoneno" autoComplete="tel" value={form.phoneno}
                    onChange={(event) => update('phoneno', event.target.value)} placeholder="082 000 0000" />
                </Field>
                <Field label="Unit number (optional)" hint="You can confirm this when joining.">
                  <Input name="unit_no" value={form.unit_no}
                    onChange={(event) => update('unit_no', event.target.value)} placeholder="HR-01" />
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
