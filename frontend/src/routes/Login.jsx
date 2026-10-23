import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
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
    return (<AuthShell
      eyebrow="Estate access"
      title="Sign in"
      intro="Your account gives you access to the estates you are a member of, and nothing else. If an HOA has provisioned your estate, it appears as soon as you sign in."
      points={[
        ['Estate-scoped', 'A supplied estate identifier is never proof of access.'],
        ['Roles from membership', 'HOA and provider capability need a matching estate membership.'],
        ['Attempts are recorded', 'Repeated failures are rate-limited per account.'],
      ]}
      cardTitle="Welcome back"
      footer={<p className="mt-5 text-[13px] text-ink-muted">
          No account yet?{' '}
          <Link to="/register" className="font-medium text-accent-ink hover:underline">
            Create an account
          </Link>
          .
        </p>}
    >
      <form className="space-y-4" onSubmit={submit} noValidate>
        {error ? (<ErrorState title={error.status === 429 ? 'Too many attempts' : 'Could not sign you in'} message={error.message} requestId={error.requestId}/>) : null}

        <Field label="Email address">
          <Input type="email" name="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.co.za"/>
        </Field>

        <Field label="Password">
          <Input type="password" name="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••"/>
        </Field>

        <div className="text-right text-[13px]">
          <Link to="/password-recovery" className="font-medium text-accent-ink hover:underline">Forgot password?</Link>
        </div>

        <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthShell>);
}
