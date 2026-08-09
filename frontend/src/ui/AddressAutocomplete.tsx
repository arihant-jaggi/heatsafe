import { useEffect, useRef, useState } from "react";
import { geocode } from "../api";

type LatLon = { lat: number; lon: number };

// Accepts "25.7815, -80.1300" (also space- or comma-separated) -> coords.
function parseCoords(s: string): LatLon | null {
  const m = s.trim().match(/^(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const lat = parseFloat(m[1]);
  const lon = parseFloat(m[2]);
  if (!isFinite(lat) || !isFinite(lon)) return null;
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat, lon };
}

export function AddressAutocomplete({
  label,
  placeholder,
  externalText,
  picking,
  onSelect,
  onPick,
}: {
  label: string;
  placeholder?: string;
  externalText?: string; // pushed in from parent (e.g. after a map Pick)
  picking: boolean;
  onSelect: (p: LatLon, display?: string) => void;
  onPick: () => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const boxRef = useRef<HTMLDivElement | null>(null);

  // Sync the field when the parent sets coordinates another way (map pick).
  useEffect(() => {
    if (externalText !== undefined) setQ(externalText);
  }, [externalText]);

  // Close the dropdown on outside click.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function handleChange(v: string) {
    setQ(v);
    if (timer.current) window.clearTimeout(timer.current);

    // Typed coordinates lock in immediately — no Search/Pick needed.
    const coords = parseCoords(v);
    if (coords) {
      setResults([]);
      setOpen(false);
      onSelect(coords, v);
      return;
    }

    if (v.trim().length < 3) {
      setResults([]);
      setOpen(false);
      return;
    }

    // Debounce Nominatim calls by 300ms.
    timer.current = window.setTimeout(async () => {
      setLoading(true);
      try {
        const res = await geocode(v.trim());
        setResults(res.results || []);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }

  function choose(r: any) {
    setQ(r.display_name);
    setResults([]);
    setOpen(false);
    onSelect({ lat: r.lat, lon: r.lon }, r.display_name);
  }

  return (
    <div ref={boxRef} style={{ position: "relative" }}>
      {label && <b>{label}</b>}
      <div style={{ display: "flex", gap: 8 }}>
        <input
          className="hs-input"
          value={q}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={placeholder ?? "Type an address or 25.7815, -80.1300"}
          style={{ flex: 1 }}
        />
        <button className={`chip-btn ${picking ? "on" : ""}`} onClick={onPick}>
          {picking ? "Click map…" : "Map"}
        </button>
      </div>

      {open && (results.length > 0 || loading) && (
        <div
          style={{
            position: "absolute",
            zIndex: 1000,
            top: "100%",
            left: 0,
            right: 0,
            marginTop: 4,
            background: "#fff",
            color: "#0f172a",
            border: "1px solid rgba(15,23,42,0.15)",
            borderRadius: 10,
            boxShadow: "0 12px 30px rgba(0,0,0,0.18)",
            overflow: "hidden",
            maxHeight: 260,
            overflowY: "auto",
          }}
        >
          {loading && (
            <div style={{ padding: "8px 12px", fontSize: 13, opacity: 0.6 }}>Searching…</div>
          )}
          {results.map((r, i) => (
            <div
              key={i}
              onClick={() => choose(r)}
              style={{
                padding: "8px 12px",
                fontSize: 13,
                cursor: "pointer",
                borderTop: i === 0 ? "none" : "1px solid rgba(15,23,42,0.08)",
              }}
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#f1f5f9")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "#fff")}
            >
              {r.display_name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
