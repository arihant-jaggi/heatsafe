export type LatLon = { lat: number; lon: number };

export async function geocode(q: string) {
  const r = await fetch(`http://localhost:8000/geocode?q=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error("geocode failed");
  return r.json();
}

export type RouteOpts = {
  hour?: number | null;      // hour of day 0-23; null => current local hour
  via_cooling?: boolean;     // also return a route through an A/C cooling stop
};

// alpha/beta (time vs heat-penalty weights) are hardcoded server-side.
export async function route(start: LatLon, end: LatLon, opts: RouteOpts = {}) {
  const { hour = null, via_cooling = false } = opts;
  const r = await fetch(`http://localhost:8000/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, end, hour, via_cooling })
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function cooling() {
  const r = await fetch(`http://localhost:8000/cooling`);
  if (!r.ok) throw new Error("cooling failed");
  return r.json();
}

export async function conditions(hour: number | null = null) {
  const qs = hour === null ? "" : `?hour=${hour}`;
  const r = await fetch(`http://localhost:8000/conditions${qs}`);
  if (!r.ok) throw new Error("conditions failed");
  return r.json();
}
