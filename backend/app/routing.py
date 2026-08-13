from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, LineString, Point, mapping
from shapely.ops import transform
from pyproj import Transformer

import osmnx as ox

from .settings import (
    PROJECT_CRS, WALK_SPEED_MPS, SAMPLE_STEP_M,
    DEFAULT_CANOPY_RADIUS_M,
    STEFAN_BOLTZMANN, MRT_EMISSIVITY, MRT_SW_ABSORPTION,
    MRT_PROJECTED_AREA_FACTOR, GROUND_ALBEDO, MRT_REF_EXCESS_C,
    SHADE_SHORTWAVE_BLOCK,
)
from .weather import Conditions
from .shadows import ShadeGeometry

@dataclass
class RouteResult:
    geojson: Dict[str, Any]
    steps: List[Dict[str, Any]]
    metrics: Dict[str, Any]

def _load_polygon(nbhd_geojson_path: str) -> Any:
    with open(nbhd_geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)
    geom = shape(gj["features"][0]["geometry"])
    return geom

def _project_transformers():
    to_proj = Transformer.from_crs("EPSG:4326", PROJECT_CRS, always_xy=True).transform
    to_wgs = Transformer.from_crs(PROJECT_CRS, "EPSG:4326", always_xy=True).transform
    return to_proj, to_wgs

def fetch_walk_graph(polygon_wgs84) -> nx.MultiDiGraph:
    # walking network
    G = ox.graph_from_polygon(polygon_wgs84, network_type="walk", simplify=True)
    G = ox.distance.add_edge_lengths(G)
    return G

def graph_to_gdfs(G: nx.MultiDiGraph):
    nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
    return nodes, edges

def _edge_samples_projected(line_proj: LineString, step_m: float) -> List[Point]:
    length = line_proj.length
    if length <= 0:
        return []
    n = max(2, int(np.ceil(length / step_m)) + 1)
    dists = np.linspace(0, length, n)
    return [line_proj.interpolate(d) for d in dists]

def compute_shade_for_edges(edges_gdf: gpd.GeoDataFrame, trees_gdf_wgs84: gpd.GeoDataFrame,
                           canopy_radius_m: float = DEFAULT_CANOPY_RADIUS_M,
                           sample_step_m: float = SAMPLE_STEP_M) -> gpd.GeoDataFrame:
    """
    Adds shade_frac and sun_min and time_min to edges_gdf.
    Shade is computed by sampling points along edge and checking if they fall within
    any tree canopy buffer.
    """
    to_proj, _ = _project_transformers()

    # Project edges + trees
    edges_proj = edges_gdf.copy()
    edges_proj["geometry"] = edges_proj["geometry"].apply(lambda g: transform(to_proj, g))

    trees_proj = trees_gdf_wgs84.copy()
    trees_proj["geometry"] = trees_proj["geometry"].apply(lambda g: transform(to_proj, g))

    # Attempt to infer canopy radius from common fields; fallback to constant
    canopy_col_candidates = ["CANOPY_DIA", "CANOPY_DI", "CROWN_DIA", "CROWN_DIA_M", "CANOPY_M"]
    canopy_col = next((c for c in canopy_col_candidates if c in trees_proj.columns), None)

    if canopy_col:
        # assume diameter in meters if it looks like meters; if in feet, you can adjust later
        radii = trees_proj[canopy_col].astype(float).replace([np.inf, -np.inf], np.nan)
        trees_proj["_radius_m"] = np.where(radii.notna(), np.clip(radii / 2.0, 1.5, 15.0), canopy_radius_m)
    else:
        trees_proj["_radius_m"] = canopy_radius_m

    # Spatial index on tree points
    sidx = trees_proj.sindex

    shade_fracs = []
    time_mins = []
    sun_mins = []

    for geom, length_m in zip(edges_gdf.geometry, edges_gdf["length"]):
        # time in minutes
        tmin = (float(length_m) / WALK_SPEED_MPS) / 60.0
        time_mins.append(tmin)

        if geom is None or geom.is_empty:
            shade_fracs.append(0.0)
            sun_mins.append(tmin)
            continue

        geom_proj = transform(to_proj, geom)
        if not isinstance(geom_proj, LineString):
            # MultiLineString -> merge to a linestring-ish
            geom_proj = LineString(list(geom_proj.geoms[0].coords)) if hasattr(geom_proj, "geoms") else geom_proj

        # Query nearby trees by bbox expansion
        minx, miny, maxx, maxy = geom_proj.bounds
        pad = 20.0
        cand_idx = list(sidx.intersection((minx - pad, miny - pad, maxx + pad, maxy + pad)))
        if not cand_idx:
            shade_fracs.append(0.0)
            sun_mins.append(tmin)
            continue

        cands = trees_proj.iloc[cand_idx]
        # Precompute canopy buffers for candidates (small set per edge)
        buffers = [pt.buffer(float(r)) for pt, r in zip(cands.geometry, cands["_radius_m"]) if pt is not None]

        samples = _edge_samples_projected(geom_proj, sample_step_m)
        if not samples or not buffers:
            shade_fracs.append(0.0)
            sun_mins.append(tmin)
            continue

        shaded = 0
        for p in samples:
            # any buffer contains point?
            if any(b.contains(p) for b in buffers):
                shaded += 1

        frac = shaded / len(samples)
        shade_fracs.append(float(frac))
        sun_mins.append((1.0 - float(frac)) * tmin)

    out = edges_gdf.copy()
    out["time_min"] = time_mins
    out["shade_frac"] = shade_fracs
    out["sun_min"] = sun_mins
    return out

def mrt_celsius(shade_frac: float, cond: Conditions) -> float:
    """Simplified outdoor Mean Radiant Temperature (degC) for a pedestrian.

    Combines longwave from the surroundings (~air temperature) with absorbed
    shortwave — the direct beam, the diffuse sky component, and ground-reflected
    radiation — via the radiant flux balance
    ``Tmrt = ((Rlong + Ssw) / (eps*sigma))**0.25``.

    ``shade_frac`` attenuates the *entire* shortwave load, not just the beam: a
    tree canopy or a building's shadow blocks the direct sun and most of the sky
    view / reflected radiation. So in deep shade the shortwave term nearly
    vanishes and MRT falls back toward air temperature, while in open sun it can
    run 15-30 degC hotter — the contrast the router needs.
    """
    ta_k = cond.air_temp_c + 273.15
    s_global = cond.direct_rad + cond.diffuse_rad
    # Shortwave a fully sun-exposed pedestrian would absorb.
    s_open = (
        MRT_PROJECTED_AREA_FACTOR * cond.direct_rad
        + 0.5 * cond.diffuse_rad
        + 0.5 * GROUND_ALBEDO * s_global
    )
    s_abs = MRT_SW_ABSORPTION * s_open * (1.0 - SHADE_SHORTWAVE_BLOCK * shade_frac)
    r_long = MRT_EMISSIVITY * STEFAN_BOLTZMANN * ta_k ** 4
    tmrt_k = ((r_long + s_abs) / (MRT_EMISSIVITY * STEFAN_BOLTZMANN)) ** 0.25
    return float(tmrt_k - 273.15)


@dataclass
class EdgeSamples:
    """Static per-edge geometry precomputed once (edges never move).

    Holds every edge's projected sample points flattened into one array (plus a
    map back to the owning edge), so per-hour scoring is a single vectorized
    STRtree query instead of a per-edge, per-point Python loop.
    """
    index: Any                 # edges_gdf index: (u, v, key) tuples
    time_min: np.ndarray       # walking minutes per edge
    all_pts: np.ndarray        # object array of projected shapely Points
    pt_edge_idx: np.ndarray    # int, sample point -> edge position
    sample_count: np.ndarray   # int, samples per edge


def precompute_edge_samples(edges_gdf: gpd.GeoDataFrame,
                            sample_step_m: float = SAMPLE_STEP_M) -> EdgeSamples:
    """Project edges to meters and pre-sample points along each (startup, once).

    float32 throughout: routing weights don't need float64 precision, and this
    array is held for the app's whole lifetime, so halving it matters on
    Render's 512MB tier.
    """
    proj = edges_gdf.to_crs(PROJECT_CRS)
    lengths = edges_gdf["length"].to_numpy(dtype=np.float32)
    time_min = (lengths / np.float32(WALK_SPEED_MPS) / np.float32(60.0)).astype(np.float32)

    all_pts: List[Point] = []
    pt_edge_idx: List[int] = []
    sample_count = np.zeros(len(edges_gdf), dtype=int)

    for i, geom in enumerate(proj.geometry):
        if geom is None or geom.is_empty:
            continue
        if not isinstance(geom, LineString) and hasattr(geom, "geoms"):
            geom = LineString(list(geom.geoms[0].coords))
        pts = _edge_samples_projected(geom, sample_step_m)
        sample_count[i] = len(pts)
        all_pts.extend(pts)
        pt_edge_idx.extend([i] * len(pts))

    return EdgeSamples(
        index=edges_gdf.index,
        time_min=time_min,
        all_pts=np.array(all_pts, dtype=object),
        pt_edge_idx=np.array(pt_edge_idx, dtype=int),
        sample_count=sample_count,
    )


def score_edges_from_samples(es: EdgeSamples, shade: ShadeGeometry, cond: Conditions) -> pd.DataFrame:
    """Score every edge for one instant: shade fraction, MRT, and heat penalty.

    Vectorized end-to-end — one STRtree query over all sample points, a bincount
    to get per-edge shade fraction, then numpy MRT/penalty math. Kept in float32:
    this DataFrame is discarded immediately after its values are written into the
    graph (see attach_edge_weights_timeaware), but it still peaks at ~5 float
    columns x ~42k edges while it's alive, so halving it caps that peak.
    """
    n_edges = len(es.index)
    f32 = np.float32

    if shade.tree is None or es.all_pts.size == 0:
        frac = np.zeros(n_edges, dtype=f32)
    else:
        # query returns [input_idx, tree_idx] pairs; input_idx are shaded points.
        hits = shade.tree.query(es.all_pts, predicate="intersects")
        shaded_mask = np.zeros(es.all_pts.size, dtype=bool)
        shaded_mask[hits[0]] = True
        shaded = np.bincount(es.pt_edge_idx, weights=shaded_mask.astype(f32), minlength=n_edges)
        frac = np.where(es.sample_count > 0, shaded / np.maximum(es.sample_count, 1), 0.0).astype(f32)

    # Vectorized MRT (see mrt_celsius for the model); shade attenuates shortwave.
    # cond.* are plain Python floats (scalars), so casting them to float32 keeps
    # every array operation below in float32 rather than upcasting to float64.
    air_temp_c = f32(cond.air_temp_c)
    direct_rad = f32(cond.direct_rad)
    diffuse_rad = f32(cond.diffuse_rad)
    ta_k = air_temp_c + f32(273.15)
    s_global = direct_rad + diffuse_rad
    s_open = (f32(MRT_PROJECTED_AREA_FACTOR) * direct_rad
              + f32(0.5) * diffuse_rad
              + f32(0.5) * f32(GROUND_ALBEDO) * s_global)
    s_abs = (f32(MRT_SW_ABSORPTION) * s_open * (f32(1.0) - f32(SHADE_SHORTWAVE_BLOCK) * frac)).astype(f32)
    r_long = f32(MRT_EMISSIVITY) * f32(STEFAN_BOLTZMANN) * ta_k ** 4
    mrt = (((r_long + s_abs) / (f32(MRT_EMISSIVITY) * f32(STEFAN_BOLTZMANN))) ** f32(0.25) - f32(273.15)).astype(f32)

    excess = np.maximum(f32(0.0), mrt - air_temp_c).astype(f32)
    sun_min = ((f32(1.0) - frac) * es.time_min).astype(f32)
    penalty = (es.time_min * (f32(1.0) + excess / f32(MRT_REF_EXCESS_C))).astype(f32)

    return pd.DataFrame(
        {
            "time_min": es.time_min,
            "shade_frac": frac,
            "sun_min": sun_min,
            "mrt_c": mrt,
            "heat_penalty_min": penalty,
        },
        index=es.index,
    )


def attach_edge_weights_timeaware(
    G: nx.MultiDiGraph, edges_scored: pd.DataFrame, alpha: float, beta: float
) -> nx.MultiDiGraph:
    """Write time-aware attributes + routing weights onto the graph.

    ``w_fast`` minimizes walking time; ``w_heat`` trades time against the
    MRT-driven ``heat_penalty_min`` via alpha/beta. Iterates over numpy columns
    (not ``iterrows``) so it stays fast across ~42k edges.
    """
    tm = edges_scored["time_min"].to_numpy()
    sf = edges_scored["shade_frac"].to_numpy()
    sm = edges_scored["sun_min"].to_numpy()
    mr = edges_scored["mrt_c"].to_numpy()
    pen = edges_scored["heat_penalty_min"].to_numpy()

    for (u, v, k), t, s, su, m, p in zip(edges_scored.index, tm, sf, sm, mr, pen):
        if not G.has_edge(u, v, k):
            continue
        d = G[u][v][k]
        t = float(t); p = float(p)
        d["time_min"] = t
        d["shade_frac"] = float(s)
        d["sun_min"] = float(su)
        d["mrt_c"] = float(m)
        d["heat_penalty_min"] = p
        d["w_fast"] = t
        d["w_heat"] = alpha * t + beta * p
    return G


def attach_edge_weights(G: nx.MultiDiGraph, edges_scored: gpd.GeoDataFrame, alpha: float, beta: float) -> nx.MultiDiGraph:
    """
    Writes edge attributes into the graph for routing.
    """
    # edges_scored index is (u, v, key)
    for (u, v, k), row in edges_scored.iterrows():
        if G.has_edge(u, v, k):
            G[u][v][k]["time_min"] = float(row.get("time_min", 0.0))
            G[u][v][k]["shade_frac"] = float(row.get("shade_frac", 0.0))
            G[u][v][k]["sun_min"] = float(row.get("sun_min", 0.0))
            G[u][v][k]["w_fast"] = float(row.get("time_min", 0.0))
            G[u][v][k]["w_heat"] = alpha * float(row.get("time_min", 0.0)) + beta * float(row.get("sun_min", 0.0))
    return G

def shortest_path(G: nx.MultiDiGraph, start_lat: float, start_lon: float, end_lat: float, end_lon: float, weight: str) -> List[int]:
    u = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    v = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)
    route = nx.shortest_path(G, u, v, weight=weight)
    return route

def route_geojson_and_metrics(G: nx.MultiDiGraph, route: List[int]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    gdf = ox.routing.route_to_gdf(G, route, weight="length")
    # dissolve into single line
    line = gdf.unary_union
    gj = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": mapping(line)
        }]
    }

    dist_m = float(gdf["length"].sum())
    time_min = float(gdf.get("time_min", 0).sum()) if "time_min" in gdf.columns else dist_m / WALK_SPEED_MPS / 60.0
    sun_min = float(gdf.get("sun_min", 0).sum()) if "sun_min" in gdf.columns else time_min
    weights = gdf["length"].values
    shade_avg = 0.0
    mrt_avg = 0.0
    if len(gdf) > 0 and weights.sum() > 0:
        if "shade_frac" in gdf.columns:
            shade_avg = float(np.average(gdf["shade_frac"].values, weights=weights))
        if "mrt_c" in gdf.columns:
            mrt_avg = float(np.average(gdf["mrt_c"].values, weights=weights))

    metrics = {
        "distance_m": dist_m,
        "distance_km": dist_m / 1000.0,
        "eta_min": time_min,
        "sun_min_proxy": sun_min,
        "shade_score_pct": 100.0 * shade_avg,
        "mrt_c": mrt_avg,
    }
    return gj, metrics


def route_via_node(G: nx.MultiDiGraph, start_lat: float, start_lon: float,
                   end_lat: float, end_lon: float, via_node: int, weight: str) -> List[int]:
    """Shortest path from start to end that is forced through ``via_node``."""
    s = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    t = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)
    leg1 = nx.shortest_path(G, s, via_node, weight=weight)
    leg2 = nx.shortest_path(G, via_node, t, weight=weight)
    return leg1 + leg2[1:]


def best_cooling_via(
    G: nx.MultiDiGraph,
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    cooling_nodes: List[int],
    weight: str,
    direct_cost: float,
    max_detour_ratio: float,
) -> Tuple[int | None, float]:
    """Pick the cooling-stop node that adds the least heat-aware detour.

    Uses two single-source Dijkstra sweeps (from start, and to end on the
    reversed graph) so every candidate is evaluated in O(1) instead of routing
    to each one individually. Returns (node, total_cost) or (None, inf) if no
    candidate stays within ``max_detour_ratio`` of the direct route.
    """
    s = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    t = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

    dist_from_start = nx.single_source_dijkstra_path_length(G, s, weight=weight)
    dist_to_end = nx.single_source_dijkstra_path_length(G.reverse(copy=False), t, weight=weight)

    best_node, best_cost = None, float("inf")
    budget = direct_cost * max_detour_ratio
    for n in cooling_nodes:
        if n in dist_from_start and n in dist_to_end:
            total = dist_from_start[n] + dist_to_end[n]
            if total < best_cost and total <= budget:
                best_node, best_cost = n, total
    return best_node, best_cost