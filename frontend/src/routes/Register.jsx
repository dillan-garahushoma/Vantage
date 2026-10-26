import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Building2, Check, Search } from 'lucide-react';
import { Keyline } from '../components/Brand';
import { AuthShell } from '../components/AuthShell';
import { Button, EmptyState, ErrorState, Field, Input, LoadingState, Select, Textarea } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';
import { listPublicEstates } from '../lib/publicDirectory';
import { clearSelectedPublicEstate, rememberPublicEstate, selectedPublicEstate } from '../lib/publicEstateSelection';
import { useAsync } from '../lib/useAsync';

const ACCOUNT_TYPES = [
  {
    value: 'resident',
    label: 'Resident',
    blurb: 'Create an account and ask your estate office for access.',
  },
  {
    value: 'estate_admin',
    label: 'HOA / estate manager',
    blurb: 'Create your account and start setting up the estate you manage.',
  },
  {
    value: 'service_provider',
    label: 'Service provider',
    blurb: 'Apply to an estate. Its HOA reviews your details before account setup.',
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
  return payload;
}

function validateEstateRegistration(form) {
  const errors = validate(form);
  if (form.estateName.trim().length < 2) errors.estateName = 'Enter the estate name.';
  if (!form.estateSuburb.trim()) errors.estateSuburb = 'Enter the suburb.';
  if (!form.estateCity.trim()) errors.estateCity = 'Enter the city.';
  if (!form.estateProvince) errors.estateProvince = 'Choose a province.';
  return errors;
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
            <p className="mt-1 text-xs text-ink-soft">You can request access after creating your account. No unit number is needed.</p>
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
  const { user, register, registerEstate, logout } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [signupStep, setSignupStep] = useState(1);
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

  function clearEstate() {
    setSelectedEstate(null);
    clearSelectedPublicEstate();
  }

  function chooseEstate(estate) {
    setSelectedEstate(estate);
    rememberPublicEstate(estate);
    setError(null);
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
      if (selectedEstate) {
        rememberPublicEstate(selectedEstate);
      } else {
        clearSelectedPublicEstate();
      }
      await register(registrationPayload(form));
      navigate('/request-access', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Registration failed.'));
    } finally {
      setBusy(false);
    }
  }

  async function submitEstateRegistration(event) {
    event.preventDefault();
    const found = validateEstateRegistration(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    setError(null);
    try {
      const estate = {
        name: form.estateName.trim(),
        suburb: form.estateSuburb.trim(),
        city: form.estateCity.trim(),
        province: form.estateProvince,
      };
      const description = form.estateDescription.trim();
      if (description) estate.description = description;
      const payload = {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        estate,
      };
      const phone = form.phoneno.trim();
      if (phone) payload.phoneno = phone;
      await registerEstate(payload);
      navigate('/welcome', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not create the estate account.'));
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
      step={signupStep}
      totalSteps={3}
      stepLabels={form.accountType === 'estate_admin' ? ['Your account', 'Estate details', 'Review & create'] : ['Your account', 'Your estate', 'Review & create']}
      title="Find your way into VALORA."
      intro="Choose the path that fits your role. Residents request estate access, HOAs create an estate workspace, and providers apply to an estate for review."
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
            <form className="space-y-5" onSubmit={submit} noValidate>
              <div className="mb-5">
                <div className="flex items-center justify-between text-xs text-ink-muted"><span>Account setup</span><span>Step {signupStep} of 3</span></div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/10"><div className="h-full rounded-full bg-accent transition-all duration-300" style={{ width: ((signupStep / 3) * 100) + "%" }} /></div>
              </div>
              {error ? <ErrorState title="Could not create the account" message={error.message} requestId={error.requestId} /> : null}
              {signupStep === 1 ? (
                <section className="space-y-4" aria-labelledby="resident-account-step">
                  <div><h2 id="resident-account-step" className="text-lg font-semibold tracking-tight text-ink">Let’s start with you.</h2><p className="mt-1 text-sm text-ink-muted">Create the secure account you’ll use across VALORA.</p></div>
                  <Field label="Full name" error={errors.full_name}><Input name="full_name" autoComplete="name" value={form.full_name} onChange={(event) => update("full_name", event.target.value)} placeholder="Thandi Nkosi" required /></Field>
                  <Field label="Email address" error={errors.email}><Input type="email" name="email" autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} placeholder="you@example.co.za" required /></Field>
                  <Field label="Password" error={errors.password} hint="At least 8 characters."><Input type="password" name="password" autoComplete="new-password" value={form.password} onChange={(event) => update("password", event.target.value)} required /></Field>
                  <Field label="Phone number (optional)"><Input name="phoneno" autoComplete="tel" value={form.phoneno} onChange={(event) => update("phoneno", event.target.value)} placeholder="082 000 0000" /></Field>
                </section>
              ) : signupStep === 2 ? (
                <section className="space-y-4" aria-labelledby="resident-estate-step">
                  <div><h2 id="resident-estate-step" className="text-lg font-semibold tracking-tight text-ink">Where do you live?</h2><p className="mt-1 text-sm text-ink-muted">Choose your complex now, or skip this and request access later.</p></div>
                  <EstatePicker value={selectedEstate} onSelect={chooseEstate} onClear={clearEstate} query={estateQuery} onQueryChange={setEstateQuery} committedQuery={committedEstateQuery} onSearch={() => setCommittedEstateQuery(estateQuery.trim())} directory={directory} />
                </section>
              ) : (
                <section className="space-y-4" aria-labelledby="resident-review-step">
                  <div><h2 id="resident-review-step" className="text-lg font-semibold tracking-tight text-ink">Everything look right?</h2><p className="mt-1 text-sm text-ink-muted">Review your details before creating your account.</p></div>
                  <div className="space-y-3 rounded-xl border border-line bg-paper/60 p-4"><div><p className="text-xs text-ink-muted">Full name</p><p className="mt-0.5 text-sm font-medium text-ink">{form.full_name || "Not provided"}</p></div><div><p className="text-xs text-ink-muted">Email</p><p className="mt-0.5 break-all text-sm font-medium text-ink">{form.email || "Not provided"}</p></div><div><p className="text-xs text-ink-muted">Phone</p><p className="mt-0.5 text-sm font-medium text-ink">{form.phoneno || "Not provided"}</p></div><div><p className="text-xs text-ink-muted">Estate</p><p className="mt-0.5 text-sm font-medium text-ink">{selectedEstate?.name || "I’ll choose an estate later"}</p><p className="mt-1 text-xs leading-relaxed text-ink-muted">Choosing an estate does not grant access. Your estate office still needs to approve your membership.</p></div></div>
                </section>
              )}
              <div className="flex items-center gap-3 border-t border-line pt-4">
                {signupStep > 1 ? <Button type="button" variant="secondary" className="flex-1" onClick={() => setSignupStep((step) => step - 1)}><ArrowLeft className="mr-2 h-4 w-4" />Back</Button> : null}
                {signupStep < 3 ? <Button type="button" variant="primary" className="flex-1" onClick={() => { const found = signupStep === 1 ? validate(form) : {}; setErrors(found); if (Object.keys(found).length === 0) setSignupStep((step) => step + 1); }}>Continue<ArrowRight className="ml-2 h-4 w-4" /></Button> : <Button type="submit" variant="primary" className="flex-1" disabled={busy}>{busy ? "Creating account…" : "Create account"}</Button>}
              </div>
            </form>

            <p className="text-[13px] text-ink-muted">
              Already registered?{' '}
              <Link to="/login" state={{ from: '/request-access' }} className="font-medium text-accent-ink hover:underline">
                Sign in
              </Link>.
            </p>
          </>
        ) : form.accountType === 'estate_admin' ? (
          <form className="space-y-5" onSubmit={submitEstateRegistration} noValidate>
            <div className="mb-5"><div className="flex items-center justify-between text-xs text-ink-muted"><span>Estate onboarding</span><span>Step {signupStep} of 3</span></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/10"><div className="h-full rounded-full bg-accent transition-all duration-300" style={{ width: ((signupStep / 3) * 100) + "%" }} /></div><div className="mt-2 grid grid-cols-3 text-[11px] text-ink-muted"><span className={signupStep === 1 ? "font-semibold text-accent-ink" : ""}>Your account</span><span className={"text-center " + (signupStep === 2 ? "font-semibold text-accent-ink" : "")}>Estate details</span><span className={"text-right " + (signupStep === 3 ? "font-semibold text-accent-ink" : "")}>Review</span></div></div>
            {error ? <ErrorState title="Could not create the estate account" message={error.message} requestId={error.requestId} /> : null}
            {signupStep === 1 ? (
              <section className="space-y-4" aria-labelledby="hoa-account-step"><div><h2 id="hoa-account-step" className="text-lg font-semibold tracking-tight text-ink">Your administrator account</h2><p className="mt-1 text-sm text-ink-muted">These details will be used to manage your estate workspace.</p></div>
                <Field label="Your full name" error={errors.full_name}><Input name="full_name" autoComplete="name" value={form.full_name} onChange={(event) => update("full_name", event.target.value)} required /></Field>
                <Field label="Email address" error={errors.email}><Input type="email" name="email" autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} required /></Field>
                <Field label="Password" error={errors.password} hint="At least 8 characters."><Input type="password" name="password" autoComplete="new-password" value={form.password} onChange={(event) => update("password", event.target.value)} required /></Field>
                <Field label="Phone number (optional)"><Input name="phoneno" autoComplete="tel" value={form.phoneno} onChange={(event) => update("phoneno", event.target.value)} /></Field>
              </section>
            ) : signupStep === 2 ? (
              <section className="space-y-4" aria-labelledby="hoa-estate-step"><div><h2 id="hoa-estate-step" className="text-lg font-semibold tracking-tight text-ink">Tell us about the estate.</h2><p className="mt-1 text-sm text-ink-muted">Start with the essentials. You can complete the rest of your estate profile after setup.</p></div>
                <Field label="Estate / complex name" error={errors.estateName}><Input name="estate_name" value={form.estateName} onChange={(event) => update("estateName", event.target.value)} placeholder="e.g. The Willows Estate" required /></Field>
                <div className="grid gap-4 sm:grid-cols-2"><Field label="Suburb" error={errors.estateSuburb}><Input name="estate_suburb" value={form.estateSuburb} onChange={(event) => update("estateSuburb", event.target.value)} required /></Field><Field label="City" error={errors.estateCity}><Input name="estate_city" value={form.estateCity} onChange={(event) => update("estateCity", event.target.value)} required /></Field></div>
                <Field label="Province" error={errors.estateProvince}><Select name="estate_province" value={form.estateProvince} onChange={(event) => update("estateProvince", event.target.value)} required>{PROVINCES.map((province) => <option key={province} value={province}>{province}</option>)}</Select></Field>
                <Field label="Short description (optional)"><Textarea name="estate_description" value={form.estateDescription} maxLength={5000} onChange={(event) => update("estateDescription", event.target.value)} placeholder="A short introduction to your estate." /></Field>
              </section>
            ) : (
              <section className="space-y-4" aria-labelledby="hoa-review-step"><div><h2 id="hoa-review-step" className="text-lg font-semibold tracking-tight text-ink">Ready to create your workspace?</h2><p className="mt-1 text-sm text-ink-muted">Check the administrator and estate details below.</p></div>
                <div className="space-y-3 rounded-xl border border-line bg-paper/60 p-4"><div><p className="text-xs text-ink-muted">Administrator</p><p className="mt-0.5 text-sm font-medium text-ink">{form.full_name}</p><p className="mt-0.5 break-all text-xs text-ink-muted">{form.email}</p></div><div className="border-t border-line pt-3"><p className="text-xs text-ink-muted">Estate / complex</p><p className="mt-0.5 text-sm font-medium text-ink">{form.estateName}</p><p className="mt-0.5 text-sm text-ink-muted">{[form.estateSuburb, form.estateCity, form.estateProvince].filter(Boolean).join(", ")}</p></div>{form.estateDescription.trim() ? <p className="border-t border-line pt-3 text-sm leading-relaxed text-ink-soft">{form.estateDescription}</p> : null}</div>
                <p className="text-xs leading-relaxed text-ink-muted">Creating this workspace establishes your HOA administrator account and estate together. You can add units, photos and publish the estate from the setup dashboard.</p>
              </section>
            )}
            <div className="flex items-center gap-3 border-t border-line pt-4">{signupStep > 1 ? <Button type="button" variant="secondary" className="flex-1" onClick={() => setSignupStep((step) => step - 1)}><ArrowLeft className="mr-2 h-4 w-4" />Back</Button> : null}{signupStep < 3 ? <Button type="button" variant="primary" className="flex-1" onClick={() => { let found = {}; if (signupStep === 1) found = validate(form); if (signupStep === 2) found = validateEstateRegistration(form); setErrors(found); if (Object.keys(found).length === 0) setSignupStep((step) => step + 1); }}>Continue<ArrowRight className="ml-2 h-4 w-4" /></Button> : <Button type="submit" variant="primary" className="flex-1" disabled={busy}>{busy ? "Creating estate…" : "Create estate & account"}</Button>}</div>
          </form>
          <p className="text-[13px] text-ink-muted">Already have an account? <Link to="/login" className="font-medium text-accent-ink hover:underline">Sign in</Link>.</p>
        ) : (
          <div className="space-y-4 border-l-2 border-accent bg-canvas p-4">
            <p className="text-sm leading-relaxed text-ink-soft">
              Apply to a published estate with your contact and trade details. The HOA reviews the application and sends a secure account setup link if it is approved.
            </p>
            <Link to="/provider/apply" className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-ink">
              Apply to work at an estate
            </Link>
          </div>
        )}
        <p className="text-xs text-ink-muted">
          {selectedPath?.label} selected. Access is always checked against your account and estate membership.
        </p>
      </div>
    </AuthShell>
  );
}
