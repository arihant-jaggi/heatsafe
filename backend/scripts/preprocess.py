"""Pre-fetch the network-heavy assets so the first API request is fast.

Downloads (and caches to disk) the walking graph, building footprints, and
cooling-station POIs for the FULL Miami Beach barrier island. All three are
overwritten every run so a boundary change (see settings.NBHD_PATH /
ISLAND_BBOX) takes effect. Edge shade/MRT scoring is time-of-day dependent, so
it is computed lazily per hour at request time rather than baked in here.

None of these three are ever fetched at runtime by the API (see app/main.py) —
Render blocks outbound connections during the startup sequence, so the graph,
buildings, and cooling POIs must already be on disk and committed to the repo.
"""
import time
import osmnx as ox

from app.settings import (
    NBHD_PATH, TREES_PATH, GRAPH_PATH, BUILDINGS_PATH, COOLING_POIS_PATH,
    COOLING_TAGS,
)
from app.routing import _load_polygon, fetch_walk_graph, graph_to_gdfs


def main():
    poly = _load_polygon(str(NBHD_PATH))
    minx, miny, maxx, maxy = poly.bounds
    print(f"Boundary: lon {minx}..{maxx}  lat {miny}..{maxy}")

    t0 = time.time()
    print("Downloading walking graph for the full Miami Beach island (this can take a few minutes)…")
    G = fetch_walk_graph(poly)
    nodes, edges = graph_to_gdfs(G)
    print(f"Graph: {len(nodes)} nodes / {len(edges)} edges  ({time.time()-t0:.0f}s)")
    ox.save_graphml(G, GRAPH_PATH)
    print(f"Saved {GRAPH_PATH}")

    t1 = time.time()
    print("Downloading building footprints (with heights) for the full island…")
    try:
        b = ox.features_from_polygon(poly, {"building": True})
        b = b[b.geometry.notna()]
        b = b[b.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs("EPSG:4326")
        keep = [c for c in ["height", "building:levels", "name", "geometry"] if c in b.columns]
        b = b.reset_index()[keep] if keep else b.reset_index()
        b.to_file(BUILDINGS_PATH, driver="GeoJSON")
        print(f"Saved {BUILDINGS_PATH} with {len(b)} buildings  ({time.time()-t1:.0f}s)")
    except Exception as e:
        print(f"Building fetch failed ({e}); the app will fall back to trees only.")

    t2 = time.time()
    print("Downloading cooling-station POIs (pharmacies, libraries, malls, cafes, …) for the full island…")
    try:
        c = ox.features_from_polygon(poly, COOLING_TAGS)
        c = c.reset_index()
        c = c[c.geometry.notna()].to_crs("EPSG:4326")
        keep = [col for col in ["name", "amenity", "shop", "leisure", "geometry"] if col in c.columns]
        c = c[keep] if keep else c
        c.to_file(COOLING_POIS_PATH, driver="GeoJSON")
        print(f"Saved {COOLING_POIS_PATH} with {len(c)} cooling POIs  ({time.time()-t2:.0f}s)")
    except Exception as e:
        print(f"Cooling POI fetch failed ({e}); /cooling will return no results until re-run.")

    print(f"Trees present: {TREES_PATH.exists()} (unchanged — covers South/Mid Beach only)")
    print(f"Done in {time.time()-t0:.0f}s. Start the API with:  uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
