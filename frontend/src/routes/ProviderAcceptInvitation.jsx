import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { Button, ErrorState, Field, Input } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';

function invitationToken() {
  return new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '';
}

export function ProviderAcceptInvitation() {
  const { acceptProviderInvitation } = useAuth();
  const navigate = useNavigate();
  const token = invitationToken();
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await acceptProviderInvitation(token, password);
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
      navigate('/welcome', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause : new ApiError(0, 'Could not activate your account.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Provider account setup"
      title="Finish setting up your account"
      intro="Your estate administrator approved your application. Existing providers can continue to add this estate; new providers should choose a password."
      cardTitle="Activate estate access"
      footer={<p className="mt-5 text-[13px] text-ink-muted"><Link to="/login" className="font-medium text-accent-ink hover:underline">Back to sign in</Link></p>}
    >
      {!token ? (
        <ErrorState title="Invitation link unavailable" message="Open the secure setup link from the approval email, or ask the estate administrator to send a new one." />
      ) : (
        <form className="space-y-4" onSubmit={submit}>
          {error ? (
            <ErrorState title="Could not activate your account" message={error.message} requestId={error.requestId} />
          ) : null}
          <Field label="Password for a new account" hint="Leave blank if you already have a VALORA provider account.">
            <Input
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <Button type="submit" variant="primary" className="w-full min-h-11" disabled={busy}>
            {busy ? 'Activating…' : 'Continue'}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
