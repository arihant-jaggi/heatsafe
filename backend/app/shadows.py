"""Time-aware ground shadows from buildings (and trees) using pysolar.

Instead of a single static canopy layer, we compute where shadows actually fall
for a given instant: the sun's altitude/azimuth (from pysolar) plus building
heights (from OSM) determine each shadow's length and direction. A low morning
sun throws long shadows one way; a high 2 pm sun throws short shadows the other
way, so the shade-aware route genuinely changes with time of day.

Projected inputs are prepared once via :func:`prepare_shade_inputs`; then
:func:`build_shade_index` casts the time-of-day shadows and returns an STRtree
spatial index of shadow polygons (project CRS) plus solar metadata. Everything is
done in projected meters so translations and buffers are metric.

Scaled for the full barrier island (~14k buildings, ~42k edges): rather than
union everything into one giant geometry and prepared-test against it, we keep
the shadow polygons separate and index them with an STRtree, so each sample
point is an O(log n) lookup. Shadows are cast as a convex-hull sweep of the
footprint (exact for convex buildings, cheap for all).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import shapely
import geopandas as gpd
from shapely.strtree import STRtree
from pysolar import solar

from .settings import (
    PROJECT_CRS,
    STOREY_HEIGHT_M,
    DEFAULT_BUILDING_HEIGHT_M,
    MAX_SHADOW_LEN_M,
    MIN_SUN_ALTITUDE_DEG,
    DEFAULT_CANOPY_RADIUS_M,
)

# Height of a tree canopy above ground used when casting its (small) shadow.
TREE_CANOPY_HEIGHT_M = 6.0


@dataclass
class SolarInfo:
    altitude_deg: float
    azimuth_deg: float
    is_daytime: bool


@dataclass
class ShadeGeometry:
    tree: Optional[STRtree]   # spatial index of shadow polygons (None => no shade)
    solar: SolarInfo


@dataclass
class ShadeInputs:
    """Projected, static inputs prepared once so per-hour builds are cheap."""
    bld_geoms: np.ndarray      # projected building footprints (object array)
    bld_heights: np.ndarray    # meters, aligned with bld_geoms
    tree_canopies: np.ndarray  # projected canopy disks (object array)


def sun_position(when_local: datetime, lat: float, lon: float) -> SolarInfo:
    """Solar altitude/azimuth (degrees) for a timezone-aware local datetime.

    pysolar wants UTC; azimuth is degrees clockwise from north (N=0, E=90).
    """
    when_utc = when_local.astimezone(timezone.utc)
    alt = solar.get_altitude(lat, lon, when_utc)
    az = solar.get_azimuth(lat, lon, when_utc)
    return SolarInfo(
        altitude_deg=float(alt),
        azimuth_deg=float(az % 360.0),
        is_daytime=bool(alt > MIN_SUN_ALTITUDE_DEG),
    )


def _shadow_vector(height_m: float, sun: SolarInfo) -> tuple[float, float]:
    """Ground displacement (east, north) of a shadow tip for a given height."""
    alt_rad = np.radians(max(sun.altitude_deg, MIN_SUN_ALTITUDE_DEG))
    length = min(height_m / np.tan(alt_rad), MAX_SHADOW_LEN_M)
    # Shadow is cast opposite the sun direction.
    shadow_az = np.radians(sun.azimuth_deg + 180.0)
    dx = length * np.sin(shadow_az)   # east component
    dy = length * np.cos(shadow_az)   # north component
    return float(dx), float(dy)


def _translate_many(geoms: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Vectorized per-geometry translation by (dx_i, dy_i) — no Python geom loop.

    Copies the geometries (identity transform) so the originals are untouched,
    then shifts every vertex by its geometry's offset in one numpy operation.
    """
    copies = shapely.transform(geoms, lambda a: a)  # deep copies
    coords = shapely.get_coordinates(copies)
    ncoords = shapely.get_num_coordinates(copies)
    offsets = np.repeat(np.column_stack([dx, dy]), ncoords, axis=0)
    return shapely.set_coordinates(copies, coords + offsets)


def building_height(row) -> float:
    """Best-effort building height (meters) from OSM height / building:levels."""
    h = row.get("height")
    if h is not None:
        try:
            # OSM height can be "12", "12 m", "12.5" ...
            return float(str(h).split()[0].replace(",", "."))
        except (ValueError, IndexError):
            pass
    levels = row.get("building:levels")
    if levels is not None:
        try:
            return float(str(levels).split()[0]) * STOREY_HEIGHT_M
        except (ValueError, IndexError):
            pass
    return DEFAULT_BUILDING_HEIGHT_M


def prepare_shade_inputs(
    buildings_wgs84: Optional[gpd.GeoDataFrame],
    trees_wgs84: Optional[gpd.GeoDataFrame],
) -> ShadeInputs:
    """Project buildings + tree canopies to meters once (buildings never move).

    Called at startup; the per-hour :func:`build_shade_index` then only casts and
    indexes shadows, avoiding a fresh reprojection of ~14k geometries per request.
    """
    bgeoms: List = []
    bheights: List[float] = []
    if buildings_wgs84 is not None and len(buildings_wgs84) > 0:
        proj = buildings_wgs84.to_crs(PROJECT_CRS)
        for geom, row in zip(proj.geometry, buildings_wgs84.to_dict("records")):
            if geom is None or geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
                continue
            bgeoms.append(geom)
            bheights.append(building_height(row))

    tcanopies: List = []
    if trees_wgs84 is not None and len(trees_wgs84) > 0:
        radii = _tree_radii(trees_wgs84)
        proj = trees_wgs84.to_crs(PROJECT_CRS)
        for geom, r in zip(proj.geometry, radii):
            if geom is None or geom.is_empty:
                continue
            tcanopies.append(geom.buffer(float(r)))

    return ShadeInputs(
        bld_geoms=np.array(bgeoms, dtype=object),
        bld_heights=np.array(bheights, dtype=float),
        tree_canopies=np.array(tcanopies, dtype=object),
    )


def build_shade_index(inp: ShadeInputs, when_local: datetime, lat: float, lon: float) -> ShadeGeometry:
    """Cast time-of-day shadows and index them for fast point-in-shade lookups.

    Building shadows are a convex-hull sweep of each footprint and its
    sun-projected copy (vectorized). Tree canopies always shade the ground
    beneath them, plus a short cast shadow when the sun is up. At night buildings
    cast nothing and MRT collapses toward air temperature.
    """
    sun = sun_position(when_local, lat, lon)
    parts: List = []

    if sun.is_daytime and inp.bld_geoms.size > 0:
        alt_rad = math.radians(max(sun.altitude_deg, MIN_SUN_ALTITUDE_DEG))
        lengths = np.minimum(inp.bld_heights / math.tan(alt_rad), MAX_SHADOW_LEN_M)
        shadow_az = math.radians(sun.azimuth_deg + 180.0)
        dx = lengths * math.sin(shadow_az)
        dy = lengths * math.cos(shadow_az)
        moved = _translate_many(inp.bld_geoms, dx, dy)
        # Swept shadow = convex hull of footprint + its projected copy (vectorized).
        hulls = shapely.convex_hull(shapely.union(inp.bld_geoms, moved))
        parts.extend(hulls.tolist())

    if inp.tree_canopies.size > 0:
        parts.extend(inp.tree_canopies.tolist())
        if sun.is_daytime:
            tdx, tdy = _shadow_vector(TREE_CANOPY_HEIGHT_M, sun)
            n = inp.tree_canopies.size
            moved_t = _translate_many(inp.tree_canopies, np.full(n, tdx), np.full(n, tdy))
            parts.extend(moved_t.tolist())

    tree = STRtree(parts) if parts else None
    return ShadeGeometry(tree=tree, solar=sun)


def _tree_radii(trees_wgs84: gpd.GeoDataFrame) -> np.ndarray:
    """Canopy radius (m) per tree, inferred from a diameter column if present."""
    candidates = ["CANOPY_DIA", "CANOPY_DI", "CROWN_DIA", "CROWN_DIA_M", "CANOPY_M"]
    col = next((c for c in candidates if c in trees_wgs84.columns), None)
    if col is None:
        return np.full(len(trees_wgs84), DEFAULT_CANOPY_RADIUS_M)
    radii = trees_wgs84[col].astype(float).replace([np.inf, -np.inf], np.nan)
    return np.where(radii.notna(), np.clip(radii / 2.0, 1.5, 15.0), DEFAULT_CANOPY_RADIUS_M)
