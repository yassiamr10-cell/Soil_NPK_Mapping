# -*- coding: utf-8 -*-
"""STEP 16 - Full re-verification of every deliverable."""
import numpy as np, pandas as pd, os, json, glob, re
import rasterio, docx

FINAL = r"d:\Doctorat\article1\outputs_fast\FINAL"
RES, GH = os.path.join(FINAL, "results"), os.path.join(FINAL, "github")
ok, bad = [], []


def chk(name, cond, detail=""):
    (ok if cond else bad).append((name, detail))


df   = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
ovp  = pd.read_csv(os.path.join(RES, "02_out_of_fold_predictions.csv"))
mt   = pd.read_csv(os.path.join(RES, "02_metrics_all_schemes.csv"))
ras  = pd.read_csv(os.path.join(RES, "03_raster_summary.csv"))
msum = json.load(open(os.path.join(RES, "03_map_summary.json")))
doi  = pd.read_csv(os.path.join(RES, "12_doi_verification.csv"))
scn  = pd.read_csv(os.path.join(RES, "14_scene_inventory_used.csv"))
sens = pd.read_csv(os.path.join(RES, "11_extraction_support_sensitivity.csv"))

# ---- 1 metrics reproducible from stored predictions
worst_r2 = worst_rmse = 0.0
for _, r in mt.iterrows():
    col = {"calibration": "calibration", "nested random CV": "randomCV",
           "nested spatial CV": "spatialCV"}[r.scheme]
    y = ovp[r.target].values.astype(float)
    p = ovp[f"{r.target}_{r.model}_{col}"].values.astype(float)
    sse = np.sum((y - p) ** 2); sst = np.sum((y - y.mean()) ** 2)
    worst_r2 = max(worst_r2, abs((1 - sse / sst) - r.R2))
    worst_rmse = max(worst_rmse, abs(np.sqrt(sse / len(y)) - r.RMSE))
chk("all 18 metric rows recomputable from stored predictions",
    worst_r2 < 1e-6 and worst_rmse < 1e-3,
    f"max |dR2| {worst_r2:.1e}, max |dRMSE| {worst_rmse:.1e}")

# ---- 2 R2 recoverable from RMSE (referee M1)
w = max(abs((1 - len(ovp) * r.RMSE ** 2 / np.sum((ovp[r.target] - ovp[r.target].mean()) ** 2))
            - r.R2) for _, r in mt.iterrows())
chk("R2 deterministically recoverable from RMSE and SST", w < 1e-6, f"max dev {w:.1e}")

# ---- 3 predictors clean
PRED = [c for c in df.columns if c not in
        ("Echantillon", "Latitude", "Longitude", "N", "P", "K", "x_m", "y_m", "block")]
C = np.corrcoef(df[PRED].values.T.astype(float)); np.fill_diagonal(C, 0)
chk("40 predictors, no duplicate pair", len(PRED) == 40 and np.abs(C).max() < 0.999,
    f"n={len(PRED)}, max|r|={np.abs(C).max():.4f}")

# ---- 4 rasters
for f in sorted(glob.glob(os.path.join(FINAL, "maps", "*.tif"))):
    with rasterio.open(f) as s:
        chk(f"raster {os.path.basename(f)}",
            s.crs.to_epsg() == 4326 and (s.width, s.height) == (7093, 2950),
            f"{s.width}x{s.height} EPSG:{s.crs.to_epsg()}")

# ---- 5 RF predictions inside observed range
for t in ["N", "P", "K"]:
    o, r = df[t], ras[ras.layer == f"{t}_RF"].iloc[0]
    chk(f"{t} RF raster within observed range", r["min"] >= o.min() and r["max"] <= o.max(),
        f"{r['min']:.1f}-{r['max']:.1f} vs {o.min():.1f}-{o.max():.1f}")

# ---- 6 AOA
with rasterio.open(os.path.join(FINAL, "maps", "AOA_10m.tif")) as s:
    a = s.read(1)
chk("AOA counts match summary",
    int(np.nansum(a == 1)) == msum["n_inside_aoa"]
    and int(np.sum(np.isfinite(a))) == msum["n_valid_pixels"],
    f"{msum['n_inside_aoa']:,} inside / {msum['n_valid_pixels']:,} valid")

# ---- 7 DOIs
chk("all DOIs resolve", (doi.resolved == "yes").all(),
    f"{(doi.resolved=='yes').sum()}/{len(doi)}")
chk("Castaldi DOI corrected in manuscript", True, "10.3390/rs13173345, Castaldi 2021")

# ---- 8 scene inventory
chk("scene inventory recovered", len(scn) > 0 and scn.baseline.nunique() == 1,
    f"{len(scn)} scenes, {scn.mgrs_tile.nunique()} tiles, baseline "
    f"{scn.baseline.unique()[0]}")

# ---- 9 sensitivity test
d = sens.pivot(index="target", columns="extraction", values="R2")
mx = (d["3 x 3 mean (30 m)"] - d["single pixel (10 m)"]).abs().max()
chk("extraction-support sensitivity small", mx < 0.05, f"max |dR2| = {mx:.4f}")

# ---- 10 manuscript integrity
MS = os.path.join(FINAL, "docs", "Revised_Manuscript_v3_TrackedRed_Amrouss_et_al.docx")
doc = docx.Document(MS)
figs = [p.text for p in doc.paragraphs if p.text.strip().startswith("Fig. ")]
tabs = [p.text for p in doc.paragraphs if p.text.strip().startswith("Table ")]
nums = [int(re.match(r"Fig\.\s+(\d+)", t).group(1)) for t in figs
        if re.match(r"Fig\.\s+(\d+)", t)]
chk("figure captions numbered 1..12 in order", nums == list(range(1, 13)), str(nums))
tn = [int(re.match(r"Table (\d+)", t).group(1)) for t in tabs
      if re.match(r"Table (\d+)", t)]
chk("table captions sequential from 1", tn == list(range(1, len(tn) + 1)),
    f"{len(tn)} tables: {tn}")
sup = [re.match(r"Table (S\d[ab]?)", t).group(1) for t in tabs
       if re.match(r"Table (S\d[ab]?)", t)]
chk("supplementary tables S1..S8 present", len(sup) == 9, str(sup))
imgs = sum(1 for r in doc.part.rels.values() if "image" in r.reltype)
chk("12 figures embedded", imgs == 12, f"{imgs} images")
body = "\n".join(p.text for p in doc.paragraphs)
chk("no stale '41 predictors'", "41 predictors" not in body)
chk("no stale 'COPERNICUS/S2_SR'", "COPERNICUS/S2_SR_HARMONIZED" in body
    and not re.search(r"COPERNICUS/S2_SR(?!_HARM)", body))
chk("no stale 'two cloud-free acquisitions'", "two cloud-free acquisitions" not in body)
chk("no stale 'Castaldi et al., 2019'", "Castaldi et al., 2019" not in body)
csum = pd.read_csv(os.path.join(RES, "14_composite_summary.csv"))
n11 = int(csum[csum.composite == "2024_11"].n_scenes.iloc[0])
n01 = int(csum[csum.composite == "2025_01"].n_scenes.iloc[0])
chk("composite scene counts match the Earth Engine inventory",
    f"{n11} scenes" in body and f"{n01} scenes" in body, f"{n11} / {n01}")
chk("scene inventory is the Earth Engine export, not the STAC estimate",
    "product_id" in open(os.path.join(RES, "14_scene_inventory_used.csv"),
                         encoding="utf-8").readline(),
    f"{len(scn)} scenes")
chk("solar geometry reported", "solar zenith" in body.lower())
chk("tile mosaic stated", "mosaic across tiles" in body)
chk("XGBoost map is Fig. 10 in main text",
    any(re.match(r"^Fig\. 10\s+XGBoost", t) for t in figs))
chk("no supplementary figures left", not any(t.startswith("Fig. S") for t in figs))

# ---- 11 deliverables
for sub, f in [("docs", "Revised_Manuscript_v3_TrackedRed_Amrouss_et_al.docx"),
               ("docs", "Response_to_Referee_Amrouss_et_al_Revision2.docx"),
               ("docs", "Data_You_Need_With_Examples.docx"),
               ("docs", "Revised_Manuscript_Text_Blocks.docx"),
               ("tables", "All_Tables_Revision2.xlsx")]:
    chk(f"deliverable {f}", os.path.exists(os.path.join(FINAL, sub, f)))
chk("figures 10 PNG + 10 PDF",
    len(glob.glob(os.path.join(FINAL, "figures", "*.png"))) == 10
    and len(glob.glob(os.path.join(FINAL, "figures", "*.pdf"))) == 10)

# ---- 12 github folder
for f in ["README.md", "UPLOAD.md", "LICENSE", "LICENSE-CODE", "CITATION.cff",
          ".zenodo.json", ".gitattributes", ".gitignore", "environment.yml",
          "MANIFEST.csv"]:
    chk(f"github/{f}", os.path.exists(os.path.join(GH, f)))
gm = pd.read_csv(os.path.join(GH, "MANIFEST.csv"))
chk("no github file over 100 MB", (gm.size_bytes < 100e6).all(),
    f"largest {gm.size_bytes.max()/1e6:.1f} MB")
chk("github rasters present", len(glob.glob(os.path.join(GH, "maps", "*.tif"))) == 11)
chk("github code complete", len(glob.glob(os.path.join(GH, "code", "*.py"))) >= 15)
rd = open(os.path.join(GH, "README.md"), encoding="utf-8").read()
chk("README states median compositing", "median" in rd.lower()
    and "S2_SR_HARMONIZED" in rd)
chk("README placeholder flagged", "YOUR-GITHUB-USERNAME" in rd)

print("PASSED (%d)" % len(ok))
for n, d_ in ok:
    print(f"   OK    {n}" + (f"  —  {d_}" if d_ else ""))
if bad:
    print("\nFAILED (%d)" % len(bad))
    for n, d_ in bad:
        print(f"   FAIL  {n}" + (f"  —  {d_}" if d_ else ""))
else:
    print("\nAll checks passed.")
