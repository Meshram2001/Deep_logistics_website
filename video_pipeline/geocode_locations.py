import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "locations_source.json"
OUT_PATH = ROOT / "locations_geocoded.json"
CACHE_PATH = ROOT / "geocode_cache.json"
MANUAL_OVERRIDES_PATH = ROOT / "geocode_manual_overrides.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Nominatim requires a valid User-Agent with contact info.
# Replace the email with yours before running.
USER_AGENT = "deep-logistics-website/1.0 (contact: deeplogisticsnagpur@gmail.com)"

# Be polite: Nominatim usage guidance is ~1 request/sec.
REQUEST_DELAY_SECONDS = 1.1
TIMEOUT_SECONDS = 25


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_city_for_query(city: str) -> str:
    city = city.strip()
    # Handle a few known naming issues.
    if city.lower() in {"sambhaji nagar", "sambhaji nagar"}:
        # Many datasets still use Aurangabad.
        return "Chhatrapati Sambhajinagar"
    if city.lower() == "panipath":
        return "Panipat"
    if city.lower() == "solapur city":
        return "Solapur"
    if city.lower() == "satara city":
        return "Satara"
    if city.lower() == "up border":
        # Not a city; we approximate it to Uttar Pradesh centroid later.
        return "Uttar Pradesh"

    # Your list says "Phulkua" but the actual place is commonly spelled "Pilkhuwa" (Hapur, UP).
    if city.lower() == "phulkua":
        return "Pilkhuwa"

    return city


def nominatim_search(query: str) -> Optional[Dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT}
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "countrycodes": "in",
    }

    resp = requests.get(NOMINATIM_URL, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    return data[0]


def geocode_city(city: str, state: str, cache: Dict[str, Any], overrides: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], str]:
    key = f"{state}::{city}"

    if key in overrides:
        o = overrides[key]
        return o.get("lat"), o.get("lon"), "manual_override"

    if key in cache:
        c = cache[key]
        return c.get("lat"), c.get("lon"), "cache"

    city_q = normalize_city_for_query(city)

    # Build a robust query.
    # For Delhi localities, state=Delhi is fine.
    query = f"{city_q}, {state}, India"

    result = nominatim_search(query)
    if result is None and city_q != city:
        # Retry with original name
        query = f"{city}, {state}, India"
        result = nominatim_search(query)

    if result is None:
        cache[key] = {"lat": None, "lon": None, "query": query, "status": "not_found"}
        return None, None, "not_found"

    lat = float(result["lat"])
    lon = float(result["lon"])
    cache[key] = {
        "lat": lat,
        "lon": lon,
        "query": query,
        "display_name": result.get("display_name"),
        "type": result.get("type"),
        "class": result.get("class"),
    }
    return lat, lon, "ok"


def main() -> int:
    if not SOURCE_PATH.exists():
        raise SystemExit(f"Missing {SOURCE_PATH}")

    source = load_json(SOURCE_PATH, {})
    cache = load_json(CACHE_PATH, {})
    overrides = load_json(MANUAL_OVERRIDES_PATH, {})

    out: Dict[str, List[Dict[str, Any]]] = {}
    failures: List[str] = []

    for state, cities in source.items():
        out[state] = []
        for city in cities:
            lat, lon, status = geocode_city(city, state, cache, overrides)
            out[state].append({"city": city, "lat": lat, "lon": lon, "status": status})

            if status in {"ok", "manual_override"}:
                pass
            elif status == "cache":
                pass
            else:
                failures.append(f"{state}::{city}")

            # Rate limit between non-cached requests
            if status not in {"cache", "manual_override"}:
                time.sleep(REQUEST_DELAY_SECONDS)

    save_json(CACHE_PATH, cache)
    save_json(OUT_PATH, out)

    if failures:
        print("Geocoding incomplete. Add manual overrides for these keys in geocode_manual_overrides.json:")
        for f in failures:
            print("  -", f)
        return 2

    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
