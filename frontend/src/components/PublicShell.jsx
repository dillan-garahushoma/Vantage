import { Wordmark } from './Brand';
import { Link } from 'react-router-dom';
import { LinkButton } from './ui';
export function PublicShell({ children }) {
    return (<div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-ink/15 bg-paper/95 backdrop-blur-sm">
        {/* `flex-wrap`: if the wordmark and the two entry actions ever stop
            fitting on one line, the actions wrap instead of widening the page. */}
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-5 py-3">
          <Wordmark />
          <nav className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            {/* Below `sm` the header keeps only the two entry actions: three
            buttons plus the wordmark is what pushed a 390px page sideways.
            The directory is still one tap away — in the hero and the footer. */}
            {/* The wrapper carries the responsive display, not the button: `LinkButton`
            already sets `inline-flex`, and two unprefixed display utilities resolve by
            stylesheet order rather than class order — `hidden` lost, so the button kept
            showing on phones and pushed the header 11px past a 360px viewport. */}
            <span className="hidden sm:inline-flex">
              <LinkButton to="/estates" variant="ghost">
                Find a complex
              </LinkButton>
            </span>
            <LinkButton to="/login" variant="ghost" className="min-h-11 whitespace-nowrap px-2.5 sm:px-3.5">
              Sign in
            </LinkButton>
            <LinkButton to="/register" variant="primary" className="min-h-11 whitespace-nowrap px-2.5 sm:px-3.5">
              Create account
            </LinkButton>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="mt-16 border-t border-ink/15 bg-surface">
        <div className="mx-auto flex max-w-[1200px] flex-col gap-3 px-5 py-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[13px] font-medium tracking-[0.12em]">VALORA</p>
            <p className="mt-1 max-w-md text-[12.5px] text-ink-muted">
              Property Health Intelligence for South African private residential estates. Built on
              the estate — the tenant and operational-health boundary.
            </p>
          </div>
          <div className="sm:text-right">
            <Link to="/contact" className="mr-4 text-[13px] font-medium text-accent-ink hover:underline">Contact us</Link>
            <Link to="/estates" className="text-[13px] font-medium text-accent-ink hover:underline">
              Find a published complex
            </Link>
            <p className="num mt-1.5 text-[11px] text-ink-muted">
              Community events → community health → property health → investment intelligence
            </p>
          </div>
        </div>
      </footer>
    </div>);
}
