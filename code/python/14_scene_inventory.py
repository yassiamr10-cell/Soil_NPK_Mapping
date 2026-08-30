# -*- coding: utf-8 -*-
"""
STEP 14 - Recover the exact Sentinel-2 scene inventory behind the two monthly
median composites, from the public STAC catalogue.

The Earth Engine export script (gee_redownload_B7_2025_01.js) shows the actual
pipeline was:
    collection  COPERNICUS/S2_SR_HARMONIZED
    AOI         polygon -7.152655..-6.309455 E, 32.143829..32.619321 N
    filter      CLOUDY_PIXEL_PERCENTAGE < 40
    mask        SCL classes 3, 8, 9, 10, 11 removed
    scaling     divide by 10000 after masking
    composite   MEDIAN of all surviving scenes in the calendar month
    export      10 m, EPSG:4326, clipped to the AOI

This script reproduces the scene selection so the manuscript can report exactly
which acquisitions contributed to each composite.
"""
import json, os, urllib.request, urllib.error
import pandas as pd

FINAL = r"d:\Doctorat\article1\outputs_fast\FINAL"
RES = os.path.join(FINAL, "results")

# AOI exactly as in the Earth Engine script
W, S, E, N = -7.152655325374058, 32.14382853284281, -6.309454641780308, 32.61932132661444
CLOUD_MAX = 40.0
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
UA = {"User-Agent": "AmroussEtAl/1.0", "Content-Type": "application/json"}

MONTHS = [("2024_11", "2024-11-01T00:00:00Z/2024-11-30T23:59:59Z"),
          ("2025_01", "2025-01-01T00:00:00Z/2025-01-31T23:59:59Z")]


def search(dt):
    items, token = [], None
    while True:
        body = {"collections": ["sentinel-2-l2a"], "bbox": [W, S, E, N],
                "datetime": dt, "limit": 100}
        if token:
            body["token"] = token
        req = urllib.request.Request(STAC, data=json.dumps(body).encode(),
                                     headers=UA, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            js = json.load(r)
        items.extend(js.get("features", []))
        nxt = [l for l in js.get("links", []) if l.get("rel") == "next"]
        if not nxt:
            break
        token = nxt[0].get("body", {}).get("token")
        if not token:
            break
    return items


rows = []
for tag, dt in MONTHS:
    try:
        items = search(dt)
    except Exception as e:
        print("STAC query failed for", tag, ":", e)
        items = []
    print(f"{tag}: {len(items)} scenes intersect the AOI")
    for it in items:
        p = it["properties"]
        rows.append(dict(
            composite=tag,
            scene_id=it["id"],
            product_id=p.get("s2:product_uri", "").replace(".SAFE", ""),
            datetime=p.get("datetime", "")[:19].replace("T", " "),
            mgrs_tile=(f"{p.get('s2:mgrs_tile','')}"
                       or f"{p.get('mgrs:utm_zone','')}{p.get('mgrs:latitude_band','')}"
                          f"{p.get('mgrs:grid_square','')}"),
            cloud_pct=round(float(p.get("eo:cloud_cover", float("nan"))), 3),
            platform=p.get("platform", ""),
            baseline=p.get("s2:processing_baseline", ""),
            orbit=p.get("sat:relative_orbit", ""),
            nodata_pct=round(float(p.get("s2:nodata_pixel_percentage", float("nan"))), 2),
        ))

d = pd.DataFrame(rows)
if len(d) == 0:
    raise SystemExit("no scenes returned - check network access")

d["used"] = d.cloud_pct < CLOUD_MAX
d = d.sort_values(["composite", "datetime", "mgrs_tile"]).reset_index(drop=True)
d.to_csv(os.path.join(RES, "14_scene_inventory_full.csv"), index=False)

used = d[d.used].copy()
used.to_csv(os.path.join(RES, "14_scene_inventory_used.csv"), index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
print("\n" + "=" * 104)
print("SCENE INVENTORY  (AOI %.4f..%.4f E, %.4f..%.4f N)" % (W, E, S, N))
print("=" * 104)
for tag, _ in MONTHS:
    sub = d[d.composite == tag]
    u = sub[sub.used]
    print(f"\n--- {tag} composite ---")
    print(f"  scenes intersecting AOI : {len(sub)}")
    print(f"  scenes with cloud < {CLOUD_MAX:.0f}%%: {len(u)}")
    print(f"  distinct MGRS tiles used: {sorted(u.mgrs_tile.unique())}")
    print(f"  distinct dates used     : {sorted(set(x[:10] for x in u.datetime))}")
    print(f"  cloud cover of used     : {u.cloud_pct.min():.2f}% .. {u.cloud_pct.max():.2f}% "
          f"(median {u.cloud_pct.median():.2f}%)")
    print(f"  platforms               : {sorted(u.platform.unique())}")
    print(f"  processing baselines    : {sorted(set(str(b) for b in u.baseline.unique()))}")

print("\n" + "=" * 104)
print("SCENES CONTRIBUTING TO EACH COMPOSITE (cloud < 40%)")
print("=" * 104)
print(used[["composite", "datetime", "mgrs_tile", "cloud_pct", "platform",
            "baseline", "orbit"]].to_string(index=False))

summ = (used.groupby("composite")
        .agg(n_scenes=("scene_id", "size"),
             n_tiles=("mgrs_tile", "nunique"),
             n_dates=("datetime", lambda s: len(set(x[:10] for x in s))),
             cloud_min=("cloud_pct", "min"), cloud_max=("cloud_pct", "max"),
             cloud_median=("cloud_pct", "median")).reset_index())
summ.to_csv(os.path.join(RES, "14_composite_summary.csv"), index=False)
print("\n" + summ.to_string(index=False))
print(f"\nwritten to {RES}")
