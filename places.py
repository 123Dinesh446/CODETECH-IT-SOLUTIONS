from __future__ import annotations

import math
from typing import Any, Dict, List

import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def fetch_nearby_hospitals(lat: float, lon: float, radius_m: int = 2000) -> List[Dict[str, Any]]:
    # Query hospitals and clinics within radius
    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:{radius_m},{lat},{lon});
      node["amenity"="clinic"](around:{radius_m},{lat},{lon});
    );
    out center tags;
    """
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        data = resp.json()

    elements = data.get("elements", [])
    results: List[Dict[str, Any]] = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or "Unknown"
        lat2 = el.get("lat") or (el.get("center") or {}).get("lat")
        lon2 = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat2 is None or lon2 is None:
            continue
        distance_km = _haversine_km(lat, lon, float(lat2), float(lon2))
        addr = ", ".join(filter(None, [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city"),
            tags.get("addr:state"),
        ]))
        results.append({
            "name": name,
            "lat": lat2,
            "lon": lon2,
            "amenity": tags.get("amenity"),
            "address": addr or None,
            "distance_km": round(distance_km, 3),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "website": tags.get("website"),
        })

    results.sort(key=lambda r: r.get("distance_km", 9999))
    return results
