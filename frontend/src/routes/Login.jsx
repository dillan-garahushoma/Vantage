import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';

export function Login() {
  const { user, login, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const from = location.state?.from;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(from ?? '/welcome', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Sign in failed.'));
    } finally {
      setBusy(false);
    }
  }

  if (user) {
    return (
      <AuthShell
        eyebrow="Your VALORA session"
        title="You're already signed in."
        intro="Continue to your workspace, or sign out first if you need to use a different account."
        cardTitle="Current account"
      >
        <div className="space-y-4">
          <div className="border-l-2 border-accent bg-canvas px-4 py-3">
            <p className="font-medium text-ink">{user.full_name}</p>
            <p className="mt-1 text-sm text-ink-muted">{user.email}</p>
            <p className="mt-2 text-xs text-ink-muted">Your role and estate access come from approved membership.</p>
          </div>
          <Button type="button" variant="primary" className="w-full" onClick={() => navigate(from ?? '/welcome', { replace: true })}>
            Continue to VALORA
          </Button>
          <Button type="button" variant="secondary" className="w-full" onClick={() => {
            logout();
            setEmail('');
            setPassword('');
            setError(null);
          }}>
            Sign out and use another account
          </Button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow="Estate access"
      title="Welcome back."
      intro="Sign in to access the estates you belong to. Your workspace and permissions follow your approved estate membership."
      points={[
        ['Estate-scoped', 'A supplied estate identifier is never proof of access.'],
        ['Roles from membership', 'HOA and provider capabilities require matching estate membership.'],
        ['Secure access', 'Repeated failed attempts are rate-limited per account.'],
      ]}
      cardTitle="Sign in"
      footer={<p className="mt-5 text-[13px] text-ink-muted">
        Need an account?{' '}
        <Link to="/register" className="font-medium text-accent-ink hover:underline">Create an account</Link>.
      </p>}
    >
      <form className="space-y-4" onSubmit={submit} noValidate>
        {error ? <ErrorState title={error.status === 429 ? 'Too many attempts' : 'Could not sign you in'} message={error.message} requestId={error.requestId} /> : null}
        <Field label="Email address">
          <Input type="email" name="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.co.za" />
        </Field>
        <Field label="Password">
          <Input type="password" name="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" />
        </Field>
        <div className="text-right text-[13px]">
          <Link to="/password-recovery" className="font-medium text-accent-ink hover:underline">Forgot password?</Link>
        </div>
        <Button type="submit" variant="primary" className="w-full py-2.5" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthShell>
  );
}
