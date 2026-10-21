import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { Button, Card, ErrorState, Field, Input } from '../components/ui';
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
        return <Navigate to="/login" replace state={{ from: '/join' }}/>;
    if (estates.length > 0)
        return <Navigate to="/app" replace/>;
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
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not join the estate.'));
        }
        finally {
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
    return (<PublicShell>
      <div className="mx-auto grid max-w-[1000px] gap-10 px-5 py-14 lg:grid-cols-[1fr_1.05fr]">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Resident onboarding
          </p>
          <h1 className="mt-3 text-[32px] leading-tight font-semibold">
            Enter your code and unit
          </h1>
          <p className="mt-3 max-w-md text-[14.5px] text-ink-soft">
            The code comes from your estate office. It names the estate for you — you cannot type an
            estate in, and holding a code is what gives you the right to join.
          </p>
          <p className="mt-3 max-w-md text-[13px] text-ink-muted">
            Five mistyped codes in fifteen minutes are rate-limited, so take the code from the message
            rather than guessing at it.
          </p>
        </div>

        <Card className="p-6">
          <h2 className="text-[16px] font-semibold">Your code</h2>
          <Keyline className="mt-3"/>

          <form className="mt-5 space-y-4" onSubmit={submit} noValidate>
            {error ? (<ErrorState title={title} message={error.message} requestId={error.requestId}/>) : null}

            <Field label="Join code" error={errors.code} hint="Ten characters, case does not matter.">
              <Input name="code" value={code} onChange={(event) => setCode(event.target.value)} autoComplete="one-time-code" spellCheck={false} className="num tracking-[0.18em] uppercase" placeholder="ABCD2EFGH3"/>
            </Field>

            <Field label="Unit number" error={errors.unit_no} hint="As it appears on your lease.">
              <Input name="unit_no" value={unitNo} onChange={(event) => setUnitNo(event.target.value)} placeholder="HR-01"/>
            </Field>

            <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
              {busy ? 'Joining…' : 'Join the estate'}
            </Button>
          </form>

          <p className="mt-5 text-[13px] text-ink-muted">
            No code yet?{' '}
            <Link to="/request-access" className="font-medium text-accent-ink hover:underline">
              Request access for approval
            </Link>{' '}
            and your estate office will review it — or{' '}
            <Link to="/estates" className="font-medium text-accent-ink hover:underline">
              find your complex
            </Link>
            .
          </p>
        </Card>
      </div>
    </PublicShell>);
}
