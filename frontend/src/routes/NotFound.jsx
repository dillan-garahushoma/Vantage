import { PublicShell } from '../components/PublicShell';
import { LinkButton } from '../components/ui';
export function NotFound() {
    return (<PublicShell>
      <div className="mx-auto max-w-xl px-5 py-24 text-center">
        <p className="num text-[13px] tracking-[0.2em] text-ink-muted uppercase">Error 404</p>
        <h1 className="mt-4 text-[30px] font-semibold">This page is not on the plan</h1>
        <p className="mt-3 text-[14.5px] text-ink-soft">
          The page you asked for does not exist. It may have been moved, or the link may be out of
          date.
        </p>
        <div className="mt-7 flex justify-center gap-3">
          <LinkButton to="/" variant="primary">
            Back to home
          </LinkButton>
          <LinkButton to="/app" variant="secondary">
            Go to the app
          </LinkButton>
        </div>
      </div>
    </PublicShell>);
}
