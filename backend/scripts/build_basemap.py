"""
Build the self-hosted basemap layers the frontend draws instead of third-party
map tiles (CARTO basemaps now require an API key).

Reads the same OSM-derived data the router uses and writes compact GeoJSON to
frontend/public/basemap/:
  streets.json    walk-network edges, deduplicated, classed major/minor/foot
  buildings.json  building footprints, simplified
  trees.json      street-tree points

Stdlib only. Run from the repo root:  python backend/scripts/build_basemap.py
"""
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"
OUT = ROOT / "frontend" / "public" / "basemap"

MAJOR = {"trunk", "primary", "secondary", "primary_link", "secondary_link", "trunk_link"}
MINOR = {"tertiary", "tertiary_link", "residential", "unclassified", "living_street", "service"}
NS = "{http://graphml.graphdrawing.org/xmlns}"


def rnd(c):
    return [round(c[0], 5), round(c[1], 5)]


def simplify(pts, tol):
    """Douglas-Peucker on lon/lat pairs (tol in degrees)."""
    if len(pts) < 3:
        return pts

    def dist(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = dist(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplify(pts[: idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [pts[0], pts[-1]]


def build_streets():
    tree = ET.parse(DATA / "graph.graphml")
    keys = {k.get("id"): k.get("attr.name") for k in tree.iter(NS + "key")}
    graph = tree.getroot().find(NS + "graph")
    nodes = {}
    for n in graph.iter(NS + "node"):
        d = {keys[x.get("key")]: x.text for x in n.iter(NS + "data")}
        nodes[n.get("id")] = (float(d["x"]), float(d["y"]))

    seen = set()
    feats = {"major": [], "minor": [], "foot": []}
    for e in graph.iter(NS + "edge"):
        u, v = e.get("source"), e.get("target")
        pair = tuple(sorted((u, v)))
        d = {keys[x.get("key")]: x.text for x in e.iter(NS + "data")}
        geom = d.get("geometry")
        sig = (pair, geom and len(geom))
        if sig in seen:
            continue
        seen.add(sig)
        hw = (d.get("highway") or "").strip("[]'").split("'")[0]
        cls = "major" if hw in MAJOR else "minor" if hw in MINOR else "foot"
        if geom:
            pts = [tuple(map(float, p.split())) for p in re.findall(r"-?[\d.]+ -?[\d.]+", geom)]
        else:
            pts = [nodes[u], nodes[v]]
        pts = simplify(pts, 0.00002)
        feats[cls].append([rnd(p) for p in pts])

    out = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"c": cls}, "geometry": {"type": "MultiLineString", "coordinates": lines}}
            for cls, lines in feats.items()
        ],
    }
    return out, {k: len(v) for k, v in feats.items()}


def build_buildings():
    src = json.loads((DATA / "buildings.geojson").read_text())
    polys = []
    for f in src["features"]:
        g = f["geometry"]
        rings = g["coordinates"] if g["type"] == "Polygon" else [r for p in g["coordinates"] for r in p]
        outer = simplify([tuple(c) for c in rings[0]], 0.000015)
        if len(outer) >= 4:
            polys.append([[rnd(c) for c in outer]])
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": polys}}]}, len(polys)


def build_trees():
    src = json.loads((DATA / "trees.geojson").read_text())
    pts = [rnd(f["geometry"]["coordinates"]) for f in src["features"] if f.get("geometry")]
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "MultiPoint", "coordinates": pts}}]}, len(pts)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("streets", build_streets), ("buildings", build_buildings), ("trees", build_trees)]:
        data, stats = fn()
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(data, separators=(",", ":")))
        print(f"{name}: {stats} -> {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
