import { Link } from "react-router";
import { Logo } from "@/components/brand/Logo";
import { site } from "@/config/site";
import { whatsappService } from "@/lib/services/whatsappService";

export function SiteFooter() {
  return (
    <footer className="bg-navy text-white">
      <div className="container-site grid gap-10 py-14 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo onDark className="text-2xl" />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/75">
            {site.description}
          </p>
          <p className="mt-4 text-sm text-white/75">
            WhatsApp:{" "}
            <a
              href={whatsappService.buildUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-gold underline-offset-4 hover:underline"
            >
              {site.whatsapp.display}
            </a>
            {!site.whatsapp.confirmed && (
              <span className="mt-1 block text-xs text-white/50">
                (number from earlier research — to be confirmed before launch)
              </span>
            )}
          </p>
        </div>

        <nav aria-label="Footer">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gold">Explore</h2>
          <ul className="mt-4 space-y-2 text-sm">
            <li><Link className="text-white/80 hover:text-white" to="/">Home</Link></li>
            <li><Link className="text-white/80 hover:text-white" to="/coverage">Check Coverage</Link></li>
            <li><Link className="text-white/80 hover:text-white" to="/plans">Plans</Link></li>
            <li><Link className="text-white/80 hover:text-white" to="/about">About</Link></li>
            <li><Link className="text-white/80 hover:text-white" to="/faq">FAQ</Link></li>
            <li><Link className="text-white/80 hover:text-white" to="/contact">Contact</Link></li>
          </ul>
        </nav>

        <nav aria-label="Legal">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gold">Legal</h2>
          <ul className="mt-4 space-y-2 text-sm">
            <li><Link className="text-white/80 hover:text-white" to="/privacy">Privacy Policy</Link></li>
            <li><Link className="text-white/80 hover:text-white" to="/terms">Terms of Service</Link></li>
          </ul>
          <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-gold">Contact</h2>
          <p className="mt-4 text-sm text-white/80">
            Fastest response: WhatsApp. Full contact options are on the{" "}
            <Link to="/contact" className="text-gold underline-offset-4 hover:underline">
              contact page
            </Link>
            .
          </p>
        </nav>
      </div>
      <div className="border-t border-white/10">
        <div className="container-site flex flex-col gap-2 py-5 text-xs text-white/50 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} FibreHood. All rights reserved.</p>
          <p>{site.domain}</p>
        </div>
      </div>
    </footer>
  );
}
