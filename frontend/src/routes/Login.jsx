import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { Button, Card, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';
export function Login() {
    const { user, login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    // A deep link wins; otherwise /welcome decides by server-resolved membership
    // (an estate administrator belongs on their setup screen, not a dashboard).
    const from = location.state?.from;
    if (user)
        return <Navigate to={from ?? '/welcome'} replace/>;
    async function submit(event) {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
            await login(email.trim(), password);
            navigate(from ?? '/welcome', { replace: true });
        }
        catch (cause) {
            setError(cause instanceof ApiError ? cause : new ApiError(0, 'Sign in failed.'));
        }
        finally {
            setBusy(false);
        }
    }
    return (<PublicShell>
      <div className="mx-auto grid max-w-[1000px] gap-10 px-5 py-14 lg:grid-cols-2 lg:items-center">
        <div>
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            Estate access
          </p>
          <h1 className="mt-3 text-[32px] leading-tight font-semibold">Sign in</h1>
          <p className="mt-3 max-w-md text-[14.5px] text-ink-soft">
            Your account gives you access to the estates you are a member of, and nothing else. If an
            HOA has provisioned your estate, it appears as soon as you sign in.
          </p>

          <div className="mt-8 max-w-md space-y-3">
            {[
            ['Estate-scoped', 'A supplied estate identifier is never proof of access.'],
            ['Roles from membership', 'HOA and provider capability need a matching estate membership.'],
            ['Attempts are recorded', 'Repeated failures are rate-limited per account.'],
        ].map(([term, detail]) => (<div key={term} className="flex gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rotate-45 bg-accent"/>
                <p className="text-[13px] text-ink-soft">
                  <span className="font-medium text-ink">{term}.</span> {detail}
                </p>
              </div>))}
          </div>
        </div>

        <Card className="p-6">
          <h2 className="text-[16px] font-semibold">Welcome back</h2>
          <Keyline className="mt-3"/>

          <form className="mt-5 space-y-4" onSubmit={submit} noValidate>
            {error ? (<ErrorState title={error.status === 429 ? 'Too many attempts' : 'Could not sign you in'} message={error.message} requestId={error.requestId}/>) : null}

            <Field label="Email address">
              <Input type="email" name="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.co.za"/>
            </Field>

            <Field label="Password">
              <Input type="password" name="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••"/>
            </Field>

            <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <p className="mt-5 text-[13px] text-ink-muted">
            No account yet?{' '}
            <Link to="/register" className="font-medium text-accent-ink hover:underline">
              Create an account
            </Link>
            .
          </p>
        </Card>
      </div>
    </PublicShell>);
}
