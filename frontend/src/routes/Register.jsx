import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthShell, SignedInAccountActions } from '../components/AuthShell';
import { Button, ErrorState, Field, Input, Select, Textarea, cx } from '../components/ui';
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

const STEP_LABELS = ['Access', 'Your details', 'Finish'];
const IDENTITY_FIELDS = ['full_name', 'email', 'password'];
const ESTATE_FIELDS = ['estateName', 'estateSuburb', 'estateCity', 'estateProvince'];

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

/** The subset of validation that belongs to the fields a step actually shows. */
function pick(errors, keys) {
  return keys.reduce((found, key) => {
    if (errors[key])
      found[key] = errors[key];
    return found;
  }, {});
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

/**
 * The three segmented measures at the head of the card.
 *
 * A segmented bar, not a percentage: three named stages a person can count, with
 * one continuous track that fills as the person advances, rather than three
 * separate blocks: the progress reads as a quantity covered, not as a light
 * panel. The labels below keep the stage names, the mint tick for completed
 * stages and `aria-current="step"` for the active one, so the state is
 * available without seeing the fill at all.
 */
function StepProgress({ step, labels }) {
  const stateOf = (number) => (number < step ? 'done' : number === step ? 'current' : 'todo');
  return (
    <div className="mb-5">
      <p className="num text-[10.5px] font-medium tracking-[0.18em] text-accent-ink uppercase">
        Step {step} of {labels.length}
      </p>
      <div
        className="mt-2.5 h-1 overflow-hidden rounded-full bg-ink/10"
        role="progressbar"
        aria-label="Registration progress"
        aria-valuemin={1}
        aria-valuemax={labels.length}
        aria-valuenow={step}
        aria-valuetext={`Step ${step} of ${labels.length}: ${labels[step - 1]}`}
      >
        <span
          aria-hidden="true"
          className="block h-full rounded-full bg-accent transition-[width] duration-300 ease-soft motion-reduce:transition-none"
          style={{ width: `${(step / labels.length) * 100}%` }}
        />
      </div>
      <ol className="mt-2 grid grid-cols-3 gap-1.5" aria-label="Registration steps">
        {labels.map((label, index) => {
          const number = index + 1;
          const state = stateOf(number);
          return (
            <li
              key={label}
              aria-current={state === 'current' ? 'step' : undefined}
              className={cx(
                'flex min-w-0 items-center gap-1.5 text-[11px] sm:text-[12px]',
                state === 'current'
                  ? 'font-medium text-ink'
                  : state === 'done'
                    ? 'text-ink-soft'
                    : 'text-ink-muted',
              )}
            >
              <span
                aria-hidden="true"
                className={cx(
                  'num text-[10px] leading-none',
                  state === 'done' ? 'text-mint-ink' : state === 'current' ? 'text-accent-ink' : 'text-ink-muted',
                )}
              >
                {state === 'done' ? '\u2713' : number}
              </span>
              <span className="truncate">{label}</span>
            </li>
          );
        })}
      </ol>
      <p role="status" className="sr-only">
        Step {step} of {labels.length}, {labels[step - 1]}
      </p>
    </div>
  );
}

function AccountTypePicker({ form, onSelect }) {
  return (
    <fieldset>
      <legend className="sr-only">Account type</legend>
      <div className="space-y-2.5">
        {ACCOUNT_TYPES.map((item) => {
          const id = `account_type_${item.value}`;
          const selected = form.accountType === item.value;
          return (
            <label
              key={item.value}
              className={cx(
                'relative flex cursor-pointer gap-3 rounded-sm border p-3.5 transition-colors sm:p-4',
                selected
                  ? 'border-accent bg-accent-wash/45'
                  : 'border-line bg-surface hover:border-ink/35',
                'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-dotted has-[:focus-visible]:outline-accent has-[:focus-visible]:outline-offset-2',
              )}
            >
              <input
                id={id}
                type="radio"
                name="account_type"
                value={item.value}
                aria-labelledby={`${id}_title`}
                aria-describedby={`${id}_description`}
                checked={selected}
                onChange={() => onSelect(item.value)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
              />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-3">
                  <span id={`${id}_title`} className="text-[14px] font-medium text-ink">
                    {item.label}
                  </span>
                  {selected ? (
                    <span className="num shrink-0 text-[9.5px] tracking-[0.18em] text-accent-ink uppercase">
                      Selected
                    </span>
                  ) : null}
                </span>
                <span
                  id={`${id}_description`}
                  className="mt-1 block text-[12.5px] leading-5 text-ink-muted"
                >
                  {item.description}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function ProviderPanel({ onBackToPaths }) {
  return (
    <div className="space-y-4">
      <div className="rounded-sm border border-accent/30 bg-accent-wash/60 p-4">
        <p className="text-[14px] font-medium text-accent-ink">
          Apply to the estate where you want to work.
        </p>
        <p className="mt-1.5 text-[13px] leading-5 text-ink-soft">
          The HOA reviews your application. If approved, you receive a secure link to set up
          your account and estate access.
        </p>
      </div>
      <Link
        to="/provider/apply"
        className="flex min-h-11 items-center justify-center rounded-sm bg-accent px-4 py-2.5 text-[14px] font-medium text-white transition-colors hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Apply to an estate
      </Link>
      <button
        type="button"
        onClick={onBackToPaths}
        className="mx-auto flex min-h-11 items-center justify-center px-3 text-[13px] font-medium text-ink-soft underline underline-offset-4 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Choose a different path
      </button>
    </div>
  );
}

export function Register() {
  const { user, logout, register, registerEstate } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(1);
  const [switchingAccount, setSwitchingAccount] = useState(false);
  const signedIn = Boolean(user) && !switchingAccount;
  const provider = form.accountType === 'service_provider';
  const estateAdmin = form.accountType === 'estate_admin';

  function update(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
    setError(null);
  }

  function selectAccountType(value) {
    update('accountType', value);
    setErrors({});
  }

  function switchAccount() {
    logout();
    setSwitchingAccount(true);
    setError(null);
  }

  function back() {
    setErrors({});
    setError(null);
    setStep((previous) => Math.max(1, previous - 1));
  }

  /** Advance only when the fields on this step are valid; otherwise stay put. */
  function advance() {
    const found = validate(form);
    const relevant = step === 2 ? pick(found, IDENTITY_FIELDS) : {};
    setErrors(relevant);
    setError(null);
    if (Object.keys(relevant).length > 0)
      return false;
    setStep((previous) => Math.min(3, previous + 1));
    return true;
  }

  async function submit(event) {
    event.preventDefault();
    if (provider)
      return;
    if (step < 3) {
      advance();
      return;
    }

    const found = validate(form);
    const identity = pick(found, IDENTITY_FIELDS);
    // The identity fields live on step 2; if an edit there went stale, send the
    // person back to the fields rather than failing silently beneath them.
    if (Object.keys(identity).length > 0) {
      setErrors(identity);
      setStep(2);
      return;
    }
    const estate = pick(found, ESTATE_FIELDS);
    setErrors(estate);
    if (Object.keys(estate).length > 0)
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

  const cardTitle = signedIn
    ? 'Current account'
    : provider
      ? 'Provider access'
      : step === 1
        ? 'How will you use VALORA?'
        : step === 2
          ? 'Your details'
          : estateAdmin
            ? 'Estate details'
            : 'Review and create';

  const intro = signedIn
    ? 'Continue to your workspace or sign out to use a different account.'
    : step === 1
      ? 'Three short steps: choose how you use your estate, add your details, then finish. It takes about a minute.'
      : step === 2
        ? 'Your name, email and password become the account you sign in with.'
        : estateAdmin
          ? 'Name the estate you manage. It stays private until you choose to publish it.'
          : 'Check your details, add a unit number if you have one, then create the account.';

  return (
    <AuthShell
      eyebrow="Estate access"
      title={signedIn ? "You're signed in" : 'Create your account'}
      intro={intro}
      points={
        signedIn || provider
          ? []
          : [
              ['Private by default', 'Only your estate\u2019s members see its records.'],
              [
                'One property record',
                'Maintenance, repairs and feedback accrue to the same history.',
              ],
            ]
      }
      cardTitle={cardTitle}
      progress={
        signedIn || provider ? null : <StepProgress step={step} labels={STEP_LABELS} />
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
      ) : provider ? (
        <ProviderPanel onBackToPaths={() => selectAccountType('resident')} />
      ) : (
        <form className="space-y-5" onSubmit={submit} noValidate>
          {step === 1 ? (
            <div className="space-y-4">
              <p className="text-[13px] leading-5 text-ink-muted">
                Pick the path that matches how you use your estate. You can change it before
                your account is created.
              </p>
              <AccountTypePicker form={form} onSelect={selectAccountType} />
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-4">
              <Field label="Full name" error={errors.full_name}>
                <Input
                  name="full_name"
                  autoComplete="name"
                  required
                  aria-invalid={Boolean(errors.full_name)}
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
                  aria-invalid={Boolean(errors.email)}
                  value={form.email}
                  onChange={(event) => update('email', event.target.value)}
                  placeholder="you@example.co.za"
                />
              </Field>

              <Field
                label="Password"
                error={errors.password}
                hint="At least 8 characters. A phrase you can remember beats a short scramble."
              >
                <Input
                  type="password"
                  name="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={Boolean(errors.password)}
                  value={form.password}
                  onChange={(event) => update('password', event.target.value)}
                />
              </Field>

              <Field label="Phone (optional)" hint="Only your estate’s office sees this.">
                <Input
                  name="phoneno"
                  autoComplete="tel"
                  value={form.phoneno}
                  onChange={(event) => update('phoneno', event.target.value)}
                  placeholder="082 000 0000"
                />
              </Field>
            </div>
          ) : null}

          {step === 3 && !estateAdmin ? (
            <div className="space-y-4">
              <div className="rounded-sm border border-line bg-paper/70 p-3.5">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[10.5px] font-medium tracking-[0.18em] text-ink-muted uppercase">
                    Resident account
                  </p>
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="-mt-2 min-h-9 shrink-0 px-1 text-[12px] font-medium text-accent-ink underline underline-offset-4 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    Edit
                  </button>
                </div>
                <dl className="mt-2 space-y-1.5 text-[13px]">
                  <div className="flex items-baseline justify-between gap-4">
                    <dt className="shrink-0 text-ink-muted">Name</dt>
                    <dd className="truncate text-ink">{form.full_name || '\u2014'}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-4">
                    <dt className="shrink-0 text-ink-muted">Email</dt>
                    <dd className="truncate text-ink">{form.email || '\u2014'}</dd>
                  </div>
                </dl>
              </div>

              <Field
                label="Unit number (optional)"
                hint="Helps your estate office match you to the right property."
              >
                <Input
                  name="unit_no"
                  value={form.unit_no}
                  onChange={(event) => update('unit_no', event.target.value)}
                  placeholder="A-101"
                />
              </Field>

              <p className="text-[12.5px] leading-5 text-ink-muted">
                You will need a join code from your estate office before you can see your
                estate’s records.
              </p>
            </div>
          ) : null}

          {step === 3 && estateAdmin ? (
            <div className="space-y-4">
              <Field label="Estate name" error={errors.estateName}>
                <Input
                  name="estate_name"
                  required
                  aria-invalid={Boolean(errors.estateName)}
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
                    aria-invalid={Boolean(errors.estateSuburb)}
                    value={form.estateSuburb}
                    onChange={(event) => update('estateSuburb', event.target.value)}
                    placeholder="Centurion"
                  />
                </Field>
                <Field label="City" error={errors.estateCity}>
                  <Input
                    name="estate_city"
                    required
                    aria-invalid={Boolean(errors.estateCity)}
                    value={form.estateCity}
                    onChange={(event) => update('estateCity', event.target.value)}
                    placeholder="Tshwane"
                  />
                </Field>
              </div>
              <Field label="Province" error={errors.estateProvince}>
                <Select
                  name="estate_province"
                  value={form.estateProvince}
                  onChange={(event) => update('estateProvince', event.target.value)}
                >
                  {PROVINCES.map((province) => (
                    <option key={province} value={province}>
                      {province}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Description (optional)">
                <Textarea
                  name="estate_description"
                  value={form.estateDescription}
                  maxLength={5000}
                  rows={3}
                  onChange={(event) => update('estateDescription', event.target.value)}
                  placeholder="A short description of your estate."
                />
              </Field>
              <p className="text-[12.5px] leading-5 text-ink-muted">
                Your estate starts private. You can publish it to the directory later.
              </p>
            </div>
          ) : null}

          {error ? (
            <ErrorState
              title={
                estateAdmin
                  ? 'Could not create the estate workspace'
                  : 'Could not create the account'
              }
              message={error.message}
              requestId={error.requestId}
            />
          ) : null}

          <div className="space-y-1">
            <Button
              type="submit"
              variant="primary"
              className="min-h-11 w-full py-2.5"
              disabled={busy}
            >
              {busy
                ? 'Creating your account…'
                : step < 3
                  ? 'Continue'
                  : estateAdmin
                    ? 'Create estate workspace'
                    : 'Create resident account'}
            </Button>
            {step > 1 ? (
              <button
                type="button"
                onClick={back}
                className="mx-auto flex min-h-11 items-center justify-center px-3 text-[13px] font-medium text-ink-soft hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Back
              </button>
            ) : null}
          </div>
        </form>
      )}
    </AuthShell>
  );
}
