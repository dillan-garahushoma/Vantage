import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthShell, SignedInAccountActions } from '../components/AuthShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';

const ACCOUNT_TYPES = [
  {
    value: 'resident',
    label: 'Resident',
    description: 'Join with a code from your estate office.',
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
  if (form.accountType === 'estate_admin') {
    if (form.estateName.trim().length < 2)
      errors.estateName = "Enter the estate\u2019s name.";
    if (!form.estateSuburb.trim())
      errors.estateSuburb = 'Enter the suburb.';
    if (!form.estateCity.trim())
      errors.estateCity = 'Enter the city.';
    if (!form.estateProvince.trim())
      errors.estateProvince = 'Choose a province.';
  }
  return errors;
}

export function registrationPayload(form) {
  const payload = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    password: form.password,
    account_type: 'resident',
  };
  const phone = form.phoneno.trim();
  const unitNo = form.unit_no.trim();
  if (phone)
    payload.phoneno = phone;
  if (unitNo)
    payload.unit_no = unitNo;
  return payload;
}

export function estateOnboardingPayload(form) {
  const description = form.estateDescription.trim();
  return {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    password: form.password,
    ...(form.phoneno.trim() ? { phoneno: form.phoneno.trim() } : {}),
    estate: {
      name: form.estateName.trim(),
      suburb: form.estateSuburb.trim(),
      city: form.estateCity.trim(),
      province: form.estateProvince.trim(),
      ...(description ? { description } : {}),
    },
  };
}

export function Register() {
  const { user, logout, register, registerEstate } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [switchingAccount, setSwitchingAccount] = useState(false);
  const signedIn = Boolean(user) && !switchingAccount;
  const provider = form.accountType === 'service_provider';
  const estateAdmin = form.accountType === 'estate_admin';

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

  async function submit(event) {
    event.preventDefault();
    if (provider)
      return;
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0)
      return;

    setBusy(true);
    setError(null);
    try {
      if (estateAdmin)
        await registerEstate(estateOnboardingPayload(form));
      else
        await register(registrationPayload(form));
      navigate('/welcome', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Registration failed.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Estate access"
      title={signedIn ? "You're signed in" : 'Create your account'}
      intro={
        signedIn
          ? 'Continue to your workspace or sign out to use a different account.'
          : 'Choose the account path that matches how you use your estate.'
      }
      cardTitle={
        signedIn
          ? 'Current account'
          : provider
            ? 'Provider access'
            : estateAdmin
              ? 'Create an estate workspace'
              : 'Resident account'
      }
      footer={
        !signedIn && !provider ? (
          <p className="mt-5 text-[13px] text-ink-muted">
            Already registered?{' '}
            <Link to="/login" className="font-medium text-accent-ink hover:underline">
              Sign in
            </Link>
            .
          </p>
        ) : null
      }
    >
      {signedIn ? (
        <SignedInAccountActions
          user={user}
          onSwitch={switchAccount}
          continueTo="/welcome"
        />
      ) : (
        <div className="space-y-5">
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
                        aria-describedby={`${id}_description`}
                        checked={form.accountType === item.value}
                        onChange={() => {
                          update('accountType', item.value);
                          setErrors({});
                        }}
                        className="h-4 w-4 shrink-0 accent-brand"
                      />
                      <span id={`${id}_title`} className="text-[14px] font-medium">
                        {item.label}
                      </span>
                    </span>
                    <span
                      id={`${id}_description`}
                      className="mt-1.5 block pl-6.5 text-[12.5px] text-ink-muted"
                    >
                      {item.description}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          {provider ? (
            <div className="rounded-sm border border-accent/30 bg-accent-wash/60 p-4">
              <p className="text-[14px] font-medium text-accent-ink">
                Apply to the estate where you want to work.
              </p>
              <p className="mt-1.5 text-[13px] leading-5 text-ink-soft">
                The HOA reviews your application. If approved, you receive a secure link to set up your account and estate access.
              </p>
              <Link
                to="/provider/apply"
                className="mt-3 inline-flex min-h-11 items-center justify-center rounded-sm bg-accent px-4 py-2.5 text-[14px] font-medium text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Apply to an estate
              </Link>
            </div>
          ) : (
            <>
              <div className="border-t border-ink/10" />
              <form className="space-y-4" onSubmit={submit} noValidate>
                {error ? (
                  <ErrorState
                    title={estateAdmin ? 'Could not create the estate workspace' : 'Could not create the account'}
                    message={error.message}
                    requestId={error.requestId}
                  />
                ) : null}

                <Field label="Full name" error={errors.full_name}>
                  <Input
                    name="full_name"
                    autoComplete="name"
                    required
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
                    required
                    value={form.email}
                    onChange={(event) => update('email', event.target.value)}
                    placeholder="you@example.co.za"
                  />
                </Field>

                <Field label="Password" error={errors.password} hint="Use at least 8 characters.">
                  <Input
                    type="password"
                    name="password"
                    autoComplete="new-password"
                    required
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
                  {!estateAdmin ? (
                    <Field label="Unit number (optional)" hint="Helps your HOA match you.">
                      <Input
                        name="unit_no"
                        value={form.unit_no}
                        onChange={(event) => update('unit_no', event.target.value)}
                        placeholder="A-101"
                      />
                    </Field>
                  ) : null}
                </div>

                {estateAdmin ? (
                  <div className="space-y-4 border-t border-ink/15 pt-4">
                    <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                      Estate details
                    </p>
                    <Field label="Estate name" error={errors.estateName}>
                      <Input
                        name="estate_name"
                        required
                        value={form.estateName}
                        onChange={(event) => update('estateName', event.target.value)}
                        placeholder="Ridge Close Estate"
                      />
                    </Field>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Field label="Suburb" error={errors.estateSuburb}>
                        <Input
                          name="estate_suburb"
                          required
                          value={form.estateSuburb}
                          onChange={(event) => update('estateSuburb', event.target.value)}
                          placeholder="Centurion"
                        />
                      </Field>
                      <Field label="City" error={errors.estateCity}>
                        <Input
                          name="estate_city"
                          required
                          value={form.estateCity}
                          onChange={(event) => update('estateCity', event.target.value)}
                          placeholder="Tshwane"
                        />
                      </Field>
                    </div>
                    <Field label="Province" error={errors.estateProvince}>
                      <select
                        name="estate_province"
                        value={form.estateProvince}
                        onChange={(event) => update('estateProvince', event.target.value)}
                        className="min-h-11 w-full rounded-xs border border-line bg-surface px-3 py-2 text-[14px] text-ink focus:border-accent focus:outline-none"
                      >
                        {PROVINCES.map((province) => (
                          <option key={province} value={province}>
                            {province}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Description (optional)">
                      <textarea
                        name="estate_description"
                        value={form.estateDescription}
                        maxLength={5000}
                        rows={3}
                        onChange={(event) => update('estateDescription', event.target.value)}
                        placeholder="A short description of your estate."
                        className="w-full resize-y rounded-xs border border-line bg-surface px-3 py-2 text-[14px] text-ink focus:border-accent focus:outline-none"
                      />
                    </Field>
                    <p className="text-[12.5px] leading-5 text-ink-muted">
                      Your estate starts private. You can publish it to the directory later.
                    </p>
                  </div>
                ) : null}

                <Button
                  type="submit"
                  variant="primary"
                  className="min-h-11 w-full py-2.5"
                  disabled={busy}
                >
                  {busy
                    ? estateAdmin
                      ? 'Creating workspace…'
                      : 'Creating account…'
                    : estateAdmin
                      ? 'Create estate workspace'
                      : 'Create resident account'}
                </Button>
              </form>
            </>
          )}
        </div>
      )}
    </AuthShell>
  );
}
