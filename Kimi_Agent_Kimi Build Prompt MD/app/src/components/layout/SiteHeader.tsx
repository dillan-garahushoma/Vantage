import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router";
import { Menu, X, MessageCircle } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { whatsappService } from "@/lib/services/whatsappService";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", label: "Home" },
  { to: "/coverage", label: "Coverage" },
  { to: "/plans", label: "Plans" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-white/90 backdrop-blur">
      <div className="container-site flex h-16 items-center justify-between gap-4">
        <Link to="/" className="shrink-0" aria-label="FibreHood home">
          <Logo className="text-xl sm:text-2xl" />
        </Link>

        <nav aria-label="Primary" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-navy-50 text-navy"
                        : "text-ink/70 hover:bg-fog hover:text-ink"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <a
            href={whatsappService.buildUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-semibold text-[#147a3c] hover:bg-[#1FA855]/10"
            aria-label="Chat on WhatsApp"
          >
            <MessageCircle className="h-4 w-4" aria-hidden="true" />
            WhatsApp
          </a>
          <Button onClick={() => navigate("/coverage")} className="bg-navy text-white hover:bg-navy-600">
            Check Coverage
          </Button>
        </div>

        <button
          type="button"
          className="rounded-md p-2 text-navy md:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-border bg-white md:hidden">
          <ul className="container-site flex flex-col gap-1 py-3">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `block rounded-md px-3 py-2.5 text-base font-medium ${
                      isActive ? "bg-navy-50 text-navy" : "text-ink/80 hover:bg-fog"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
            <li className="pt-2">
              <Button
                onClick={() => {
                  setOpen(false);
                  navigate("/coverage");
                }}
                className="w-full bg-gold text-navy hover:bg-gold-300"
              >
                Check Coverage
              </Button>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
