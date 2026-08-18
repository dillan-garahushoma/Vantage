import { MessageCircle } from "lucide-react";
import { whatsappService } from "@/lib/services/whatsappService";
import { site } from "@/config/site";
import { cn } from "@/lib/utils";

export function WhatsAppButton({
  address,
  planName,
  className,
  variant = "solid",
  children,
}: {
  address?: string;
  planName?: string;
  className?: string;
  variant?: "solid" | "outline" | "fab";
  children?: React.ReactNode;
}) {
  const label = children ?? "Chat on WhatsApp";
  const url = whatsappService.buildUrl({ address, planName });
  const track = () =>
    import("@/lib/services/analytics").then((m) =>
      m.analytics.track("whatsapp.click", { via_wa_me: true }),
    );

  if (variant === "fab") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        onClick={track}
        aria-label={`Chat with FibreHood on WhatsApp (${site.whatsapp.display})`}
        title={`WhatsApp ${site.whatsapp.display}`}
        className={cn(
          "fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#1FA855] text-white shadow-lg transition-transform hover:scale-105 focus-visible:ring-gold",
          className,
        )}
      >
        <MessageCircle className="h-7 w-7" aria-hidden="true" />
      </a>
    );
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={track}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-semibold transition-colors",
        variant === "solid"
          ? "bg-[#1FA855] text-white hover:bg-[#178a45]"
          : "border-2 border-[#1FA855] text-[#147a3c] hover:bg-[#1FA855]/10",
        className,
      )}
    >
      <MessageCircle className="h-4 w-4" aria-hidden="true" />
      {label}
    </a>
  );
}
