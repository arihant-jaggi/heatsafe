from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
import networkx as nx
import geopandas as gpd
import osmnx as ox
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware


from .settings import (
    NBHD_PATH, TREES_PATH, GRAPH_PATH, BUILDINGS_PATH,
    DEFAULT_ALPHA, DEFAULT_BETA, LOCAL_TZ,
    COOLING_TAGS, COOLING_MAX_DETOUR_RATIO, COOLING_MAX_CANDIDATES,
)
from .cache import geocode_cache, route_cache
from .weather import get_conditions, Conditions
from .shadows import prepare_shade_inputs, build_shade_index, sun_position
from .routing import (
    _load_polygon, graph_to_gdfs,
    precompute_edge_samples, score_edges_from_samples, attach_edge_weights_timeaware,
    shortest_path, route_geojson_and_metrics, route_via_node, best_cooling_via,
    mrt_celsius,
)
from .turns import route_steps

app = FastAPI(title="HeatSafe Routes API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


STATE: Dict[str, Any] = {}

class LatLon(BaseModel):
    lat: float
    lon: float

class RouteRequest(BaseModel):
    start: LatLon
    end: LatLon
    alpha: float = DEFAULT_ALPHA
    beta: float = DEFAULT_BETA
    # Hour of day (0-23) to route for; drives sun position + weather.
    # Defaults to the current local hour when omitted.
    hour: Optional[int] = None
    # Also compute a route that detours through an air-conditioned cooling stop.
    via_cooling: bool = False


def _load_buildings() -> gpd.GeoDataFrame:
    """Building footprints (with height tags), loaded from the committed file.

    Never fetched at runtime: Render blocks outbound connections during the
    startup sequence, so the graph/buildings must already be on disk (generated
    locally via ``scripts/preprocess.py`` and committed to the repo).
    """
    if not BUILDINGS_PATH.exists():
        raise RuntimeError(
            f"Missing {BUILDINGS_PATH}. Run `python scripts/preprocess.py` locally "
            "and commit the generated file — buildings are never fetched at runtime."
        )
    return gpd.read_file(BUILDINGS_PATH).to_crs("EPSG:4326")


def _init_once():
    if STATE.get("ready"):
        return

    polygon = _load_polygon(str(NBHD_PATH))
    STATE["polygon"] = polygon
    centroid = polygon.centroid
    STATE["lat"], STATE["lon"] = float(centroid.y), float(centroid.x)
    STATE["tz"] = ZoneInfo(LOCAL_TZ)

    # Load the walking graph from disk only. Never fetched at runtime: Render
    # blocks outbound connections during startup, so a missing graph must fail
    # loudly rather than silently trying (and hanging on) an Overpass call.
    if not GRAPH_PATH.exists():
        raise RuntimeError(
            f"Missing {GRAPH_PATH}. Run `python scripts/preprocess.py` locally "
            "and commit the generated file — the graph is never fetched at runtime."
        )
    G = ox.load_graphml(GRAPH_PATH)

    # Static layers: trees (canopy) + buildings (for dynamic shadows).
    if TREES_PATH.exists():
        trees = gpd.read_file(TREES_PATH).to_crs("EPSG:4326")
    else:
        trees = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    buildings = _load_buildings()

    nodes, edges = graph_to_gdfs(G)

    # Precompute the static, reusable geometry once so per-hour scoring is cheap:
    # projected building/tree shadows-inputs, and projected per-edge sample points.
    STATE["shade_inputs"] = prepare_shade_inputs(buildings, trees)
    STATE["edge_samples"] = precompute_edge_samples(edges)

    STATE["G"] = G
    STATE["trees_loaded"] = len(trees)
    STATE["buildings_loaded"] = len(buildings)
    STATE["scored_cache"] = {}   # keyed by (date_str, hour) -> (edges_scored, conditions, solar)
    STATE["ready"] = True


def _resolve_when(hour: Optional[int]) -> datetime:
    now = datetime.now(STATE["tz"])
    if hour is None:
        return now.replace(minute=0, second=0, microsecond=0)
    hour = max(0, min(23, int(hour)))
    return now.replace(hour=hour, minute=0, second=0, microsecond=0)


def _scored_for(when: datetime) -> Tuple[gpd.GeoDataFrame, Conditions, Any]:
    """Time-aware edge scores + weather for a given instant, cached per hour."""
    key = (when.strftime("%Y-%m-%d"), when.hour)
    cache = STATE["scored_cache"]
    if key in cache:
        return cache[key]

    cond = get_conditions(when, STATE["lat"], STATE["lon"])
    shade = build_shade_index(STATE["shade_inputs"], when, STATE["lat"], STATE["lon"])
    edges_scored = score_edges_from_samples(STATE["edge_samples"], shade, cond)
    result = (edges_scored, cond, shade.solar)
    cache[key] = result
    return result


@app.on_event("startup")
def on_startup():
    _init_once()

@app.get("/health")
def health():
    return {
        "ok": True,
        "trees_loaded": STATE.get("trees_loaded", 0),
        "buildings_loaded": STATE.get("buildings_loaded", 0),
    }

def _photon_display_name(props: Dict[str, Any]) -> str:
    """Build a readable label from Photon feature properties (deduped)."""
    house = props.get("housenumber")
    street = props.get("street")
    first = props.get("name")
    if not first:
        first = f"{house} {street}".strip() if (house and street) else (street or "")
    parts = [first, street if first != street else None,
             props.get("city") or props.get("county"),
             props.get("state"), props.get("postcode"), props.get("country")]
    seen, out = set(), []
    for p in parts:
        p = (str(p).strip() if p is not None else "")
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return ", ".join(out)


@app.get("/geocode")
def geocode(q: str):
    q = q.strip()
    if not q:
        return {"results": []}
    cached = geocode_cache.get(q)
    if cached:
        return cached

    # Photon (Komoot) — free, no key, OSM-based, with fuzzy/typo tolerance.
    # lat/lon bias ranks results toward Miami Beach; that bias alone is weak
    # (a typo'd generic street can match anywhere on earth), so bbox constrains
    # results to the Miami Beach area. GeoJSON coordinates are [lon, lat].
    url = "https://photon.komoot.io/api/"
    params = {
        "q": q,
        "lat": 25.7907,
        "lon": -80.1300,
        "bbox": "-80.20,25.74,-80.11,25.87",  # minLon,minLat,maxLon,maxLat
        "limit": 5,
    }
    headers = {"User-Agent": "HeatSafeRoutes-DiamondMVP/0.1"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    features = r.json().get("features", []) or []

    results = []
    for f in features:
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        results.append({
            "display_name": _photon_display_name(f.get("properties") or {}),
            "lat": lat,
            "lon": lon,
        })

    out = {"results": results}
    geocode_cache.set(q, out)
    return out


def _clean(v: Any) -> Optional[str]:
    """Return a non-empty string, or None for NaN / None / blank cells.

    OSM feature columns are sparse, so a missing tag comes back as float NaN.
    ``NaN or x`` keeps the NaN (it's truthy), which is how blank labels leaked
    through before — hence this explicit guard.
    """
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    s = str(v).strip()
    return s or None


def _cooling_gdf() -> gpd.GeoDataFrame:
    """Air-conditioned cooling stops (+ shady parks) inside the neighborhood."""
    if "cooling_gdf" in STATE:
        return STATE["cooling_gdf"]
    polygon = STATE["polygon"]
    try:
        gdf = ox.features_from_polygon(polygon, COOLING_TAGS)
    except Exception:
        gdf = None
    if gdf is None or len(gdf) == 0:
        gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    else:
        gdf = gdf.reset_index()
        gdf = gdf[gdf.geometry.notna()].to_crs("EPSG:4326")
    STATE["cooling_gdf"] = gdf
    return gdf


def _cooling_nodes() -> List[Dict[str, Any]]:
    """Cooling stops snapped to graph nodes: [{node, name, lat, lon}, ...].

    Snaps all POIs in a single vectorized nearest_nodes call — snapping them one
    at a time rebuilt the graph's KD-tree per POI (tens of seconds on the full
    island).
    """
    if "cooling_nodes" in STATE:
        return STATE["cooling_nodes"]
    gdf = _cooling_gdf()
    G = STATE["G"]
    if gdf is None or len(gdf) == 0:
        STATE["cooling_nodes"] = []
        return []

    xs, ys, names = [], [], []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        pt = geom if geom.geom_type == "Point" else geom.representative_point()
        xs.append(float(pt.x))
        ys.append(float(pt.y))
        names.append(_clean(row.get("name")) or _clean(row.get("amenity"))
                     or _clean(row.get("shop")) or _clean(row.get("leisure")) or "Cooling Stop")

    out: List[Dict[str, Any]] = []
    if xs:
        snapped = ox.distance.nearest_nodes(G, X=xs, Y=ys)  # one KD-tree, vectorized
        seen: set = set()
        for node, x, y, name in zip(snapped, xs, ys, names):
            node = int(node)
            if node in seen:
                continue
            seen.add(node)
            out.append({"node": node, "name": name, "lat": y, "lon": x})
    STATE["cooling_nodes"] = out
    return out


@app.get("/cooling")
def cooling():
    """OSM-based air-conditioned cooling stops + rest POIs for map display."""
    gdf = _cooling_gdf()
    if gdf is None or len(gdf) == 0:
        return {"type": "FeatureCollection", "features": []}

    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.geom_type not in (
            "Point", "Polygon", "MultiPolygon", "LineString", "MultiLineString"
        ):
            continue
        name = (_clean(row.get("name")) or _clean(row.get("amenity"))
                or _clean(row.get("shop")) or _clean(row.get("leisure")) or "Cooling Stop")
        kind = (_clean(row.get("amenity")) or _clean(row.get("shop"))
                or _clean(row.get("leisure")) or "Cooling Stop")
        features.append({
            "type": "Feature",
            "properties": {"name": name, "kind": kind},
            "geometry": json.loads(gpd.GeoSeries([geom], crs="EPSG:4326").to_json())["features"][0]["geometry"]
        })

    return {"type": "FeatureCollection", "features": features}


def _time_label(hour: int) -> str:
    """12-hour clock label, e.g. 7 -> '7 AM', 14 -> '2 PM' (Windows-safe)."""
    suffix = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12} {suffix}"


def _conditions_block(when: datetime, cond: Conditions, solar) -> Dict[str, Any]:
    return {
        "hour": when.hour,
        "time_label": _time_label(when.hour),
        "iso": when.isoformat(),
        "air_temp_c": round(cond.air_temp_c, 1),
        "rh_pct": round(cond.rh_pct, 0),
        "heat_index_c": round(cond.heat_index_c, 1),
        "heat_index_f": round(cond.heat_index_f, 1),
        "direct_rad": round(cond.direct_rad, 0),
        "diffuse_rad": round(cond.diffuse_rad, 0),
        "sun_altitude_deg": round(solar.altitude_deg, 1),
        "sun_azimuth_deg": round(solar.azimuth_deg, 1),
        "is_daytime": solar.is_daytime,
        "weather_source": cond.source,
        # Peak radiant temperature a pedestrian would feel in full sun right now
        # (shade_frac = 0). Lets the banner show MRT without a specific route.
        "peak_mrt_c": round(mrt_celsius(0.0, cond), 1),
    }


@app.get("/conditions")
def conditions_now(hour: Optional[int] = None):
    """Heat context (index, peak MRT, sun) for the area — no route required.

    Backs the always-on conditions alert so users see the heat picture before
    computing anything. Cheap: one weather lookup + a sun-position calc.
    """
    when = _resolve_when(hour)
    cond = get_conditions(when, STATE["lat"], STATE["lon"])
    solar = sun_position(when, STATE["lat"], STATE["lon"])
    return _conditions_block(when, cond, solar)


@app.post("/route")
def route(req: RouteRequest):
    G = STATE["G"]
    when = _resolve_when(req.hour)

    cache_key = (
        round(req.start.lat, 6), round(req.start.lon, 6),
        round(req.end.lat, 6), round(req.end.lon, 6),
        round(req.alpha, 3), round(req.beta, 3),
        when.strftime("%Y-%m-%d"), when.hour, bool(req.via_cooling),
    )
    cached = route_cache.get(cache_key)
    if cached:
        return cached

    # Time-aware per-edge scores (shadows + MRT) for this hour, then apply the
    # request's alpha/beta to derive routing weights on the shared graph.
    edges_scored, cond, solar = _scored_for(when)
    attach_edge_weights_timeaware(G, edges_scored, req.alpha, req.beta)

    try:
        r_fast = shortest_path(G, req.start.lat, req.start.lon, req.end.lat, req.end.lon, weight="w_fast")
        r_heat = shortest_path(G, req.start.lat, req.start.lon, req.end.lat, req.end.lon, weight="w_heat")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Routing failed: {e}")

    gj_fast, m_fast = route_geojson_and_metrics(G, r_fast)
    gj_heat, m_heat = route_geojson_and_metrics(G, r_heat)

    conditions = _conditions_block(when, cond, solar)
    # Include the shared heat context on each route so the panel can show it.
    for m in (m_fast, m_heat):
        m["heat_index_c"] = conditions["heat_index_c"]
        m["heat_index_f"] = conditions["heat_index_f"]
        m["time_label"] = conditions["time_label"]

    out: Dict[str, Any] = {
        "conditions": conditions,
        "fastest": {"geojson": gj_fast, "steps": route_steps(G, r_fast), "metrics": m_fast},
        "heatsafe": {"geojson": gj_heat, "steps": route_steps(G, r_heat), "metrics": m_heat},
    }

    if req.via_cooling:
        cooling_route = _compute_cooling_route(G, req, conditions)
        if cooling_route is not None:
            out["cooling"] = cooling_route

    route_cache.set(cache_key, out)
    return out


def _compute_cooling_route(G, req: RouteRequest, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Heat-aware route that detours through the best air-conditioned stop."""
    candidates = _cooling_nodes()
    if not candidates:
        return None
    try:
        s = ox.distance.nearest_nodes(G, X=req.start.lon, Y=req.start.lat)
        t = ox.distance.nearest_nodes(G, X=req.end.lon, Y=req.end.lat)
        direct_cost = nx.shortest_path_length(G, s, t, weight="w_heat")
    except Exception:
        return None

    nodes = [c["node"] for c in candidates[:COOLING_MAX_CANDIDATES]]
    via_node, _ = best_cooling_via(
        G, req.start.lat, req.start.lon, req.end.lat, req.end.lon,
        nodes, "w_heat", direct_cost, COOLING_MAX_DETOUR_RATIO,
    )
    if via_node is None:
        return None

    try:
        r_cool = route_via_node(G, req.start.lat, req.start.lon, req.end.lat, req.end.lon, via_node, "w_heat")
    except Exception:
        return None

    gj_cool, m_cool = route_geojson_and_metrics(G, r_cool)
    stop = next((c for c in candidates if c["node"] == via_node), None)
    m_cool["heat_index_c"] = conditions["heat_index_c"]
    m_cool["heat_index_f"] = conditions["heat_index_f"]
    m_cool["time_label"] = conditions["time_label"]
    m_cool["cooling_stop"] = stop["name"] if stop else "Cooling stop"
    return {
        "geojson": gj_cool,
        "steps": route_steps(G, r_cool),
        "metrics": m_cool,
        "stop": stop,
    }
