import type { Coordinates } from "@/types";

/**
 * MOCK coverage fixtures — development only, clearly labelled.
 * Real coverage polygons will arrive as KML/GeoJSON/shapefile via the admin
 * upload pipeline and be served by the backend (PostGIS point-in-polygon).
 * These shapes are approximate rectangles around Harare suburbs so the UI
 * can be exercised end-to-end. They are NOT real coverage.
 */

export interface MockPolygon {
  id: string;
  name: string;
  /** ring of [lon, lat] */
  ring: [number, number][];
}

export const MOCK_COVERAGE_VERSION = 1;

export const mockPolygons: MockPolygon[] = [
  {
    id: "mock-avondale",
    name: "Avondale (mock coverage)",
    ring: [
      [31.028, -17.795],
      [31.052, -17.795],
      [31.052, -17.778],
      [31.028, -17.778],
      [31.028, -17.795],
    ],
  },
  {
    id: "mock-borrowdale",
    name: "Borrowdale (mock coverage)",
    ring: [
      [31.075, -17.755],
      [31.115, -17.755],
      [31.115, -17.725],
      [31.075, -17.725],
      [31.075, -17.755],
    ],
  },
  {
    id: "mock-msasa",
    name: "Msasa / Graniteside (mock coverage)",
    ring: [
      [31.055, -17.855],
      [31.09, -17.855],
      [31.09, -17.83],
      [31.055, -17.83],
      [31.055, -17.855],
    ],
  },
];

/** Mock address book for keyword-based development geocoding. */
export const mockAddressBook: { keywords: string[]; label: string; coordinates: Coordinates }[] = [
  {
    keywords: ["avondale", "king george"],
    label: "Avondale, Harare",
    coordinates: { lat: -17.7865, lon: 31.04 },
  },
  {
    keywords: ["borrowdale", "sam levy"],
    label: "Borrowdale, Harare",
    coordinates: { lat: -17.74, lon: 31.095 },
  },
  {
    keywords: ["msasa", "graniteside"],
    label: "Msasa, Harare",
    coordinates: { lat: -17.842, lon: 31.072 },
  },
  {
    keywords: ["cbd", "first street", "harare centre"],
    label: "Harare CBD (outside mock coverage)",
    coordinates: { lat: -17.8216, lon: 31.0492 },
  },
  {
    keywords: ["highlands"],
    label: "Highlands, Harare (near mock coverage)",
    coordinates: { lat: -17.776, lon: 31.062 },
  },
  {
    keywords: ["bulawayo"],
    label: "Bulawayo (outside mock coverage)",
    coordinates: { lat: -20.15, lon: 28.5833 },
  },
];

export const HARARE_CENTER: Coordinates = { lat: -17.8252, lon: 31.0335 };

/** Ray-casting point-in-polygon over a [lon,lat] ring. */
export function pointInRing(lon: number, lat: number, ring: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersect =
      yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

export function ringCentroid(ring: [number, number][]): Coordinates {
  let lat = 0;
  let lon = 0;
  const n = ring.length - 1; // last point repeats the first
  for (let i = 0; i < n; i++) {
    lon += ring[i][0];
    lat += ring[i][1];
  }
  return { lat: lat / n, lon: lon / n };
}

export function haversineM(a: Coordinates, b: Coordinates): number {
  const R = 6371000;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const la = (a.lat * Math.PI) / 180;
  const lb = (b.lat * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(la) * Math.cos(lb) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
