import json
from pathlib import Path
import requests

# Miami Beach Tree Inventory FeatureServer
BASE = "https://gis.miamibeachfl.gov/public/rest/services/gc/gc_TreeInventory/FeatureServer/0/query"

OUT = Path(__file__).resolve().parents[1] / "data" / "trees.geojson"

# Bounding box must match your neighborhood; this one covers the sample polygon above (W,S,E,N)
BBOX = (-80.1419, 25.7772, -80.1242, 25.8006)

params = {
    "where": "1=1",
    "geometry": f"{BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}",
    "geometryType": "esriGeometryEnvelope",
    "inSR": 4326,
    "outSR": 4326,
    "outFields": "*",
    "returnGeometry": "true",
    "f": "geojson"
}

print("Requesting trees…")
r = requests.get(BASE, params=params, timeout=60)
r.raise_for_status()
gj = r.json()

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(gj), encoding="utf-8")

print(f"Saved {OUT} with {len(gj.get('features', []))} features")
