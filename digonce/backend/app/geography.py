"""
Geography and jurisdiction services for Tamil Nadu.

Uses real OpenStreetMap/Nominatim data for search and reverse geocoding when
network access is available. Administrative hierarchy fields are derived from
geocoder responses where present; unavailable fields are returned as empty and
never invented. District reference coordinates are static reference points for
navigation only, not parcel/legal boundaries.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from ml.config import DISTRICTS, LAT_MAX, LAT_MIN, LON_MAX, LON_MIN

NOMINATIM_BASE = os.getenv("NAGARSYNC_NOMINATIM_URL", "https://nominatim.openstreetmap.org")
USER_AGENT = os.getenv("NAGARSYNC_GEO_USER_AGENT", "NagarSync/1.0 (civic infrastructure platform)")
TN_VIEWBOX = f"{LON_MIN},{LAT_MAX},{LON_MAX},{LAT_MIN}"
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 300.0


def _cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any):
    _CACHE[key] = (time.time(), value)
    if len(_CACHE) > 400:
        for k in list(_CACHE.keys())[:120]:
            _CACHE.pop(k, None)


def tn_districts() -> list[dict[str, Any]]:
    items = []
    for idx, item in enumerate(DISTRICTS):
        name, lat, lon = item[0], float(item[1]), float(item[2])
        items.append({"id": idx, "name": name, "lat": lat, "lon": lon, "state": "Tamil Nadu"})
    known = {d["name"].casefold() for d in items}
    for extra in (
        ("Kancheepuram", 12.8342, 79.7036),
        ("Kanyakumari", 8.0883, 77.5385),
        ("Tirupathur", 12.4960, 78.5730),
        ("Tiruvannamalai", 12.2253, 79.0747),
        ("Viluppuram", 11.9401, 79.4861),
    ):
        if extra[0].casefold() not in known:
            items.append({"id": len(items), "name": extra[0], "lat": extra[1], "lon": extra[2], "state": "Tamil Nadu"})
    items.sort(key=lambda x: x["name"])
    return items


def in_tamil_nadu(lat: float, lon: float) -> bool:
    return LAT_MIN - 0.25 <= lat <= LAT_MAX + 0.25 and LON_MIN - 0.25 <= lon <= LON_MAX + 0.25


def _http_json(url: str, timeout: float = 8.0):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clean(value: Any) -> str:
    return str(value or "").strip()[:120]


def _pick(address: dict, *keys: str) -> str:
    for key in keys:
        val = _clean(address.get(key))
        if val:
            return val
    return ""


def nearest_district(lat: float, lon: float) -> dict[str, Any] | None:
    best = None
    best_d = float("inf")
    for d in tn_districts():
        dd = (d["lat"] - lat) ** 2 + (d["lon"] - lon) ** 2
        if dd < best_d:
            best_d = dd
            best = d
    return best


def normalize_hierarchy(*, address: dict | None = None, lat: float | None = None, lon: float | None = None,
                        display_name: str = "", source: str = "") -> dict[str, Any]:
    address = address or {}
    state = _pick(address, "state") or ("Tamil Nadu" if lat is not None and lon is not None and in_tamil_nadu(lat, lon) else "")
    district = _pick(address, "state_district", "district")
    if district.lower().endswith(" district"):
        district = district[: -len(" district")].strip()
    taluk = _pick(address, "county", "subdistrict", "municipality")
    block = _pick(address, "block", "borough")
    local_body = _pick(address, "city", "town", "municipality", "village", "hamlet", "city_district")
    local_body_type = ""
    for key, label in (
        ("city", "Corporation/City"),
        ("town", "Town"),
        ("municipality", "Municipality"),
        ("village", "Village Panchayat"),
        ("hamlet", "Hamlet"),
        ("suburb", "Urban Locality"),
    ):
        if _pick(address, key):
            local_body_type = label
            break
    ward = _pick(address, "quarter", "neighbourhood", "suburb", "city_district", "ward")
    village = _pick(address, "village", "hamlet")
    locality = _pick(address, "neighbourhood", "suburb", "road", "residential", "quarter", "hamlet", "village")
    pincode = _pick(address, "postcode")

    if (not district or "tamil nadu" in district.lower()) and lat is not None and lon is not None and in_tamil_nadu(lat, lon):
        nearest = nearest_district(lat, lon)
        if nearest:
            district = district or nearest["name"]

    return {
        "state": state or "Tamil Nadu",
        "district": district,
        "taluk": taluk,
        "block": block,
        "local_body": local_body,
        "local_body_type": local_body_type,
        "ward_or_village": ward or village,
        "ward": ward,
        "village": village,
        "locality": locality,
        "pincode": pincode,
        "display_name": _clean(display_name),
        "lat": lat,
        "lon": lon,
        "source": source or "unknown",
        "verified_boundary": False,
        "available_levels": [k for k, v in {
            "state": state or "Tamil Nadu",
            "district": district,
            "taluk": taluk,
            "block": block,
            "local_body": local_body,
            "ward_or_village": ward or village,
            "locality": locality,
        }.items() if _clean(v)],
    }


def search_places(query: str, limit: int = 8) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if len(query) < 2:
        return []
    cache_key = f"s:{query.lower()}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": str(max(1, min(limit, 10))),
        "countrycodes": "in",
        "viewbox": TN_VIEWBOX,
        "bounded": "0",
        "q": query if "tamil nadu" in query.lower() else f"{query}, Tamil Nadu, India",
    }
    url = f"{NOMINATIM_BASE.rstrip('/')}/search?{urllib.parse.urlencode(params)}"
    try:
        data = _http_json(url) or []
    except Exception:
        return []
    results = []
    for item in data:
        try:
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
        except Exception:
            continue
        h = normalize_hierarchy(
            address=item.get("address") or {},
            lat=lat,
            lon=lon,
            display_name=item.get("display_name") or "",
            source="nominatim_search",
        )
        h["place_id"] = item.get("place_id")
        h["osm_type"] = item.get("osm_type")
        h["osm_id"] = item.get("osm_id")
        results.append(h)
    results.sort(key=lambda r: (0 if in_tamil_nadu(r.get("lat") or 0, r.get("lon") or 0) else 1))
    _cache_set(cache_key, results)
    return results


def reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    lat = float(lat)
    lon = float(lon)
    cache_key = f"r:{round(lat,5)}:{round(lon,5)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {
        "format": "jsonv2",
        "addressdetails": "1",
        "lat": str(lat),
        "lon": str(lon),
        "zoom": "18",
    }
    url = f"{NOMINATIM_BASE.rstrip('/')}/reverse?{urllib.parse.urlencode(params)}"
    try:
        data = _http_json(url) or {}
        h = normalize_hierarchy(
            address=data.get("address") or {},
            lat=lat,
            lon=lon,
            display_name=data.get("display_name") or "",
            source="nominatim_reverse",
        )
    except Exception:
        h = normalize_hierarchy(address={}, lat=lat, lon=lon, display_name="", source="coordinates_only")
        nd = nearest_district(lat, lon)
        if nd and in_tamil_nadu(lat, lon):
            h["district"] = h["district"] or nd["name"]
            h["nearest_district_reference"] = nd["name"]
            h["note"] = "Administrative labels unavailable from geocoding service; nearest district is a reference estimate."
    h["in_tamil_nadu_bbox"] = in_tamil_nadu(lat, lon)
    _cache_set(cache_key, h)
    return h


def jurisdiction_for_area(values: dict[str, Any]) -> dict[str, Any]:
    district = _clean(values.get("district"))
    taluk = _clean(values.get("taluk"))
    block = _clean(values.get("block"))
    local_body = _clean(values.get("local_body") or values.get("municipality") or values.get("panchayat"))
    ward = _clean(values.get("ward") or values.get("ward_or_village") or values.get("village"))
    locality = _clean(values.get("locality"))
    level = "state"
    authority = "State-level administrator"
    if ward or locality:
        level = "ward_village_locality"
        authority = "Local-body / ward-level operations"
    elif local_body:
        level = "local_body"
        authority = "Municipality / Corporation / Town or Village Panchayat administrator"
    elif block:
        level = "block"
        authority = "Block administrator"
    elif taluk:
        level = "taluk"
        authority = "Taluk administrator"
    elif district:
        level = "district"
        authority = "District administrator"
    return {
        "level": level,
        "suggested_authority": authority,
        "district": district,
        "taluk": taluk,
        "block": block,
        "local_body": local_body,
        "ward_or_village": ward,
        "locality": locality,
        "routing_configurable": True,
    }


def hierarchy_options() -> dict[str, Any]:
    return {
        "state": "Tamil Nadu",
        "districts": tn_districts(),
        "notes": {
            "taluk_block_local_body_ward": "Taluk, block, local body, ward/village and locality labels are resolved from selected coordinates or search results using available geocoding data; unavailable levels remain blank and must not be assumed.",
            "boundaries": "Official administrative boundary polygons are not bundled in this build; jurisdiction is identified from geocoded administrative fields and user-confirmed hierarchy.",
        },
    }
