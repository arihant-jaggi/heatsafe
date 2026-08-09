"""Pre-fetch the network-heavy assets so the first API request is fast.

Downloads (and caches to disk) the walking graph and building footprints for the
FULL Miami Beach barrier island. Both are overwritten every run so a boundary
change (see settings.NBHD_PATH / ISLAND_BBOX) takes effect. Edge shade/MRT
scoring is time-of-day dependent, so it is computed lazily per hour at request
time rather than baked in here.
"""
import time
import osmnx as ox

from app.settings import NBHD_PATH, TREES_PATH, GRAPH_PATH, BUILDINGS_PATH
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

    print(f"Trees present: {TREES_PATH.exists()} (unchanged — covers South/Mid Beach only)")
    print(f"Done in {time.time()-t0:.0f}s. Start the API with:  uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
