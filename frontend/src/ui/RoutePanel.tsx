import { useState } from "react";
import { useMagnetic, useReveal, useCountUp } from "./motion";

const KIND: Record<string, { badge: string; tone: "amber" | "navy" }> = {
  fastest: { badge: "badge-fastest", tone: "amber" },
  heatsafe: { badge: "badge-heatsafe", tone: "navy" },
  cool: { badge: "badge-cool", tone: "navy" },
};

export function RoutePanel({
  kind = "heatsafe", title, subtitle, metrics, steps, recommended, destination,
}: {
  kind?: "fastest" | "heatsafe" | "cool";
  title: string;
  subtitle?: string;
  metrics: any;
  steps?: any[];
  recommended?: boolean;
  destination?: string;
}) {
  const mag = useMagnetic<HTMLDivElement>();
  const { ref, inView } = useReveal<HTMLDivElement>(0.2);
  const [openSteps, setOpenSteps] = useState(false);
  const shade = Math.round(metrics?.shade_score_pct ?? 0);
  const shadeShown = useCountUp(shade, inView, 1400, 0);
  const mrtShown = useCountUp(metrics?.mrt_c ?? 0, inView, 1400, 1);
  if (!metrics) return null;

  const meta = KIND[kind];

  return (
    <div ref={ref}>
      <div
        ref={mag.ref}
        onMouseMove={mag.onMouseMove}
        onMouseLeave={mag.onMouseLeave}
        className={`route-card-el magnetic ${recommended ? "recommended" : ""}`}
      >
        {recommended && <div className="rec-tab">Recommended</div>}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className={`route-badge ${meta.badge}`}>{title}</span>
          <span className="muted" style={{ fontWeight: 600 }}>{metrics.eta_min.toFixed(0)} min</span>
        </div>

        {subtitle && <h3 style={{ margin: "16px 0 4px", fontSize: 19, letterSpacing: "-0.02em", color: "var(--ink)" }}>{subtitle}</h3>}
        {metrics.cooling_stop && (
          <div style={{ fontSize: 13, color: "var(--navy)", fontWeight: 600, marginBottom: 6 }}>❄️ via {metrics.cooling_stop}</div>
        )}

        <div style={{ margin: "16px 0 6px", display: "flex", alignItems: "baseline" }}>
          <span className={`big-temp ${meta.tone}`}>{mrtShown.toFixed(1)}</span>
          <span className="big-temp"><span className="u">°C felt on skin</span></span>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5, marginTop: 14, marginBottom: 8 }}>
          <span className="muted">In the shade</span>
          <b style={{ color: "var(--navy)" }}>{shadeShown}%</b>
        </div>
        <div className="bar thin">
          <div className="bar-fill navy" style={{ width: inView ? `${shade}%` : 0 }} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 18, fontSize: 12.5 }}>
          <div><div className="muted">Distance</div><b style={{ color: "var(--ink)" }}>{metrics.distance_km.toFixed(2)} km</b></div>
          <div><div className="muted">Direct sun</div><b style={{ color: "var(--ink)" }}>{metrics.sun_min_proxy.toFixed(0)} min</b></div>
          <div><div className="muted">Heat index</div><b style={{ color: "var(--ink)" }}>{metrics.heat_index_c?.toFixed(0)}°C</b></div>
        </div>

        {steps && steps.length > 0 && (
          <div style={{ marginTop: 16, borderTop: "1px solid var(--line-soft)", paddingTop: 4 }}>
            <button className="details-head" onClick={() => setOpenSteps((o) => !o)}>
              <span>Step-by-step directions</span>
              <span className="details-sign">{openSteps ? "−" : "+"}</span>
            </button>
            {openSteps && (
              <div className="step-list">
                {steps.map((s: any, i: number) => (
                  <div className="step-row" key={i}>
                    <span className="step-num">{i + 1}</span>
                    <span className="step-text">
                      {s.instruction}
                      {s.shade_pct != null && <span className="step-shade">, {Math.round(s.shade_pct)}% shaded</span>}
                    </span>
                    <span className="step-dist">{Math.round(s.distance_m)} m</span>
                  </div>
                ))}
                <div className="step-row arrive">
                  <span className="step-num">{steps.length + 1}</span>
                  <span className="step-text">Arrive at {destination || "your destination"}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
