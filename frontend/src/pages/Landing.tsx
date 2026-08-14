import { Link } from "react-router-dom";
import { SunHero } from "../ui/SunHero";
import { Reveal, useReveal, useMagnetic, useCountUp } from "../ui/motion";

/* Liquid-fill bar that fills once it scrolls into view. */
function LiquidBar({ pct, tone = "navy", thin = false }: { pct: number; tone?: "amber" | "navy"; thin?: boolean }) {
  const { ref, inView } = useReveal<HTMLDivElement>(0.25);
  return (
    <div ref={ref} className={`bar ${thin ? "thin" : ""}`}>
      <div className={`bar-fill ${tone}`} style={{ width: inView ? `${pct}%` : 0 }} />
    </div>
  );
}

/* Comparison row: label, liquid bar, big temperature that counts up. */
function CompareRow({ label, temp, max, tone }: { label: string; temp: number; max: number; tone: "amber" | "navy" }) {
  const { ref, inView } = useReveal<HTMLDivElement>(0.3);
  const shown = useCountUp(temp, inView, 1400, 1);
  return (
    <div ref={ref} className="compare-row-grid">
      <div style={{ fontWeight: 600, color: "var(--ink)" }}>{label}</div>
      <LiquidBar pct={(temp / max) * 100} tone={tone} />
      <div style={{ textAlign: "right", fontWeight: 700, color: tone === "amber" ? "var(--amber-ink)" : "var(--navy)" }}>
        {shown.toFixed(1)}°
      </div>
    </div>
  );
}

function WalkCard({
  badge, badgeClass, eta, title, desc, temp, tempTone, shade, note, recommended,
}: {
  badge: string; badgeClass: string; eta: string; title: string; desc: string;
  temp: number; tempTone: "amber" | "navy"; shade: number; note: string; recommended?: boolean;
}) {
  const mag = useMagnetic<HTMLDivElement>();
  const { ref: rref, inView } = useReveal<HTMLDivElement>(0.25);
  const shadeShown = useCountUp(shade, inView, 1400, 0);
  return (
    <div ref={rref}>
      <div
        ref={mag.ref}
        onMouseMove={mag.onMouseMove}
        onMouseLeave={mag.onMouseLeave}
        className={`route-card-el magnetic ${recommended ? "recommended" : ""}`}
      >
        {recommended && <div className="rec-tab">Recommended</div>}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className={`route-badge ${badgeClass}`}>{badge}</span>
          <span className="muted" style={{ fontWeight: 600 }}>{eta}</span>
        </div>
        <h3 style={{ margin: "18px 0 8px", fontSize: 21, letterSpacing: "-0.02em", color: "var(--ink)" }}>{title}</h3>
        <p className="lead" style={{ fontSize: 14.5, margin: 0 }}>{desc}</p>
        <div style={{ margin: "20px 0 6px", display: "flex", alignItems: "baseline" }}>
          <span className={`big-temp ${tempTone}`}>{temp.toFixed(1)}</span>
          <span className="big-temp"><span className="u">°C felt on skin</span></span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5, marginTop: 14, marginBottom: 8 }}>
          <span className="muted">In the shade</span>
          <b style={{ color: "var(--navy)" }}>{shadeShown}%</b>
        </div>
        <div className="bar thin">
          <div className="bar-fill navy" style={{ width: inView ? `${shade}%` : 0 }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--line-soft)", fontSize: 13.5 }}>
          <span className="muted">{note}</span>
          <Link to="/app" style={{ color: "var(--navy)", fontWeight: 700, textDecoration: "none" }}>Try it →</Link>
        </div>
      </div>
    </div>
  );
}

function Persona({ title, desc }: { title: string; desc: string }) {
  return (
    <div>
      <div style={{ fontWeight: 700, color: "var(--ink)", marginBottom: 8, fontSize: 17 }}>{title}</div>
      <div className="lead" style={{ fontSize: 14.5 }}>{desc}</div>
    </div>
  );
}

export default function Landing() {
  return (
    <div className="wrap landing-page">
      {/* ---------------- HERO ---------------- */}
      <section className="section" style={{ paddingTop: 64 }}>
        <div className="hero-grid" style={{ display: "grid", gridTemplateColumns: "1fr 0.82fr", gap: 32, alignItems: "center" }}>
          <div>
            <Reveal className="eyebrow">Miami Beach · walking in the heat</Reveal>
            <Reveal delay={60}>
              <h1 className="display" style={{ whiteSpace: "nowrap", fontSize: "clamp(34px, 4.2vw, 56px)" }}>
                <span className="amber-t">The sun side.</span><br />
                <span className="navy-t">The shade side.</span><br />
                <span className="gray-t">Same 15 minutes.</span>
              </h1>
            </Reveal>
            <Reveal delay={130}>
              <p className="lead" style={{ maxWidth: 500, marginTop: 24 }}>
                Two walks that take the same time can differ by up to 20&nbsp;°C of heat on your
                skin. HeatSafe Routes finds the cooler one, using shade, humidity and
                air-conditioned rest stops.
              </p>
            </Reveal>
            <Reveal delay={200}>
              <div style={{ display: "flex", gap: 14, marginTop: 32 }}>
                <Link to="/app" className="btn btn-primary cta-glisten">Plan a walk</Link>
                <Link to="/how" className="btn btn-ghost">How it works</Link>
              </div>
            </Reveal>
          </div>
          <Reveal delay={120} style={{ display: "grid", placeItems: "center" }}>
            <SunHero />
          </Reveal>
        </div>
      </section>

      {/* ---------------- CONDITIONS STRIP ---------------- */}
      <Reveal>
        <section className="card glass-bubble" style={{ padding: "30px 34px", margin: "8px 0 40px" }}>
          <div className="orb orb-a" /><div className="orb orb-b" /><div className="sheen" />
          <div className="landing-cond-grid">
            <div>
              <div className="muted" style={{ fontSize: 13.5, marginBottom: 8 }}>A typical August afternoon</div>
              <div style={{ display: "flex", alignItems: "flex-start" }}>
                <span style={{ fontSize: 68, fontWeight: 800, color: "var(--amber-ink)", letterSpacing: "-0.03em", lineHeight: 1 }}>37</span>
                <span style={{ fontSize: 20, fontWeight: 600, color: "var(--slate-2)", marginTop: 6 }}>°C</span>
              </div>
              <div className="muted" style={{ fontSize: 13.5, marginTop: 10 }}>Feels like 99°F · dangerous for long walks</div>
            </div>
            <div className="landing-cond-stats">
              {[
                ["Air temp", "30°C"],
                ["Humidity", "82%"],
                ["In direct sun", "60°C"],
                ["Pavement", "62 to 68°C"],
              ].map(([l, v]) => (
                <div key={l} className="stat-tile" style={{ borderLeft: "none" }}>
                  <div className="stat-label">{l}</div>
                  <div className="stat-value">{v}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 22 }}>
            <div style={{ height: 8, borderRadius: 999, background: "linear-gradient(90deg, #e0870b, #f0c07a 45%, #9fb2c8 62%, #1e3a5f)" }} />
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12.5 }} className="muted">
              <span>Open pavement, full sun</span>
              <span>Continuous canopy shade</span>
            </div>
          </div>
        </section>
      </Reveal>

      {/* ---------------- THREE WALKS ---------------- */}
      <section className="section">
        <div className="walks-header-grid" style={{ marginBottom: 34 }}>
          <div>
            <Reveal className="eyebrow">Pick your trade-off</Reveal>
            <Reveal delay={60}>
              <h2 className="h2"><span className="navy-t">Same start. Same finish.</span><br /><span style={{ color: "var(--navy)" }}>Three very different walks.</span></h2>
            </Reveal>
          </div>
          <Reveal delay={120}>
            <p className="lead">Every search returns a comparison, never a single answer. You decide what a degree of heat is worth against a minute of walking.</p>
          </Reveal>
        </div>

        <Reveal>
          <div className="card" style={{ padding: "28px 32px", marginBottom: 34 }}>
            <div className="muted" style={{ fontSize: 13.5, marginBottom: 22 }}>How hot each one feels on your skin</div>
            <CompareRow label="Fastest" temp={48.6} max={54} tone="amber" />
            <CompareRow label="HeatSafe" temp={40.8} max={54} tone="navy" />
            <CompareRow label="Via A/C" temp={39.2} max={54} tone="navy" />
          </div>
        </Reveal>

        <div className="grid-3">
          <Reveal delay={0}>
            <WalkCard badge="Fastest" badgeClass="badge-fastest" eta="14 min" title="The route you'd normally take"
              desc="The shortest walking time on the grid, with a clear reading of what it costs you in heat."
              temp={48.6} tempTone="amber" shade={21} note="Quickest, hottest" />
          </Reveal>
          <Reveal delay={130}>
            <WalkCard badge="HeatSafe" badgeClass="badge-heatsafe" eta="15 min" title="A small detour, several degrees cooler"
              desc="Threads canopy, awnings and building shadow. Usually 5 to 6 °C cooler for a few percent more distance."
              temp={40.8} tempTone="navy" shade={74} note="Best all round" recommended />
          </Reveal>
          <Reveal delay={260}>
            <WalkCard badge="Via A/C" badgeClass="badge-cool" eta="18 min" title="Break the walk with real relief"
              desc="Passes through a public air-conditioned building, a library, rec center or transit lounge, with the least added exposure."
              temp={39.2} tempTone="navy" shade={68} note="One cool pause" />
          </Reveal>
        </div>
      </section>

      {/* ---------------- PERSONAS + CTA ---------------- */}
      <section className="section">
        <Reveal>
          <div className="grid-4" style={{ marginBottom: 20 }}>
            <Persona title="Elderly residents" desc="Radiant heat, not air temperature, drives heat strain." />
            <Persona title="Outdoor workers" desc="Many crossings a day, the savings compound." />
            <Persona title="Visitors" desc="Walking further than planned, in the worst hours." />
            <Persona title="Caregivers" desc="Strollers and wheelchairs ride closest to hot pavement." />
          </div>
        </Reveal>

        <div style={{ borderTop: "1px solid var(--line-soft)", paddingTop: 70, textAlign: "center" }}>
          <Reveal>
            <h2 className="h2" style={{ maxWidth: 720, margin: "0 auto" }}>
              <span className="navy-t">Nine seconds now.</span><br />
              <span style={{ color: "var(--navy)" }}>Eleven fewer minutes in the sun.</span>
            </h2>
          </Reveal>
          <Reveal delay={120}>
            <div style={{ marginTop: 34 }}>
              <Link to="/app" className="btn btn-primary cta-glisten" style={{ padding: "17px 40px", fontSize: 16 }}>Open the route planner</Link>
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  );
}
