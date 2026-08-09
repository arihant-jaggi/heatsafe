import { Link } from "react-router-dom";
import { Reveal } from "../ui/motion";

const personas = [
  ["Elderly residents", "Reduced thermoregulation and medications that blunt sweating make radiant load, not air temperature, the real hazard on an errand walk."],
  ["Outdoor workers", "Landscapers, delivery riders and hotel staff cross the island many times a day. Small per-trip savings compound into whole degrees of daily strain."],
  ["Visitors", "Tourists walk further than they plan, in the hottest hours, without knowing which streets have canopy and which are bare asphalt."],
  ["Caregivers & parents", "Strollers and wheelchairs sit lower, closer to re-radiating pavement, where surface temperatures run hottest."],
];

export default function About() {
  return (
    <div className="wrap section">
      <Reveal>
        <h1 className="display dyna-title" style={{ maxWidth: 820 }}>
          <span className="navy-t">Shade is infrastructure.</span><br />
          <span style={{ color: "var(--navy)" }}>It should be routable.</span>
        </h1>
      </Reveal>
      <Reveal delay={80}>
        <p className="lead" style={{ marginTop: 20 }}>HeatSafe Routes was created by <b style={{ color: "var(--ink)" }}>Arihant Jaggi</b>.</p>
      </Reveal>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: 40, marginTop: 40, alignItems: "start" }}>
        <Reveal>
          <div className="stack" style={{ gap: 20 }}>
            <p className="lead">
              HeatSafe Routes started from a simple, uncomfortable observation: every mapping tool
              on the island optimises for the one variable that no longer matters most. On a barrier
              island where the heat index sits near 37 °C for months, saving ninety seconds is
              worthless if it costs you eleven extra minutes in full sun.
            </p>
            <p className="lead">
              Heat is not distributed evenly. It pools on wide, treeless corridors and evaporates
              under a banyan canopy. Two neighbours on the same block can experience radically
              different walks depending on which street they take, and the people least able to
              absorb that difference are the ones most likely to be walking.
            </p>
            <p className="lead">
              So we built a router that treats an unshaded metre at solar noon as what it actually
              is: expensive. It will happily spend a 2–5% detour to buy back five or six degrees of
              mean radiant temperature, and it will route you through an air-conditioned public
              building when the walk is long enough to warrant a reset.
            </p>
            <blockquote style={{ margin: 0, padding: "4px 0 4px 20px", borderLeft: "3px solid var(--amber)", color: "var(--slate)", fontSize: 16, lineHeight: 1.55 }}>
              Our goal is boring and specific: fewer heat-related emergency calls on this island,
              because a walk that used to be dangerous is now merely warm.
            </blockquote>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <div className="card" style={{ padding: "8px 24px" }}>
            {personas.map(([t, d], i) => (
              <div key={t} style={{ padding: "20px 0", borderBottom: i < personas.length - 1 ? "1px solid var(--line-soft)" : "none" }}>
                <div style={{ fontWeight: 700, color: "var(--ink)", marginBottom: 6 }}>{t}</div>
                <div className="lead" style={{ fontSize: 14 }}>{d}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </div>

      <Reveal>
        <div className="card grid-3" style={{ padding: 30, gap: 30, marginTop: 40 }}>
          {[
            ["Free, always", "No account, no tracking, no paywall on a safety tool."],
            ["Transparent model", "Every number we show is explained on the methodology page."],
            ["Built for glare", "High-contrast type, tested for legibility in direct sunlight."],
          ].map(([t, d]) => (
            <div key={t}>
              <div style={{ fontWeight: 700, color: "var(--ink)", marginBottom: 8 }}>{t}</div>
              <div className="lead" style={{ fontSize: 14.5 }}>{d}</div>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal>
        <div className="card" style={{ padding: "26px 30px", marginTop: 26, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 18 }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 20, color: "var(--ink)" }}>Plan a walk before you take it.</div>
            <div className="lead" style={{ fontSize: 14.5 }}>Compare a fastest route against a HeatSafe route in about nine seconds.</div>
          </div>
          <Link to="/app" className="btn btn-primary cta-glisten">Open the Route Planner</Link>
        </div>
      </Reveal>
    </div>
  );
}
