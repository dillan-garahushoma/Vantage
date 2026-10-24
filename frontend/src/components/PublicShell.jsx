import { House } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Wordmark } from './Brand';
import { LinkButton } from './ui';

export function PublicShell({ children }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-ink/15 bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-5 py-3">
          <Wordmark />
          <nav className="flex flex-wrap items-center justify-end gap-1.5 sm:gap-2" aria-label="Main navigation">
            <Link
              to="/"
              aria-label="Home"
              aria-current={typeof window !== 'undefined' && window.location.pathname === '/' ? 'page' : undefined}
              className="inline-flex items-center justify-center gap-1.5 border border-transparent px-2.5 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-ink/5 hover:text-ink sm:px-3.5"
            >
              <House className="h-4 w-4" aria-hidden="true" />
              <span>Home</span>
            </Link>
            <LinkButton to="/estates" variant="ghost" className="hidden sm:inline-flex">
              Find a complex
            </LinkButton>
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
    </div>
  );
}
