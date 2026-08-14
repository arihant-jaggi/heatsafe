import { useEffect, useState } from "react";
import { MapView } from "./map/MapView";
import { RoutePanel } from "./ui/RoutePanel";
import { AddressAutocomplete } from "./ui/AddressAutocomplete";
import { route, cooling, conditions } from "./api";
import { Reveal } from "./ui/motion";

type LatLon = { lat: number; lon: number };

function coordText(p: LatLon) {
  return `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`;
}

// Heat-index severity -> pill styling + advice.
function heatLevel(hiC: number | undefined) {
  if (hiC == null) return { cls: "heat-green", label: "Loading…", advice: "" };
  if (hiC >= 46) return { cls: "heat-red", label: "Extreme heat", advice: "Avoid non-essential walks right now." };
  if (hiC >= 40) return { cls: "heat-orange", label: "Dangerous heat", advice: "Avoid long stretches in direct sun." };
  if (hiC >= 32) return { cls: "heat-orange", label: "Elevated heat", advice: "Seek shade on longer walks." };
  return { cls: "heat-green", label: "Comfortable", advice: "Pleasant conditions for walking." };
}

export default function App() {
  const [start, setStart] = useState<LatLon | undefined>();
  const [end, setEnd] = useState<LatLon | undefined>();
  const [picking, setPicking] = useState<"start" | "end" | null>(null);

  const [startText, setStartText] = useState<string | undefined>();
  const [endText, setEndText] = useState<string | undefined>();
  const [endLabel, setEndLabel] = useState<string | undefined>();

  const [data, setData] = useState<any>(null);
  const [hour, setHour] = useState<number | "">("");
  const [viaCooling, setViaCooling] = useState(false);

  const [cond, setCond] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [coolingGeo, setCoolingGeo] = useState<any>(null);
  const [showCooling, setShowCooling] = useState(false);

  useEffect(() => {
    cooling().then(setCoolingGeo).catch(() => {});
  }, []);

  useEffect(() => {
    conditions(hour === "" ? null : hour).then(setCond).catch(() => {});
  }, [hour]);

  async function doRoute() {
    if (!start || !end) {
      setError("Set a Start and Destination first (type an address, or use Map to click a point).");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await route(start, end, { hour: hour === "" ? null : hour, via_cooling: viaCooling });
      setData(res);
      if (res.conditions) setCond(res.conditions);
    } catch (e: any) {
      setError(`Route failed: ${e?.message ?? e}`);
    } finally {
      setLoading(false);
    }
  }

  const lvl = heatLevel(cond?.heat_index_c);
  const sunPct = cond ? Math.max(0, Math.min(100, (cond.sun_altitude_deg / 90) * 100)) : 0;

  return (
    <div className="wrap section" style={{ paddingTop: 34 }}>
      {/* ---------------- CONDITIONS BANNER ---------------- */}
      <Reveal>
        <section className="card glass-bubble" style={{ padding: "26px 30px", marginBottom: 34 }}>
          <div className="orb orb-a" /><div className="orb orb-b" /><div className="sheen" />
          <div className="cond-grid">
            <div>
              <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
                Right now in Miami Beach{cond ? ` · ${cond.time_label}` : ""}
              </div>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 4 }}>
                <span style={{ fontSize: 60, fontWeight: 800, color: "var(--amber-ink)", letterSpacing: "-0.03em", lineHeight: 1 }}>
                  {cond ? Math.round(cond.heat_index_c) : "—"}
                </span>
                <span style={{ fontSize: 18, fontWeight: 600, color: "var(--slate-2)", marginTop: 6 }}>°C</span>
                <span className={`heat-pill ${lvl.cls}`} style={{ marginLeft: 14, marginTop: 6 }}>
                  <span className="dot" />{lvl.label}
                </span>
              </div>
              <div className="muted" style={{ fontSize: 13.5, marginTop: 8 }}>
                {cond ? `Feels like ${Math.round(cond.heat_index_f)}°F` : "Reading conditions…"}
                {lvl.advice ? ` · ${lvl.advice}` : ""}
              </div>
            </div>

            <div className="cond-stats">
              <div className="stat-tile"><div className="stat-label">Air temp</div><div className="stat-value">{cond ? cond.air_temp_c.toFixed(0) : "—"}<span className="u">°C</span></div></div>
              <div className="stat-tile"><div className="stat-label">Humidity</div><div className="stat-value">{cond ? cond.rh_pct.toFixed(0) : "—"}<span className="u">%</span></div></div>
              <div className="stat-tile"><div className="stat-label">In direct sun</div><div className="stat-value amber-t" style={{ color: "var(--amber-ink)" }}>{cond ? cond.peak_mrt_c.toFixed(0) : "—"}<span className="u">°C</span></div></div>
              <div className="stat-tile"><div className="stat-label">Sun height</div><div className="stat-value">{cond ? cond.sun_altitude_deg.toFixed(0) : "—"}<span className="u">°</span></div></div>
              <div className="stat-tile">
                <div className="stat-label">Sun track</div>
                <div className="bar thin" style={{ marginTop: 10 }}>
                  <div className="bar-fill amber" style={{ width: `${sunPct}%`, transition: "width 0.6s var(--ease-deep-out)" }} />
                </div>
                <div className="muted" style={{ fontSize: 11.5, marginTop: 6 }}>{cond && cond.is_daytime ? "Above horizon" : "Below horizon"}</div>
              </div>
            </div>
          </div>
        </section>
      </Reveal>

      {/* ---------------- HEADING ---------------- */}
      <Reveal style={{ textAlign: "center", marginBottom: 26 }}>
        <h1 className="h2 dyna-title" style={{ fontSize: 34 }}>Where are you walking?</h1>
        <p className="lead" style={{ maxWidth: 560, margin: "10px auto 0" }}>
          Set a start and a destination below, and we'll show you the fast way and the shady way
          side by side.
        </p>
      </Reveal>

      {/* ---------------- PLANNER ---------------- */}
      <div className="planner-grid">
        <Reveal className="card control-card">
          <div style={{ marginBottom: 16 }}>
            <div className="field-label"><span className="field-dot dot-start" />Start</div>
            <AddressAutocomplete
              label=""
              externalText={startText}
              picking={picking === "start"}
              onSelect={(p) => { setStart(p); setError(null); }}
              onPick={() => setPicking(picking === "start" ? null : "start")}
            />
          </div>

          <div style={{ marginBottom: 18 }}>
            <div className="field-label"><span className="field-dot dot-end" />Destination</div>
            <AddressAutocomplete
              label=""
              externalText={endText}
              picking={picking === "end"}
              onSelect={(p, display) => { setEnd(p); setEndLabel(display?.split(",")[0]); setError(null); }}
              onPick={() => setPicking(picking === "end" ? null : "end")}
            />
          </div>

          <div className="field-label" style={{ marginBottom: 8 }}>When are you heading out?</div>
          <div className="time-row">
            <button className={`chip-btn ${hour === "" ? "on" : ""}`} onClick={() => setHour("")}>
              Now{cond && hour === "" ? ` · ${cond.time_label}` : ""}
            </button>
            <select
              className="hs-select"
              style={{ flex: 1 }}
              value={hour}
              onChange={(e) => setHour(e.target.value === "" ? "" : parseInt(e.target.value))}
            >
              <option value="">Later today…</option>
              {Array.from({ length: 24 }, (_, h) => (
                <option key={h} value={h}>{(h % 12 === 0 ? 12 : h % 12)} {h < 12 ? "AM" : "PM"}</option>
              ))}
            </select>
          </div>

          <label className="toggle-row" style={{ marginBottom: 12 }}>
            <input type="checkbox" checked={viaCooling} onChange={(e) => setViaCooling(e.target.checked)} style={{ marginTop: 3 }} />
            <span>
              <div style={{ fontWeight: 600, color: "var(--ink)", fontSize: 14 }}>Stop somewhere cool</div>
              <div className="muted" style={{ fontSize: 12.5 }}>Adds a route through an air-conditioned spot</div>
            </span>
          </label>

          <label className="check-row" style={{ marginBottom: 18 }}>
            <input type="checkbox" checked={showCooling} onChange={(e) => setShowCooling(e.target.checked)} />
            Show cooling &amp; rest spots
          </label>

          <button className="btn btn-amber btn-block cta-glisten" onClick={doRoute} disabled={loading}>
            {loading ? (<><span className="spin" /> Finding routes…</>) : "Find my routes"}
          </button>

          {error && (
            <div style={{ marginTop: 12, background: "#fef2f2", color: "#b91c1c", border: "1px solid #fecaca", borderRadius: 10, padding: "9px 12px", fontSize: 13 }}>
              {error}
            </div>
          )}
        </Reveal>

        <Reveal delay={80} className="map-shell" style={{ position: "relative" }}>
          <MapView
            start={start}
            end={end}
            picking={picking}
            onPickStart={(p) => { setStart(p); setStartText(coordText(p)); setPicking(null); setError(null); }}
            onPickEnd={(p) => { setEnd(p); setEndText(coordText(p)); setEndLabel(coordText(p)); setPicking(null); setError(null); }}
            fastestGeo={data?.fastest?.geojson}
            heatsafeGeo={data?.heatsafe?.geojson}
            coolingRouteGeo={data?.cooling?.geojson}
            coolingStop={data?.cooling?.stop}
            coolingGeo={coolingGeo}
            showCooling={showCooling}
          />
          <div className="map-legend">
            <span className="legend-item"><span className="legend-swatch" style={{ background: "#e0870b" }} />Fastest</span>
            <span className="legend-item"><span className="legend-swatch" style={{ background: "#1e3a5f" }} />HeatSafe</span>
            {data?.cooling && <span className="legend-item"><span className="legend-swatch" style={{ background: "#0e7490" }} />Via A/C</span>}
          </div>
        </Reveal>
      </div>

      {/* ---------------- RESULTS ---------------- */}
      {data && (
        <div className={data.cooling ? "grid-3" : "grid-2"} style={{ marginTop: 30 }}>
          <RoutePanel kind="fastest" title="Fastest" subtitle="The route you'd normally take" metrics={data?.fastest?.metrics} steps={data?.fastest?.steps} destination={endLabel} />
          <RoutePanel kind="heatsafe" title="HeatSafe" subtitle="A small detour, several degrees cooler" metrics={data?.heatsafe?.metrics} steps={data?.heatsafe?.steps} recommended destination={endLabel} />
          {data?.cooling && (
            <RoutePanel kind="cool" title="Via A/C" subtitle="Breaks the walk with real relief" metrics={data.cooling.metrics} steps={data.cooling.steps} destination={endLabel} />
          )}
        </div>
      )}
    </div>
  );
}
