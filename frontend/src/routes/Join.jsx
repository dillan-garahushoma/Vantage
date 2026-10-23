import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstate } from '../context/EstateContext';
import { ApiError } from '../lib/api';
import { joinEstateWithCode } from '../lib/estateAdmin';

function validate(code, unitNo) {
  const errors = {};
  if (code.trim().length === 0)
    errors.code = 'Enter the code your estate office gave you.';
  if (code.trim().length > 32)
    errors.code = 'That code is longer than a VALORA code can be.';
  if (unitNo.trim().length === 0)
    errors.unit_no = 'Enter your unit number.';
  if (unitNo.trim().length > 10)
    errors.unit_no = 'Unit numbers are at most 10 characters.';
  return errors;
}

export function Join() {
  const { user } = useAuth();
  const { estates, reload } = useEstate();
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [unitNo, setUnitNo] = useState('');
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!user)
    return <Navigate to="/login" replace state={{ from: '/join' }} />;
  if (estates.length > 0)
    return <Navigate to="/app" replace />;

  async function submit(event) {
    event.preventDefault();
    const found = validate(code, unitNo);
    setErrors(found);
    if (Object.keys(found).length > 0)
      return;
    setBusy(true);
    setError(null);
    try {
      // Exactly what was validated: the code upper-cased and stripped, the unit
      // trimmed. The API normalises again, but nothing here sends stray spaces.
      await joinEstateWithCode(code.trim(), unitNo.trim());
      reload();
      navigate('/app', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not join the estate.'));
    } finally {
      setBusy(false);
    }
  }

  const title = !error
    ? 'Join your estate'
    : error.status === 429
      ? 'Too many attempts'
      : error.status === 409
        ? 'You are already a member'
        : error.status === 401
          ? 'Your session expired'
          : 'Could not join with that code';

  return (
    <AuthShell
      eyebrow="Estate access"
      step={2}
      totalSteps={3}
      stepLabels={['Account', 'Join estate', "You're in"]}
      title="Enter your code and unit"
      intro="The code comes from your estate office — it names the estate for you."
      points={[
        ['One code, one estate', 'The code carries the estate, so there is nothing else to pick.'],
        ['Your unit is checked', 'The office matches the unit number against their register.'],
      ]}
      backTo="/register"
      backLabel="Back to your account"
    >
      <form className="space-y-4" onSubmit={submit} noValidate>
        {error ? (
          <ErrorState title={title} message={error.message} requestId={error.requestId} />
        ) : null}

        <Field label="Join code" error={errors.code} hint="Ten characters, case does not matter.">
          <Input
            name="code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            autoComplete="one-time-code"
            spellCheck={false}
            className="num tracking-[0.18em] uppercase"
            placeholder="ABCD2EFGH3"
          />
        </Field>

        <Field label="Unit number" error={errors.unit_no} hint="As it appears on your lease.">
          <Input
            name="unit_no"
            value={unitNo}
            onChange={(event) => setUnitNo(event.target.value)}
            placeholder="HR-01"
          />
        </Field>

        <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
          {busy ? 'Joining…' : 'Join the estate'}
        </Button>
      </form>

      <div className="relative my-5">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-line" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-surface px-3 text-[11px] uppercase tracking-widest text-ink-muted">or</span>
        </div>
      </div>
      <Link
        to="/request-access"
        className="flex w-full items-center justify-between rounded-xl border border-line bg-surface px-4 py-3 text-[13.5px] font-medium text-ink-soft transition-colors hover:border-accent hover:text-accent-ink"
      >
        Request access for approval
        <span className="text-ink-muted">→</span>
      </Link>
      <p className="mt-3 text-center text-[12px] text-ink-muted">
        No code yet? Your estate office will review the request.
      </p>
    </AuthShell>
  );
}
