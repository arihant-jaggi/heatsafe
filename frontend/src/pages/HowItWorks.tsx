import { Link } from "react-router-dom";
import { Reveal } from "../ui/motion";

const steps = [
  ["01", "Read the sky", "Sun altitude and azimuth are computed for the selected hour, then combined with air temperature and relative humidity into a heat index and a peak in-sun radiant temperature."],
  ["02", "Score every segment", "Each pedestrian segment of the Miami Beach street graph carries a structural shade value from tree canopy, awnings and building height, then gains cast-shadow shade depending on how the street sits relative to the sun's azimuth."],
  ["03", "Re-weight the graph", "Fastest routing minimises walking metres. HeatSafe routing minimises exposure-weighted metres: an unshaded metre at solar noon costs several times more than a shaded one."],
  ["04", "Report absorbed heat", "For each route we report distance, ETA at 4 km/h, shade score, mean radiant temperature, and direct sun time, the minutes your body spends absorbing shortwave radiation."],
  ["05", "Insert relief", "With the A/C option on, the router tests every registered cooling station and keeps the one that adds the least exposure while breaking the walk into two shorter thermal loads."],
];

const numbers = [
  ["Mean radiant temperature (MRT)", "The area-weighted temperature of everything radiating at you: asphalt, walls, sky, sun. It is the single number that best predicts heat strain on a walk, and it can sit 15–20 °C above air temperature in direct sun."],
  ["Shade score", "Distance-weighted percentage of the route under canopy or building shadow at the selected hour. It changes through the day even on an identical path."],
  ["Direct sun time", "ETA multiplied by unshaded fraction. A proxy for cumulative solar dose, the quantity that matters for elderly walkers and outdoor workers."],
  ["Heat index", "Apparent temperature from air temperature and humidity. In Miami Beach humidity, it stays punishing long after the air temperature plateaus."],
];

const limits = [
  "Shade is modelled from canopy, street orientation and sun geometry, not measured from live sensors or LiDAR returns.",
  "Coverage is limited to the Miami Beach pedestrian grid. Routes never leave the barrier island.",
  "Cooling station hours vary. Call ahead before relying on one during an extreme heat event.",
  "This tool reduces exposure. It does not make an extreme heat advisory safe to walk in.",
];

export default function HowItWorks() {
  return (
    <div className="wrap section">
      <Reveal className="eyebrow">Methodology</Reveal>
      <Reveal delay={60}>
        <h1 className="display dyna-title" style={{ maxWidth: 900 }}>
          We do not optimise for <span className="amber-t">time</span> we optimise for <span className="navy-t">absorbed heat.</span>
        </h1>
      </Reveal>
      <Reveal delay={130}>
        <p className="lead" style={{ maxWidth: 640, marginTop: 22 }}>
          Two 15-minute walks between the same two points can differ by 15–20 °C of radiant
          load. The difference is shade, and shade is a routable property. Here is exactly how it
          is modelled.
        </p>
      </Reveal>

      <Reveal>
        <div className="card" style={{ padding: "10px 30px", margin: "44px 0" }}>
          {steps.map(([n, title, body], i) => (
            <Reveal
              key={n}
              delay={i * 110}
              className="step-row-grid"
              style={{
                padding: "26px 0", borderBottom: i < steps.length - 1 ? "1px solid var(--line-soft)" : "none",
              }}
            >
              <div style={{ fontSize: 22, fontWeight: 800, color: "var(--amber-ink)" }}>{n}</div>
              <div style={{ fontSize: 17, fontWeight: 700, color: "var(--ink)" }}>{title}</div>
              <div className="lead" style={{ fontSize: 14.5 }}>{body}</div>
            </Reveal>
          ))}
        </div>
      </Reveal>

      <Reveal><h2 className="h2" style={{ fontSize: 28, marginBottom: 20 }}>The four numbers</h2></Reveal>
      <Reveal>
        <div className="card grid-2" style={{ padding: 30, gap: 30, marginBottom: 34 }}>
          {numbers.map(([t, d]) => (
            <div key={t}>
              <div style={{ fontWeight: 700, color: "var(--navy)", marginBottom: 8 }}>{t}</div>
              <div className="lead" style={{ fontSize: 14.5 }}>{d}</div>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal>
        <div className="soft-card" style={{ padding: 30 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 20, color: "var(--ink)" }}>Limits worth knowing</h3>
          <ul style={{ margin: 0, paddingLeft: 4, listStyle: "none" }}>
            {limits.map((l) => (
              <li key={l} className="lead" style={{ fontSize: 14.5, marginBottom: 12, display: "flex", gap: 10 }}>
                <span style={{ color: "var(--amber)" }}>·</span>{l}
              </li>
            ))}
          </ul>
        </div>
      </Reveal>

      <div style={{ marginTop: 40 }}>
        <Link to="/app" className="btn btn-primary cta-glisten">Open the Route Planner</Link>
      </div>
    </div>
  );
}
