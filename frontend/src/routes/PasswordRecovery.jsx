import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { Button, Card, ErrorState, Field, Input } from '../components/ui';
import { ApiError } from '../lib/api';
import { confirmPasswordRecovery, requestPasswordRecovery } from '../lib/accountSupport';

export function PasswordRecovery() {
    const [params] = useSearchParams();
    const token = params.get('token')?.trim() ?? '';
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmation, setConfirmation] = useState('');
    const [error, setError] = useState(null);
    const [message, setMessage] = useState(null);
    const [busy, setBusy] = useState(false);
    const confirming = Boolean(token);
    async function submit(event) {
        event.preventDefault();
        if (confirming && password !== confirmation) {
            setError(new ApiError(0, 'The two passwords do not match.'));
            return;
        }
        if (confirming && password.length < 8) {
            setError(new ApiError(0, 'Use at least 8 characters for your new password.'));
            return;
        }
        setBusy(true);
        setError(null);
        setMessage(null);
        try {
            const response = confirming
                ? await confirmPasswordRecovery(token, password)
                : await requestPasswordRecovery(email.trim());
            setMessage(response.message);
        }
        catch (cause) {
            setError(cause instanceof ApiError
                ? cause
                : new ApiError(0, 'Could not process password recovery.'));
        }
        finally {
            setBusy(false);
        }
    }
    return (<PublicShell>
      <div className="mx-auto max-w-md px-5 py-14">
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">Account recovery</p>
        <h1 className="mt-3 text-[30px] leading-tight font-semibold">
          {confirming ? 'Set a new password' : 'Reset your password'}
        </h1>
        <p className="mt-3 text-[14px] text-ink-soft">
          {confirming
                ? 'Choose a new password for your VALORA account.'
                : 'Enter your account email. If it is eligible, recovery instructions will be sent.'}
        </p>

        <Card className="mt-7 p-6">
          <Keyline className="mb-5"/>
          <form className="space-y-4" onSubmit={submit} noValidate>
            {error ? <ErrorState message={error.message} requestId={error.requestId}/> : null}
            {message ? <p role="status" className="rounded-xs bg-accent-wash px-3 py-2.5 text-[13px] text-accent-ink">{message}</p> : null}
            {confirming ? (<>
                <Field label="New password" hint="At least 8 characters.">
                  <Input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)}/>
                </Field>
                <Field label="Confirm new password">
                  <Input type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)}/>
                </Field>
                <Button type="submit" variant="primary" className="w-full" disabled={busy || Boolean(message)}>
                  {busy ? 'Updating…' : 'Set new password'}
                </Button>
              </>) : (<>
                <Field label="Email address">
                  <Input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.co.za" required/>
                </Field>
                <Button type="submit" variant="primary" className="w-full" disabled={busy || !email.trim()}>
                  {busy ? 'Sending…' : 'Send recovery instructions'}
                </Button>
              </>)}
          </form>
          <p className="mt-5 text-[13px] text-ink-muted"><Link to="/login" className="font-medium text-accent-ink hover:underline">Back to sign in</Link></p>
        </Card>
      </div>
    </PublicShell>);
}
