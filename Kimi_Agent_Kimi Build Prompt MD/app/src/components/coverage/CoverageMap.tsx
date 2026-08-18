import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Coordinates } from "@/types";
import { HARARE_CENTER, mockPolygons } from "@/lib/mock/coverage";
import { site } from "@/config/site";

/**
 * Leaflet coverage map.
 * Supports: address marker, mock coverage polygons, zoom-to-result,
 * and click-to-pin lookup. Authoritative polygons will come from the
 * backend once real KML/GeoJSON coverage data is supplied.
 */
export function CoverageMap({
  pin,
  highlightPolygonId,
  onMapClick,
  className,
}: {
  pin?: Coordinates;
  highlightPolygonId?: string;
  onMapClick?: (coords: Coordinates) => void;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Layer | null>(null);
  const polygonsRef = useRef<L.Polygon[]>([]);
  const onClickRef = useRef(onMapClick);
  onClickRef.current = onMapClick;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [HARARE_CENTER.lat, HARARE_CENTER.lon],
      zoom: 12,
      scrollWheelZoom: false,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Mock coverage polygons — clearly development data.
    polygonsRef.current = mockPolygons.map((p) => {
      const latLngs = p.ring.map(([lon, lat]) => [lat, lon] as [number, number]);
      const polygon = L.polygon(latLngs, {
        color: site.brand.navy,
        weight: 2,
        fillColor: site.brand.yellow,
        fillOpacity: 0.18,
      })
        .addTo(map)
        .bindTooltip(`${p.name} — development mock data`, { sticky: true });
      (polygon as unknown as { __id: string }).__id = p.id;
      return polygon;
    });

    map.on("click", (e: L.LeafletMouseEvent) => {
      onClickRef.current?.({ lat: e.latlng.lat, lon: e.latlng.lng });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Pin updates
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }
    if (pin) {
      const icon = L.divIcon({
        className: "",
        html: `<div style="width:22px;height:22px;border-radius:50%;background:${site.brand.navy};border:4px solid ${site.brand.yellow};box-shadow:0 2px 8px rgba(0,0,0,.35)"></div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });
      markerRef.current = L.marker([pin.lat, pin.lon], { icon, keyboard: false })
        .addTo(map)
        .bindPopup("Checked address")
        .openPopup();
      map.flyTo([pin.lat, pin.lon], Math.max(map.getZoom(), 14), { duration: 0.8 });
    }
  }, [pin]);

  // Polygon highlight
  useEffect(() => {
    polygonsRef.current.forEach((polygon) => {
      const id = (polygon as unknown as { __id: string }).__id;
      if (id === highlightPolygonId) {
        polygon.setStyle({ fillOpacity: 0.4, weight: 3, color: site.brand.yellow });
        polygon.bringToFront();
      } else {
        polygon.setStyle({ fillOpacity: 0.18, weight: 2, color: site.brand.navy });
      }
    });
  }, [highlightPolygonId]);

  return (
    <div
      ref={containerRef}
      role="application"
      aria-label="Coverage map of Harare (development mock data). Click the map to check a location."
      className={className ?? "h-72 w-full sm:h-96"}
    />
  );
}
