import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthShell, SignedInAccountActions } from '../components/AuthShell';
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
  const [switchingAccount, setSwitchingAccount] = useState(false);
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

  if (user && !switchingAccount) {
    return (
      <AuthShell
        eyebrow="Your VALORA session"
        title="You're already signed in."
        intro="Continue to your workspace, or sign out first if you need to use a different account."
        cardTitle="Current account"
      >
        <SignedInAccountActions user={user} continueTo={from ?? '/welcome'} onSwitch={() => {
            logout();
            setSwitchingAccount(true);
            setEmail('');
            setPassword('');
            setError(null);
          }} />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow="Estate access"
      title="Welcome back."
      intro="Sign in to continue to your estate."
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
