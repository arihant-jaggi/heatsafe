import { useMemo } from "react";
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMapEvents } from "react-leaflet";
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
    <MapContainer center={center} zoom={12} style={{ height: "72vh", width: "100%" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
      />

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
          style={() => ({ color: "#0e7490", weight: 6, opacity: 0.9 }) as any}
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
            style={() => ({ color: "#1e3a5f", weight: 7, opacity: 0.98 }) as any}
            eventHandlers={drawHandler()}
          />
          {/* comet overlay only on HeatSafe — starts after the draw completes */}
          <GeoJSON
            key={`hc-${geoKey(props.heatsafeGeo)}`}
            data={props.heatsafeGeo}
            style={() => ({ color: "#7fb0e0", weight: 3, opacity: 0.9, className: "route-comet" }) as any}
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
