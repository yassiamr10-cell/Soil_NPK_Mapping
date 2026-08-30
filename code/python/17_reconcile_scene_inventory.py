# -*- coding: utf-8 -*-
"""
STEP 17 - Adopt the authoritative Earth Engine scene inventory.

The inventory exported by gee_01_metadata_report.js is what actually built the
composites, so it supersedes the STAC reconstruction produced by step 14. This
script ingests the two exported CSVs, reconciles them against the STAC estimate,
and rewrites 14_scene_inventory_used.csv / 14_composite_summary.csv so that every
downstream document quotes the Earth Engine numbers.
"""
import os, glob
import pandas as pd
import numpy as np

FINAL = r"d:\Doctorat\article1\outputs_fast\FINAL"
RES = os.path.join(FINAL, "results")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 25)

gee = pd.concat([pd.read_csv(f) for f in
                 sorted(glob.glob(os.path.join(RES, "gee_S2_scene_inventory_*.csv")))],
                ignore_index=True)
gee["date"] = gee.sensing_utc.str[:10]
gee["orbit"] = gee.orbit.astype(int)
gee["baseline"] = gee.baseline.astype(str)
gee = gee.sort_values(["composite", "sensing_utc", "mgrs_tile"]).reset_index(drop=True)

print("=" * 100)
print("AUTHORITATIVE EARTH ENGINE SCENE INVENTORY")
print("=" * 100)
for tag in ["2024_11", "2025_01"]:
    s = gee[gee.composite == tag]
    print(f"\n--- {tag} ---")
    print(f"  scenes            : {len(s)}")
    print(f"  distinct dates    : {s.date.nunique()}  ({s.date.min()} .. {s.date.max()})")
    print(f"  MGRS tiles        : {sorted(s.mgrs_tile.unique())}")
    print(f"  relative orbits   : {sorted(s.orbit.unique())}")
    print(f"  platforms         : {sorted(s.platform.unique())}")
    print(f"  baselines         : {sorted(s.baseline.unique())}")
    print(f"  BOA_ADD_OFFSET_B2 : {sorted(s.boa_offset_B2.unique())}")
    print(f"  cloud %%           : {s.cloud_pct.min():.4f} .. {s.cloud_pct.max():.3f} "
          f"(median {s.cloud_pct.median():.3f})")
    print(f"  nodata %%          : {s.nodata_pct.min():.2f} .. {s.nodata_pct.max():.2f} "
          f"(median {s.nodata_pct.median():.2f})")
    print(f"  solar zenith      : {s.sun_zenith.min():.1f} .. {s.sun_zenith.max():.1f} deg")
    print(f"  scenes per tile   : {s.mgrs_tile.value_counts().sort_index().to_dict()}")

# ---- reconcile against the STAC reconstruction -------------------------
print("\n" + "=" * 100)
print("RECONCILIATION WITH THE STAC RECONSTRUCTION (step 14)")
print("=" * 100)
stac_path = os.path.join(RES, "14_scene_inventory_used.csv")
if os.path.exists(stac_path):
    stac = pd.read_csv(stac_path)
    stac["date"] = stac.datetime.str[:10]
    for tag in ["2024_11", "2025_01"]:
        g, s = gee[gee.composite == tag], stac[stac.composite == tag]
        gk = set(zip(g.date, g.mgrs_tile))
        sk = set(zip(s.date, s.mgrs_tile))
        print(f"\n  {tag}: Earth Engine {len(g)} scenes, STAC {len(s)} rows")
        print(f"     same date+tile combinations : {len(gk & sk)}")
        dup = len(s) - len(sk)
        if dup:
            print(f"     duplicate rows in STAC      : {dup} "
                  f"(reprocessed granules listed twice)")
        only_s = sk - gk
        only_g = gk - sk
        if only_s:
            print(f"     in STAC but not Earth Engine: {sorted(only_s)}")
        if only_g:
            print(f"     in Earth Engine but not STAC: {sorted(only_g)}")
    print("\n  The Earth Engine export is authoritative: it is the collection that was "
          "actually\n  reduced to the median composites. The STAC listing double-counted "
          "granules that had\n  been reprocessed under a later baseline date.")

# ---- rewrite the canonical files ---------------------------------------
out = gee.rename(columns={"sensing_utc": "datetime"})[
    ["composite", "asset_id", "product_id", "granule_id", "datetime", "mgrs_tile",
     "cloud_pct", "cloud_land_pct", "shadow_pct", "nodata_pct", "platform",
     "baseline", "orbit", "sun_zenith", "sun_azimuth", "boa_offset_B2"]]
out.to_csv(os.path.join(RES, "14_scene_inventory_used.csv"), index=False)

summ = (gee.groupby("composite")
        .agg(n_scenes=("asset_id", "size"),
             n_tiles=("mgrs_tile", "nunique"),
             n_dates=("date", "nunique"),
             n_orbits=("orbit", "nunique"),
             cloud_min=("cloud_pct", "min"),
             cloud_max=("cloud_pct", "max"),
             cloud_median=("cloud_pct", "median"),
             date_first=("date", "min"),
             date_last=("date", "max")).reset_index())
summ.to_csv(os.path.join(RES, "14_composite_summary.csv"), index=False)

print("\n" + "=" * 100)
print("COMPOSITE SUMMARY  (written to 14_composite_summary.csv)")
print("=" * 100)
print(summ.to_string(index=False))

# ---- a note worth putting in the manuscript ----------------------------
print("\n" + "=" * 100)
print("POINTS WORTH STATING IN SECTION 3.2.1")
print("=" * 100)
print(f"  * {len(gee)} scenes total: {int(summ.iloc[0].n_scenes)} in November 2024, "
      f"{int(summ.iloc[1].n_scenes)} in January 2025.")
print(f"  * Four MGRS tiles and two relative orbits (94, 137) per composite, so the "
      f"median\n    reduction also performs the tile mosaic.")
print(f"  * Every scene carries processing baseline 05.11 and BOA_ADD_OFFSET = -1000; "
      f"the\n    harmonized collection applies that offset, so divide(10000) yields "
      f"true reflectance.")
print(f"  * Sentinel-2C contributes one scene to the January composite "
      f"(27 Jan 2025, tile 29SQR),\n    alongside 2A and 2B.")
nod = gee[gee.nodata_pct > 30]
print(f"  * {len(nod)} scenes have more than 30 % no-data over the AOI because the tile "
      f"only\n    partially covers the district; the median composite fills these from "
      f"other tiles.")
print(f"  * Solar zenith ranges {gee.sun_zenith.min():.1f}-{gee.sun_zenith.max():.1f} deg "
      f"across the two months, a\n    difference in illumination geometry between the "
      f"composites worth acknowledging.")
print("\nSTEP 17 complete.")
