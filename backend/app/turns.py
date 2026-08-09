from __future__ import annotations

from typing import Any, Dict, List, Optional
import math
import networkx as nx

# Steps shorter than this are graph noise (tiny connector edges). We merge their
# distance into the preceding step instead of showing "Turn ... (4m)".
MIN_STEP_M = 10.0


def _clean_str(v: Any) -> Optional[str]:
    """First usable string from an OSM value, or None. NaN/blank/'nan' -> None.

    OSM columns are sparse (missing => float NaN) and multi-valued tags come
    back as lists, so a plain ``row.get`` can yield NaN or a list — which is how
    'nan' leaked into directions.
    """
    if v is None:
        return None
    if isinstance(v, list):
        for x in v:
            c = _clean_str(x)
            if c:
                return c
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def _edge_label(row) -> str:
    """Human street label with a robust fallback chain (never 'nan').

    name -> ref (road number) -> highway type (e.g. "residential street")
    -> "unnamed street".
    """
    name = _clean_str(row.get("name"))
    if name:
        return name
    ref = _clean_str(row.get("ref"))
    if ref:
        return ref
    highway = _clean_str(row.get("highway"))
    if highway:
        # Pedestrian ways read better as a "walking path" than "footway street".
        if highway.lower() in ("footway", "pedestrian", "path"):
            return "walking path"
        return f"{highway} street"
    return "unnamed street"


def _bearing(lat1, lon1, lat2, lon2) -> float:
    # bearing in degrees
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlon)
    brng = (math.degrees(math.atan2(x, y)) + 360) % 360
    return brng

def _turn_dir(prev_b: float, next_b: float) -> str:
    delta = (next_b - prev_b + 540) % 360 - 180
    if abs(delta) < 25:
        return "Continue"
    return "Turn right" if delta > 0 else "Turn left"


_COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]


def _compass(bearing: float) -> str:
    return _COMPASS[int((bearing + 22.5) % 360 // 45)]


def _instruction(verb: str, road: str) -> str:
    """Join an entering verb + road name. Turns read 'onto', others 'on'."""
    prep = "onto" if verb.startswith("Turn") else "on"
    return f"{verb} {prep} {road}"


def _merge_short_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fold sub-``MIN_STEP_M`` steps into the preceding step's distance."""
    merged: List[Dict[str, Any]] = []
    for s in steps:
        if merged and s["distance_m"] < MIN_STEP_M:
            merged[-1]["distance_m"] += s["distance_m"]
        else:
            merged.append(dict(s))
    return merged


def route_steps(G: nx.MultiDiGraph, route: List[int]) -> List[Dict[str, Any]]:
    # Read node coords + edge attrs straight from the graph. (Converting the
    # whole graph to GeoDataFrames here cost ~10s per request on the full island.)
    steps: List[Dict[str, Any]] = []
    if len(route) < 2:
        return steps

    prev_b = None
    current_road = None
    enter_verb = ""        # how you got onto the current road (e.g. "Head east")
    acc_len = 0.0
    acc_shade = 0.0        # length-weighted shade so we can report % per step

    def flush():
        pct = (acc_shade / acc_len * 100.0) if acc_len > 0 else 0.0
        steps.append({
            "instruction": _instruction(enter_verb, current_road),
            "distance_m": acc_len,
            "shade_pct": pct,
        })

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        # pick the shortest edge among parallel edges for labeling
        row = min(edge_data.values(), key=lambda d: d.get("length", float("inf")))

        name = _edge_label(row)
        length = float(row.get("length", 0.0))
        shade = float(row.get("shade_frac", 0.0))

        un, vn = G.nodes[u], G.nodes[v]
        b = _bearing(float(un["y"]), float(un["x"]), float(vn["y"]), float(vn["x"]))

        if current_road is None:
            current_road = name
            enter_verb = f"Head {_compass(b)}"
            acc_len = length
            acc_shade = shade * length
            prev_b = b
            continue

        turn = _turn_dir(prev_b, b) if prev_b is not None else "Continue"
        if name != current_road or turn != "Continue":
            flush()
            current_road = name
            enter_verb = turn            # "Turn left" / "Turn right" / "Continue"
            acc_len = length
            acc_shade = shade * length
        else:
            acc_len += length
            acc_shade += shade * length

        prev_b = b

    if current_road:
        flush()
    return _merge_short_steps(steps)
