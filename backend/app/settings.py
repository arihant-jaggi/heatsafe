from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
# Full Miami Beach barrier island: South Point (25.7617) -> Bal Harbour (25.9000).
NBHD_PATH = DATA_DIR / "neighborhoods" / "miami_beach_island.geojson"
# Island bounding box (west, south, east, north) — the boundary of the polygon
# above. Longitudes span the bay (west) and Atlantic (east) shorelines.
ISLAND_BBOX = (-80.16, 25.7617, -80.11, 25.9000)

TREES_PATH = DATA_DIR / "trees.geojson"
GRAPH_PATH = DATA_DIR / "graph.graphml"
BUILDINGS_PATH = DATA_DIR / "buildings.geojson"
COOLING_POIS_PATH = DATA_DIR / "cooling_pois.geojson"

# Miami Beach is UTM zone 17N (meters). Good for buffering/sampling.
PROJECT_CRS = "EPSG:32617"

# Local timezone for Miami Beach. Used to turn a requested hour-of-day into a
# concrete, timezone-aware instant for both the weather lookup and the solar
# position (pysolar) that drives dynamic building shadows.
LOCAL_TZ = "America/New_York"

WALK_SPEED_MPS = 1.2
SAMPLE_STEP_M = 10.0
DEFAULT_CANOPY_RADIUS_M = 4.0

DEFAULT_ALPHA = 1.0
# Heat penalty weight. Large on purpose: the per-edge heat_penalty_min already
# carries the same units as time, so beta is how many "extra minutes of walking"
# we're willing to trade for one minute of avoided radiant load. At beta=8 a
# fully sun-exposed edge costs several times a shaded one, so the router will
# take a meaningfully longer shaded detour instead of the direct sunny path.
DEFAULT_BETA = 8.0

# ---------------------------------------------------------------------------
# Dynamic shadows (buildings)
# ---------------------------------------------------------------------------
# Assumed storey height when a building has building:levels but no height tag.
STOREY_HEIGHT_M = 3.0
# Fallback height (meters) for buildings with no height/levels info at all
# (~two storeys, a reasonable Miami Beach residential default).
DEFAULT_BUILDING_HEIGHT_M = 6.0
# Cap a single shadow's ground length so a low sun near sunrise/sunset does not
# produce kilometre-long shadows that swamp the whole neighborhood.
MAX_SHADOW_LEN_M = 120.0
# Sun altitude (degrees) below which we treat it as effectively night: no
# meaningful direct-beam shadows. Kept low so a just-risen morning sun (e.g.
# ~7 AM in summer, only a couple degrees up) still casts its long shadows and
# the route genuinely differs from midday.
MIN_SUN_ALTITUDE_DEG = 1.0

# ---------------------------------------------------------------------------
# Open-Meteo weather (free, no API key)
# ---------------------------------------------------------------------------
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# Fallback conditions used when the network call fails, so the app still runs
# offline. Hot, humid Miami Beach afternoon defaults.
FALLBACK_AIR_TEMP_C = 32.0
FALLBACK_RH_PCT = 70.0
FALLBACK_DIRECT_RAD = 700.0   # W/m^2 direct beam on a clear afternoon
FALLBACK_DIFFUSE_RAD = 120.0  # W/m^2 diffuse

# ---------------------------------------------------------------------------
# Mean Radiant Temperature (simplified outdoor model)
# ---------------------------------------------------------------------------
STEFAN_BOLTZMANN = 5.670374419e-8  # W/m^2/K^4
MRT_EMISSIVITY = 0.97              # emissivity of clothed human body
MRT_SW_ABSORPTION = 0.7           # shortwave absorption coefficient of a person
MRT_PROJECTED_AREA_FACTOR = 0.28  # fp for a standing person (beam projection)
GROUND_ALBEDO = 0.18              # urban asphalt/concrete mix
# Fraction of the shortwave load a fully shaded spot blocks. Shade (canopy or a
# building's shadow) intercepts the direct beam AND most of the sky/diffuse and
# reflected radiation — so it must attenuate the *whole* shortwave term, not
# just the beam. Without this, shade did nothing on overcast/diffuse-dominated
# hours and every edge collapsed to the same MRT.
SHADE_SHORTWAVE_BLOCK = 0.85
# Radiant excess over air temp (degC) used to normalize MRT into a routing heat
# penalty. Smaller => a sun-exposed edge (MRT well above air temp) gets a much
# higher penalty relative to a shaded one, widening the sun/shade cost contrast
# so shadier alternatives actually win. At ~6degC, a typical afternoon sunny
# edge (MRT ~16degC over air) lands around a 3.7x per-meter penalty vs shade.
MRT_REF_EXCESS_C = 6.0

# Cooling stations: OSM amenities that are reliably air-conditioned.
COOLING_TAGS = {
    "amenity": ["library", "pharmacy", "community_centre", "clinic", "cafe", "fast_food"],
    "shop": ["mall", "department_store", "supermarket", "convenience"],
    "leisure": ["park"],
}
# Only consider cooling stops whose detour keeps the trip within this multiple
# of the direct heat-aware route cost.
COOLING_MAX_DETOUR_RATIO = 1.6
# Cap on number of candidate cooling nodes evaluated for the via-route.
COOLING_MAX_CANDIDATES = 40
