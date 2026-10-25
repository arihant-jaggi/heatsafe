import { useEffect, useMemo, useState } from "react";
import { MapContainer, GeoJSON, Marker, Popup, useMapEvents } from "react-leaflet";
import L from "leaflet";

type LatLon = { lat: number; lon: number };

function ClickPicker({ onPick }: { onPick: (p: LatLon) => void }) {
  useMapEvents({
    click(e) {
      onPick({ lat: e.latlng.lat, lon: e.latlng.lng });
    },
  });
  return null;
}

function pinHtml(letter: string, bg: string) {
  return `<div class="pin-wrap" style="color:${bg}">
    <div class="pin-drop" style="width:26px;height:26px;border-radius:50%;background:${bg};color:#fff;
      display:grid;place-items:center;font-weight:800;font-size:13px;border:2px solid #fff;
      box-shadow:0 4px 10px rgba(20,35,55,0.35)">${letter}</div>
    <span class="pin-ripple"></span>
  </div>`;
}

// Small signature so a new route re-mounts the GeoJSON and replays the trace.
function geoKey(g: any): string {
  try {
    const c = g?.features?.[0]?.geometry?.coordinates;
    return `${g?.features?.length}-${c?.length}-${c?.[0]?.[0]}`;
  } catch {
    return Math.random().toString();
  }
}

// Self-hosted basemap: Miami Beach streets, buildings and street trees drawn
// from the router's own OSM data (built by backend/scripts/build_basemap.py),
// so the map needs no third-party tile service or API key.
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const MAP_BG = "#0e1a2a";
const BOUNDS: [[number, number], [number, number]] = [[25.75, -80.18], [25.91, -80.10]];

type Basemap = { streets?: any; buildings?: any; trees?: any };

function useBasemap(): Basemap {
  const [layers, setLayers] = useState<Basemap>({});
  useEffect(() => {
    let alive = true;
    for (const name of ["buildings", "streets", "trees"] as const) {
      fetch(`/basemap/${name}.json`)
        .then((r) => r.json())
        .then((data) => alive && setLayers((prev) => ({ ...prev, [name]: data })))
        .catch(() => {});
    }
    return () => {
      alive = false;
    };
  }, []);
  return layers;
}

const STREET_STYLE: Record<string, { color: string; weight: number; opacity: number }> = {
  major: { color: "#9db8d6", weight: 2.6, opacity: 0.85 },
  minor: { color: "#4f6a8a", weight: 1.3, opacity: 0.8 },
  foot: { color: "#3a5170", weight: 0.7, opacity: 0.55 },
};

const treeRenderer = L.canvas({ padding: 0.5 });
function treeDot(_f: any, latlng: L.LatLng) {
  return L.circleMarker(latlng, { renderer: treeRenderer, radius: 2.4, stroke: false, fillColor: "#4cc38a", fillOpacity: 0.75, interactive: false });
}

const WATER_LABELS: { pos: [number, number]; text: string }[] = [
  { pos: [25.862, -80.104], text: "Atlantic Ocean" },
  { pos: [25.805, -80.168], text: "Biscayne Bay" },
];
const waterIcon = (text: string) =>
  L.divIcon({ html: `<span class="hs-water">${text}</span>`, className: "", iconSize: [140, 20], iconAnchor: [70, 10] });

// Street trees only once zoomed in; at city scale they merge into a blob.
function TreeLayer({ data }: { data: any }) {
  const [zoom, setZoom] = useState(13);
  useMapEvents({ zoomend: (e) => setZoom(e.target.getZoom()) });
  return zoom >= 15 ? <GeoJSON data={data} interactive={false as any} pointToLayer={treeDot} /> : null;
}

const DRAW_MS = 1800;
const DRAW_EASE = "cubic-bezier(0.32, 0.72, 0.3, 1)";

/**
 * Draw a Leaflet vector layer's SVG path from A to B by animating
 * stroke-dashoffset over the path's *actual* length. A forced reflow between
 * setting the full offset and the transition guarantees the browser paints the
 * start state instead of jumping straight to the end.
 */
function drawLayer(layer: any) {
  layer.eachLayer?.((sub: any) => {
    const path: SVGPathElement | undefined = sub?._path;
    if (!path || typeof path.getTotalLength !== "function") return;
    const len = path.getTotalLength();
    path.style.transition = "none";
    path.style.strokeDasharray = `${len}`;
    path.style.strokeDashoffset = `${len}`;
    path.getBoundingClientRect(); // force reflow so the start state is painted
    path.style.transition = `stroke-dashoffset ${DRAW_MS}ms ${DRAW_EASE}`;
    path.style.strokeDashoffset = "0";
  });
}

function drawHandler() {
  return {
    add: (e: any) => {
      const layer = e.target;
      layer.bringToFront?.();
      requestAnimationFrame(() => drawLayer(layer));
    },
  };
}

export function MapView(props: {
  start?: LatLon;
  end?: LatLon;
  onPickStart: (p: LatLon) => void;
  onPickEnd: (p: LatLon) => void;
  picking: "start" | "end" | null;
  fastestGeo?: any;
  heatsafeGeo?: any;
  coolingRouteGeo?: any;
  coolingStop?: { lat: number; lon: number; name: string } | null;
  coolingGeo?: any;
  showCooling: boolean;
}) {
  const center: [number, number] = [25.83, -80.13];
  const basemap = useBasemap();
  // Basemap on its own canvas (fast for ~35k shapes); routes stay SVG so they can animate.
  const baseRenderer = useMemo(() => L.canvas({ padding: 0.5 }), []);

  const startIcon = useMemo(() => L.divIcon({ html: pinHtml("A", "#1e3a5f"), className: "", iconSize: [26, 26], iconAnchor: [13, 13] }), []);
  const endIcon = useMemo(() => L.divIcon({ html: pinHtml("B", "#e0870b"), className: "", iconSize: [26, 26], iconAnchor: [13, 13] }), []);
  const coolingIcon = useMemo(
    () => L.divIcon({ html: `<div class="pin-wrap"><div class="pin-drop" style="font-size:22px;line-height:22px">❄️</div></div>`, className: "", iconSize: [22, 22], iconAnchor: [11, 11] }),
    []
  );

  const onPick = (p: LatLon) => {
    if (props.picking === "start") props.onPickStart(p);
    if (props.picking === "end") props.onPickEnd(p);
  };

  return (
    <MapContainer
      center={center}
      zoom={13}
      minZoom={12}
      maxZoom={18}
      maxBounds={BOUNDS}
      maxBoundsViscosity={0.8}
      className="hs-map"
      style={{ height: "72vh", width: "100%", background: MAP_BG }}
    >
      {basemap.buildings && (
        <GeoJSON
          data={basemap.buildings}
          {...({ renderer: baseRenderer } as any)}
          interactive={false as any}
          style={() => ({ stroke: false, fillColor: "#1b2c42", fillOpacity: 1 }) as any}
          {...({ attribution: OSM_ATTRIBUTION } as any)}
        />
      )}
      {basemap.streets && (
        <>
          <GeoJSON
            data={{ ...basemap.streets, features: basemap.streets.features.filter((f: any) => f.properties.c === "major") }}
            {...({ renderer: baseRenderer } as any)}
            interactive={false as any}
            style={() => ({ color: "#5d86b3", weight: 7, opacity: 0.16 }) as any}
          />
          <GeoJSON
            data={basemap.streets}
            {...({ renderer: baseRenderer } as any)}
            interactive={false as any}
            style={(f: any) => STREET_STYLE[f?.properties?.c ?? "minor"] as any}
          />
        </>
      )}
      {WATER_LABELS.map((w) => (
        <Marker key={w.text} position={w.pos} icon={waterIcon(w.text)} interactive={false} keyboard={false} />
      ))}
      {basemap.trees && <TreeLayer data={basemap.trees} />}

      {props.picking && <ClickPicker onPick={onPick} />}

      {props.start && (
        <Marker key={`s-${props.start.lat},${props.start.lon}`} position={[props.start.lat, props.start.lon]} icon={startIcon}>
          <Popup>Start</Popup>
        </Marker>
      )}
      {props.end && (
        <Marker key={`e-${props.end.lat},${props.end.lon}`} position={[props.end.lat, props.end.lon]} icon={endIcon}>
          <Popup>Destination</Popup>
        </Marker>
      )}

      {props.showCooling && props.coolingGeo && (
        <GeoJSON data={props.coolingGeo} style={() => ({ color: "#0e7490", weight: 1.5, opacity: 0.35, fillColor: "#0e7490", fillOpacity: 0.08 })} />
      )}

      {props.coolingRouteGeo && (
        <GeoJSON
          key={`c-${geoKey(props.coolingRouteGeo)}`}
          data={props.coolingRouteGeo}
          style={() => ({ color: "#2dd4bf", weight: 6, opacity: 0.9 }) as any}
          eventHandlers={drawHandler()}
        />
      )}

      {props.fastestGeo && (
        <GeoJSON
          key={`f-${geoKey(props.fastestGeo)}`}
          data={props.fastestGeo}
          style={() => ({ color: "#e0870b", weight: 6, opacity: 0.95 }) as any}
          eventHandlers={drawHandler()}
        />
      )}

      {props.heatsafeGeo && (
        <>
          <GeoJSON
            key={`h-${geoKey(props.heatsafeGeo)}`}
            data={props.heatsafeGeo}
            style={() => ({ color: "#6cc4ff", weight: 7, opacity: 0.98 }) as any}
            eventHandlers={drawHandler()}
          />
          {/* comet overlay only on HeatSafe — starts after the draw completes */}
          <GeoJSON
            key={`hc-${geoKey(props.heatsafeGeo)}`}
            data={props.heatsafeGeo}
            style={() => ({ color: "#ffffff", weight: 3, opacity: 0.9, className: "route-comet" }) as any}
            interactive={false as any}
          />
        </>
      )}

      {props.coolingStop && (
        <Marker key={`cs-${props.coolingStop.lat}`} position={[props.coolingStop.lat, props.coolingStop.lon]} icon={coolingIcon}>
          <Popup>A/C stop: {props.coolingStop.name}</Popup>
        </Marker>
      )}
    </MapContainer>
  );
}
