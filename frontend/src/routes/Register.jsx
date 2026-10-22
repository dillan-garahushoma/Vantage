import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { OnboardingShell } from '../components/OnboardingShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';

const ACCOUNT_TYPES = [
  {
    value: 'resident',
    label: 'Resident',
    blurb: 'Live in the estate. You join with a code from your estate office.',
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
  if (form.full_name.trim().length < 2)
    errors.full_name = 'Enter your full name.';
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim()))
    errors.email = 'Enter a valid email address.';
  if (form.password.length < 8)
    errors.password = 'Use at least 8 characters.';
  if (new TextEncoder().encode(form.password).length > 72)
    errors.password = 'Password must not exceed 72 bytes.';
  return errors;
}

/**
 * The request body for the chosen account type — nothing else is ever sent.
 *
 * Optional fields are omitted rather than sent empty, so the object that leaves
 * this function is exactly the JSON on the wire.
 */
export function registrationPayload(form) {
  const payload = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    password: form.password,
    account_type: 'resident',
  };
  const phone = form.phoneno.trim();
  if (phone)
    payload.phoneno = phone;
  // A resident request never carries an estate or a provider object.
  const unitNo = form.unit_no.trim();
  if (unitNo)
    payload.unit_no = unitNo;
  return payload;
}

export function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  // Registration lands on /welcome, which resolves where the account belongs from
  // its memberships: a resident has no estate yet, so they are sent to /join.
  if (user)
    return <Navigate to="/welcome" replace />;

  function update(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0)
      return;
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

  return (
    <OnboardingShell
      step={1}
      totalSteps={3}
      stepLabels={['Account', 'Join estate', "You're in"]}
      title="Create your account"
      subtitle="Resident accounts join an estate with a code from your estate office."
    >
      <div className="space-y-5">
        <div>
          <fieldset>
            <legend className="sr-only">Account type</legend>
            <div className="space-y-2.5">
              {ACCOUNT_TYPES.map((item) => {
                const id = `account_type_${item.value}`;
                return (
                  <label
                    key={item.value}
                    className={
                      (form.accountType === item.value
                        ? 'hairline rounded-xs block cursor-pointer border-accent bg-surface p-3.5'
                        : 'hairline rounded-xs block cursor-pointer bg-surface p-3.5 hover:border-ink/40') +
                      ' has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-dotted has-[:focus-visible]:outline-accent has-[:focus-visible]:outline-offset-2'
                    }
                  >
                    <span className="flex items-center gap-2.5">
                      <input
                        id={id}
                        type="radio"
                        name="account_type"
                        value={item.value}
                        aria-labelledby={`${id}_title`}
                        aria-describedby={`${id}_blurb`}
                        checked={form.accountType === item.value}
                        onChange={() => {
                          update('accountType', item.value);
                          setErrors({});
                          setError(null);
                        }}
                        className="h-4 w-4 shrink-0 accent-[#1F6F5C]"
                      />
                      <span id={`${id}_title`} className="text-[14px] font-medium">
                        {item.label}
                      </span>
                    </span>
                    <span
                      id={`${id}_blurb`}
                      className="mt-1.5 block pl-6.5 text-[12.5px] text-ink-muted"
                    >
                      {item.blurb}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
          <p className="mt-2 text-[12.5px] text-ink-muted">
            Resident accounts join an apartment complex through its estate office. The estate office
            provisions manager and provider accounts separately.
          </p>
        </div>

        <Keyline />

        <form className="space-y-4" onSubmit={submit} noValidate>
          {error ? (
            <ErrorState
              title="Could not create the account"
              message={error.message}
              requestId={error.requestId}
            />
          ) : null}

          <Field label="Full name" error={errors.full_name}>
            <Input
              name="full_name"
              autoComplete="name"
              value={form.full_name}
              onChange={(event) => update('full_name', event.target.value)}
              placeholder="Thandi Nkosi"
            />
          </Field>

          <Field label="Email address" error={errors.email}>
            <Input
              type="email"
              name="email"
              autoComplete="email"
              value={form.email}
              onChange={(event) => update('email', event.target.value)}
              placeholder="you@example.co.za"
            />
          </Field>

          <Field label="Password" error={errors.password} hint="At least 8 characters.">
            <Input
              type="password"
              name="password"
              autoComplete="new-password"
              value={form.password}
              onChange={(event) => update('password', event.target.value)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Phone (optional)">
              <Input
                name="phoneno"
                autoComplete="tel"
                value={form.phoneno}
                onChange={(event) => update('phoneno', event.target.value)}
                placeholder="082 000 0000"
              />
            </Field>

            <Field label="Unit number (optional)" hint="Helps your HOA match you.">
              <Input
                name="unit_no"
                value={form.unit_no}
                onChange={(event) => update('unit_no', event.target.value)}
                placeholder="HR-01"
              />
            </Field>
          </div>

          <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
            {busy ? 'Creating account…' : 'Create account'}
          </Button>
        </form>

        <p className="text-[13px] text-ink-muted">
          Already registered?{' '}
          <Link to="/login" className="font-medium text-accent-ink hover:underline">
            Sign in
          </Link>
          .
        </p>
      </div>
    </OnboardingShell>
  );
}
