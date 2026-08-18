import { useState } from "react";
import { LocateFixed, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export function AddressSearchForm({
  onSearch,
  onUseLocation,
  loading = false,
  autoFocus = false,
  defaultValue = "",
}: {
  onSearch: (address: string) => void;
  onUseLocation?: () => void;
  loading?: boolean;
  autoFocus?: boolean;
  defaultValue?: string;
}) {
  const [value, setValue] = useState(defaultValue);
  const [error, setError] = useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (value.trim().length < 3) {
      setError("Please enter at least a few characters of your address or suburb.");
      return;
    }
    setError(null);
    onSearch(value.trim());
  }

  return (
    <form onSubmit={submit} className="w-full" noValidate>
      <label htmlFor="address-input" className="sr-only">
        Enter your address
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink/40"
            aria-hidden="true"
          />
          <input
            id="address-input"
            type="text"
            inputMode="text"
            autoComplete="street-address"
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus={autoFocus}
            placeholder="Enter your address or suburb…"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError(null);
            }}
            aria-invalid={!!error}
            aria-describedby={error ? "address-error" : undefined}
            className="h-12 w-full rounded-lg border border-input bg-white pl-10 pr-3 text-base text-ink placeholder:text-ink/40 focus-visible:ring-gold"
          />
        </div>
        <Button
          type="submit"
          disabled={loading}
          className="h-12 bg-gold px-6 text-base font-bold text-navy hover:bg-gold-300"
        >
          {loading ? "Checking…" : "Check Coverage"}
        </Button>
      </div>
      {error && (
        <p id="address-error" role="alert" className="mt-2 text-sm font-medium text-destructive">
          {error}
        </p>
      )}
      {onUseLocation && (
        <button
          type="button"
          onClick={onUseLocation}
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-navy underline-offset-4 hover:underline"
        >
          <LocateFixed className="h-4 w-4" aria-hidden="true" />
          Use my location
        </button>
      )}
    </form>
  );
}
