#!/usr/bin/env python3
"""harvest_osm.py — every place OpenStreetMap tags as barbecue in North and South Carolina.

One Overpass query, both states by ISO 3166-2 area, ways and relations reduced to a
centre point. Output is a harvest file, never a record: data/harvest/osm-places.json,
with the licence (ODbL 1.0, share-alike), the fetch time and the query itself, so an
absence can be read as "not in OSM on that date" rather than "does not exist".

    python3 tools/harvest_osm.py            # fetch and write
    python3 tools/harvest_osm.py --dry      # print the count only

Refuses to overwrite a previous harvest with a much smaller one (a zero-element
Overpass reply is valid and looks exactly like "no barbecue in the Carolinas").
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HARVEST, jdump, jload, slugify, state_by_geo  # noqa: E402

UA = "carolina-barbecue-build/0.1 (https://wichaa.net; nan@motdang.net) python-urllib"
ENDPOINT = "https://overpass-api.de/api/interpreter"
QUERY = ('[out:json][timeout:120];'
         'area["ISO3166-2"="US-NC"]->.nc;area["ISO3166-2"="US-SC"]->.sc;'
         '(nwr["cuisine"~"barbecue|bbq",i](area.nc);nwr["cuisine"~"barbecue|bbq",i](area.sc););'
         'out center tags;')
OUT = HARVEST / "osm-places.json"
KEEP = ("name", "amenity", "cuisine", "addr:housenumber", "addr:street", "addr:city", "addr:state", "addr:postcode",
        "phone", "website", "opening_hours", "brand", "brand:wikidata", "wikidata", "wikipedia", "check_date",
        "takeaway", "outdoor_seating", "wheelchair", "contact:facebook", "smoking", "start_date",
        "lgbtq", "lgbtq:signed", "diet:vegetarian", "drive_through", "payment:cash", "payment:cards", "cuisine:barbecue", "description")


def fetch() -> dict:
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def state_of(tags: dict, lat: float, lon: float = None) -> str:
    s = (tags.get("addr:state") or "").strip().upper()
    if s in ("NC", "NORTH CAROLINA"):
        return "NC"
    if s in ("SC", "SOUTH CAROLINA"):
        return "SC"
    # The two states share a long east-west border near 35°N in the east and ~35.2°N in the west.
    # A postcode is a better tell than latitude: 27xxx/28xxx are NC, 29xxx is SC.
    pc = (tags.get("addr:postcode") or "")[:2]
    if pc in ("27", "28"):
        return "NC"
    if pc == "29":
        return "SC"
    if lon is not None:
        return state_by_geo(lat, lon) or "unknown"
    return "NC" if lat >= 35.2 else "SC" if lat < 34.8 else "unknown"


def main(dry=False) -> int:
    t0 = time.time()
    raw = fetch()
    els = raw.get("elements", [])
    rows = []
    seen = set()
    for e in els:
        tags = e.get("tags", {})
        if not tags.get("name"):
            continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        st = state_of(tags, lat, lon)
        base = slugify(tags["name"]) or "unnamed"
        slug = base
        n = 2
        while slug in seen:
            city = slugify(tags.get("addr:city", "")) or f"{lat:.3f}-{lon:.3f}".replace(".", "")
            slug = f"{base}-{city}" if n == 2 and city else f"{base}-{n}"
            n += 1
        seen.add(slug)
        rows.append({
            "osm_id": f"{e['type']}/{e['id']}", "slug": slug, "name": tags["name"], "state": st,
            "lat": round(lat, 5), "lon": round(lon, 5),
            "tags": {k: v for k, v in tags.items() if k in KEEP},
        })
    rows.sort(key=lambda r: (r["state"], r["name"].lower()))
    print(f"{len(els)} elements → {len(rows)} named places · NC {sum(1 for r in rows if r['state']=='NC')} · "
          f"SC {sum(1 for r in rows if r['state']=='SC')} · unknown {sum(1 for r in rows if r['state']=='unknown')} · {time.time()-t0:.1f}s")
    if dry:
        return 0
    if OUT.exists():
        prev = len(jload(OUT).get("places", []))
        if rows and len(rows) < prev * 0.75:
            print(f"refused: previous harvest had {prev} places, this one {len(rows)} (>25% shrink). Delete {OUT} to force.")
            return 3
    if not rows:
        print("refused: zero places is a valid Overpass reply and would be cached as absence")
        return 3
    jdump({
        "source": "OpenStreetMap contributors", "license": "ODbL 1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "endpoint": ENDPOINT, "query": QUERY,
        "osm_base": raw.get("osm3s", {}).get("timestamp_osm_base"), "count": len(rows), "places": rows,
    }, OUT)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__" and "--towns" not in sys.argv:
    sys.exit(main(dry="--dry" in sys.argv))


# ------------------------------------------------------------------ towns and counties
# OSM rows without addr:city (a third of them) cannot be grouped by town. Nominatim's
# reverse geocoder fills town and county from the same OSM data, one request per
# second as its usage policy asks, cached by osm_id so a re-run fetches only new rows.
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
TOWNS = HARVEST / "osm-towns.json"


def towns(sleep=1.1) -> int:
    if not OUT.exists():
        print("no harvest yet")
        return 1
    h = jload(OUT)
    cache = jload(TOWNS) if TOWNS.exists() else {"source": "Nominatim reverse geocoding of OpenStreetMap data, ODbL", "rows": {}}
    rows = cache["rows"]
    n = 0
    for p in h["places"]:
        if p["osm_id"] in rows:
            continue
        q = urllib.parse.urlencode({"lat": p["lat"], "lon": p["lon"], "format": "jsonv2", "zoom": 10, "addressdetails": 1})
        req = urllib.request.Request(f"{NOMINATIM}?{q}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"  {p['name']}: {e}")
            time.sleep(sleep)
            continue
        a = d.get("address", {})
        town = a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or a.get("municipality") or ""
        county = (a.get("county") or "").replace(" County", "")
        rows[p["osm_id"]] = {"town": town, "county": county, "state": a.get("state", ""), "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        n += 1
        if n % 25 == 0:
            jdump(cache, TOWNS)
            print(f"  {n} geocoded…", flush=True)
        time.sleep(sleep)
    jdump(cache, TOWNS)
    print(f"towns: {n} new, {len(rows)} cached → {TOWNS}")
    return 0


if __name__ == "__main__" and "--towns" in sys.argv:
    sys.exit(towns())
