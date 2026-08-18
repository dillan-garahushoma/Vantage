import { cn } from "@/lib/utils";

/**
 * FibreHood wordmark. The "oo" in "hood" is a yellow infinity motif.
 * Placeholder for the official high-res SVG brand asset (not yet supplied).
 */
export function Logo({
  className,
  onDark = false,
}: {
  className?: string;
  onDark?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-0 font-extrabold tracking-tight leading-none select-none",
        onDark ? "text-white" : "text-navy",
        className,
      )}
      aria-label="FibreHood"
    >
      FibreH
      <svg
        viewBox="0 0 44 24"
        className="mx-[1px] h-[0.62em] self-center"
        role="img"
        aria-hidden="true"
        focusable="false"
      >
        <path
          d="M11 12c0-3.3 2.7-6 6-6 4.4 0 5.6 12 10 12 3.3 0 6-2.7 6-6s-2.7-6-6-6c-4.4 0-5.6 12-10 12-3.3 0-6-2.7-6-6z"
          fill="none"
          stroke="#FFCC00"
          strokeWidth="4.4"
          strokeLinecap="round"
        />
      </svg>
      d
    </span>
  );
}
