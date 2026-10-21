import { Navigate, useNavigate } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { PublicShell } from '../components/PublicShell';
import { IconClock, IconLogout } from '../components/Icons';
import { Button, Card, ErrorState, LoadingState } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { useEstate } from '../context/EstateContext';
import { getMyProviderProfile } from '../lib/estateAdmin';
import { displayLabel } from '../lib/format';
import { useAsync } from '../lib/useAsync';
/**
 * A service provider with no estate yet.
 *
 * This is the one onboarding state that cannot be finished by the person in it:
 * a provider may register themselves, but only an estate administrator can add
 * them (by email). So the screen says exactly who to talk to and what will
 * happen, and offers the only useful action — check again.
 */
export function ProviderWaiting() {
    const { user, logout } = useAuth();
    const { estates, loading, reload } = useEstate();
    const navigate = useNavigate();
    const profile = useAsync(() => getMyProviderProfile(), []);
    if (!user)
        return <Navigate to="/login" replace state={{ from: '/provider/waiting' }}/>;
    if (estates.length > 0)
        return <Navigate to="/app" replace/>;
    return (<PublicShell>
      <div className="mx-auto max-w-3xl px-5 py-14">
        <Card className="p-6">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xs bg-ochre-wash text-ochre-ink">
            <IconClock size={19}/>
          </span>
          <h1 className="mt-4 text-[24px] font-semibold">Waiting to be added to an estate</h1>
          <p className="mt-2 text-[14px] text-ink-soft">
            Your provider account is active and your trade profile is on record. An estate
            administrator now has to add you to their estate by email
            {user.email ? (<>
                : <span className="num font-medium text-ink">{user.email}</span>
              </>) : null}
            .
          </p>

          <Keyline className="my-5"/>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                Your provider profile
              </p>
              {profile.loading ? (<LoadingState label="Loading your profile"/>) : profile.error ? (<ErrorState title="No provider profile on this account" message={profile.error.message} requestId={profile.error.requestId}/>) : profile.data ? (<dl className="mt-2 space-y-1.5 text-[13px]">
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-ink-soft">Name</dt>
                    <dd className="font-medium">{profile.data.full_name}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-ink-soft">Trade</dt>
                    <dd className="font-medium">{displayLabel(profile.data.trade)}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-ink-soft">Phone</dt>
                    <dd className="num font-medium">{profile.data.phone}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-ink-soft">Verified</dt>
                    <dd className="font-medium">{profile.data.verified ? 'Yes' : 'Not yet'}</dd>
                  </div>
                </dl>) : null}
            </div>

            <div>
              <p className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                What happens next
              </p>
              <ol className="mt-2 space-y-2.5">
                {[
            'Your estate office adds your email to their estate.',
            'The estate appears in your account as soon as they do.',
            'Assigned work then appears under “My work”.',
        ].map((step, index) => (<li key={step} className="flex gap-3 text-[13px] text-ink-soft">
                    <span className="num mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-xs border border-ink/20 text-[11px] font-semibold text-accent-ink">
                      {index + 1}
                    </span>
                    {step}
                  </li>))}
              </ol>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3 border-t border-ink/15 pt-5">
            <Button variant="primary" onClick={reload} disabled={loading}>
              {loading ? 'Checking…' : 'Check again'}
            </Button>
            <Button variant="ghost" onClick={() => {
            logout();
            navigate('/');
        }}>
              <IconLogout size={16}/>
              Sign out
            </Button>
          </div>
        </Card>
      </div>
    </PublicShell>);
}
