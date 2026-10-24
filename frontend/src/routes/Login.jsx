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
  const signedIn = Boolean(user) && !switchingAccount;

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

  function switchAccount() {
    logout();
    setSwitchingAccount(true);
    setError(null);
  }

  return (
    <AuthShell
      eyebrow="Estate access"
      title={signedIn ? "You're signed in" : 'Sign in'}
      intro={
        signedIn
          ? 'Continue to your workspace or sign out to use a different account.'
          : 'Sign in to reach the estates linked to your account. Provider access starts after an estate HOA approves your application.'
      }
      points={
        signedIn
          ? []
          : [
              ['Estate-scoped', 'Your membership determines which estate data you can access.'],
              ['Role-specific', 'HOA and provider tools are available only to approved memberships.'],
            ]
      }
      cardTitle={signedIn ? 'Current account' : 'Welcome back'}
      footer={
        signedIn ? null : (
          <p className="mt-5 text-[13px] text-ink-muted">
            No account yet?{' '}
            <Link to="/register" className="font-medium text-accent-ink hover:underline">
              Create an account
            </Link>
            .
          </p>
        )
      }
    >
      {signedIn ? (
        <SignedInAccountActions
          user={user}
          onSwitch={switchAccount}
          continueTo={from ?? '/welcome'}
        />
      ) : (
        <form className="space-y-4" onSubmit={submit} noValidate>
          {error ? (
            <ErrorState
              title={error.status === 429 ? 'Too many attempts' : 'Could not sign you in'}
              message={error.message}
              requestId={error.requestId}
            />
          ) : null}

          <Field label="Email address">
            <Input
              type="email"
              name="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.co.za"
            />
          </Field>

          <Field label="Password">
            <Input
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
            />
          </Field>

          <div className="text-right text-[13px]">
            <Link
              to="/password-recovery"
              className="font-medium text-accent-ink hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <Button type="submit" variant="primary" className="w-full min-h-11" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
