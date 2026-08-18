import { useCallback, useState } from "react";
import type { Coordinates, CoverageResult } from "@/types";
import { coverageService, UnknownAddressError } from "@/lib/services/coverageService";

export type CoverageLookupState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "result"; result: CoverageResult }
  | { phase: "unknown_address"; address: string };

/**
 * useCoverageLookup — the only coverage API the UI talks to.
 * Swapping the mock service for the real backend requires no UI changes.
 */
export function useCoverageLookup() {
  const [state, setState] = useState<CoverageLookupState>({ phase: "idle" });

  const lookupAddress = useCallback(async (address: string) => {
    setState({ phase: "loading" });
    try {
      const result = await coverageService.lookupByAddress(address);
      setState({ phase: "result", result });
    } catch (err) {
      if (err instanceof UnknownAddressError) {
        setState({ phase: "unknown_address", address });
      } else {
        setState({ phase: "unknown_address", address });
      }
    }
  }, []);

  const lookupCoordinates = useCallback(async (coords: Coordinates) => {
    setState({ phase: "loading" });
    const result = await coverageService.lookupByCoordinates(coords);
    setState({ phase: "result", result });
  }, []);

  const reset = useCallback(() => setState({ phase: "idle" }), []);

  return { state, lookupAddress, lookupCoordinates, reset };
}
