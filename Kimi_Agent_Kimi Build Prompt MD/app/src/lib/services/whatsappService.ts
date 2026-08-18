import { site } from "@/config/site";
import { analytics } from "./analytics";

/**
 * WhatsApp service — centralized wa.me URL generation.
 * The configured number is a research reference that REQUIRES CONFIRMATION
 * before launch (see config/site.ts).
 */
export interface WhatsAppContext {
  address?: string;
  planName?: string;
}

export const whatsappService = {
  buildUrl(context?: WhatsAppContext): string {
    let message = site.whatsapp.defaultMessage;
    if (context?.address) {
      message = `Hi FibreHood, I'd like to enquire about fibre at ${context.address}.`;
      if (context.planName) message += ` I'm interested in ${context.planName}.`;
    } else if (context?.planName) {
      message = `Hi FibreHood, I'm interested in ${context.planName}.`;
    }
    return `https://wa.me/${site.whatsapp.numberE164}?text=${encodeURIComponent(message)}`;
  },

  open(context?: WhatsAppContext) {
    analytics.track("whatsapp.click", { via_wa_me: true });
    window.open(this.buildUrl(context), "_blank", "noopener,noreferrer");
  },

  /** Shown wherever the number appears until the business confirms it. */
  confirmationNotice: site.whatsapp.confirmed
    ? null
    : "This WhatsApp number is from earlier research and will be confirmed before launch.",
};
