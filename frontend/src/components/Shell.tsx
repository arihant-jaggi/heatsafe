import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/app", label: "Route Planner" },
  { to: "/how", label: "How it works" },
  { to: "/about", label: "About" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Close the mobile menu whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="page">
      {/* animated background haze */}
      <div className="haze" aria-hidden="true">
        <div className="blob blob-a" />
        <div className="blob blob-b" />
        <div className="blob blob-c" />
      </div>

      <header className="nav">
        <div className="nav-inner">
          <Link to="/" className="brand">
            <img src="/logo.svg" alt="HeatSafe" className="brand-logo" />
            <span className="stack">
              <span className="brand-name">HeatSafe <b>Routes</b></span>
              <span className="brand-sub">Miami Beach</span>
            </span>
          </Link>

          <nav className={`nav-links ${menuOpen ? "mobile-open" : ""}`}>
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end as any}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <button
            className={`hamburger-btn ${menuOpen ? "open" : ""}`}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span /><span /><span />
          </button>
        </div>
      </header>

      <main>{children}</main>

      <footer className="footer">
        <div className="wrap" style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <span>HeatSafe Routes — real-time shade, humidity &amp; cooling stations for Miami Beach.</span>
          <span className="muted">Reduces exposure. It does not make an extreme-heat advisory safe to walk in.</span>
        </div>
      </footer>
    </div>
  );
}
