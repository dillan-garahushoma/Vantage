import { Link } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { useEstate } from '../context/EstateContext';

export function WelcomeSuccess() {
  const { estates } = useEstate();
  const estateName = estates?.[0]?.estate_name ?? null;

  if (!estateName) {
    // Request is still pending approval
    return (
      <AuthShell
        step={3}
        totalSteps={3}
        stepLabels={['Account', 'Join estate', "You're in"]}
        eyebrow="Resident onboarding"
        title="Request submitted"
        intro="Your estate office will review and approve your request."
      >
        <div className="space-y-4 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-ochre-wash text-[28px]">
            ⏳
          </div>
          <p className="text-[14px] text-ink-soft">
            You'll be notified once an administrator approves your access. Check back here anytime.
          </p>
          <Link
            to="/request-access"
            className="inline-block text-[13.5px] font-medium text-accent-ink hover:underline"
          >
            View your request status →
          </Link>
        </div>
      </AuthShell>
    );
  }

  const actions = [
    { label: 'Report a maintenance issue', to: '/app/complaints', primary: true },
    { label: 'Read estate announcements', to: '/app/announcements', primary: false },
    { label: 'View your unit details', to: '/app/properties', primary: false },
  ];

  return (
    <AuthShell
      step={3}
      totalSteps={3}
      stepLabels={['Account', 'Join estate', "You're in"]}
      eyebrow="Estate access"
      title={`Welcome to ${estateName}`}
      intro="Your membership is confirmed. Here's what you can do first."
    >
      <div className="space-y-4">
        {/* Estate visual banner */}
        <div className="relative mb-5 overflow-hidden rounded-xl border border-line shadow-xs">
          <img
            src="/estate-hero.jpg"
            alt={estateName}
            className="h-36 w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
          <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-white">
            <div>
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-white/80">
                Community Access Confirmed
              </span>
              <span className="text-[15px] font-bold">
                {estateName}
              </span>
            </div>
            <span className="flex items-center gap-1 rounded-full bg-mint/90 px-2.5 py-0.5 text-[11px] font-semibold text-white shadow-xs backdrop-blur-xs">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-white" />
              Active
            </span>
          </div>
        </div>

        {/* Action links */}
        {actions.map((action) => (
          <Link
            key={action.to}
            to={action.to}
            className="flex w-full items-center justify-between rounded-xl border border-line bg-surface px-4 py-3.5 text-[0.88rem] font-medium transition-colors hover:border-accent hover:bg-canvas"
          >
            <span className={action.primary ? 'text-accent-ink' : 'text-ink'}>
              {action.label}
            </span>
            <span className="text-ink-muted">→</span>
          </Link>
        ))}

        <p className="pt-2 text-center text-[12px] text-ink-muted">
          You can always reach these from the sidebar once you're inside the app.
        </p>
      </div>
    </AuthShell>
  );
}
