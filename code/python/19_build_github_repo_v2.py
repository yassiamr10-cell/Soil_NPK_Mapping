# -*- coding: utf-8 -*-
"""
STEP 19 - Assemble the public GitHub repository as a research compendium.

Layout
    code/earthengine   the four Earth Engine scripts
    code/python        the numbered analysis pipeline
    data/soil          observations and the analysis-ready predictor matrix
    data/spatial       district boundary and the cross-validation block design
    data/sentinel2     scene inventory of both monthly composites
    outputs/figures    every manuscript figure, PNG and vector PDF
    outputs/tables     every manuscript and supplementary table
    outputs/results    metrics, out-of-fold predictions, diagnostics
    outputs/maps       README only; the rasters live on Zenodo

Decisions taken here
  * The 10 m GeoTIFFs are NOT tracked in Git. They are 271 MB and would consume
    GitHub's free LFS bandwidth in about three clones. They are uploaded to the
    Zenodo record instead, which is where the citable DOI lives.
  * The manuscript and the response letter are NOT published. The response letter
    quotes the referee report, which most journals treat as confidential.
"""
import os, shutil, glob, hashlib, json, textwrap
import pandas as pd

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
GH    = os.path.join(FINAL, "github")

REPO = "beni-moussa-npk-mapping"
USER = "YOUR-GITHUB-USERNAME"

if os.path.isdir(GH):
    shutil.rmtree(GH)
DIRS = ["code/earthengine", "code/python", "data/soil", "data/spatial",
        "data/sentinel2", "outputs/figures", "outputs/tables", "outputs/results",
        "outputs/maps"]
for sub in DIRS:
    os.makedirs(os.path.join(GH, sub), exist_ok=True)

s01  = json.load(open(os.path.join(RES, "01_summary.json")))
msum = json.load(open(os.path.join(RES, "03_map_summary.json")))
csum = pd.read_csv(os.path.join(RES, "14_composite_summary.csv"))
mt   = pd.read_csv(os.path.join(RES, "02_metrics_all_schemes.csv"))
ds   = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
c11 = csum[csum.composite == "2024_11"].iloc[0]
c01 = csum[csum.composite == "2025_01"].iloc[0]


def sp(t, m):
    r = mt[(mt.target == t) & (mt.model == m) & (mt.scheme == "nested spatial CV")]
    return r.iloc[0]


# ------------------------------------------------------------------- copy
COPY = []
# earth engine
for src, dst in [
    ("gee_00_original_as_submitted.js", "00_original_as_submitted.js"),
    ("gee_01_metadata_report.js",       "01_metadata_report.js"),
    ("gee_02_export_covariates_CORRECTED.js", "02_export_covariates.js"),
]:
    COPY.append((os.path.join(FINAL, "code", src), f"code/earthengine/{dst}"))
COPY.append((r"d:\Doctorat\article1\gee_redownload_B7_2025_01.js",
             "code/earthengine/03_reexport_B7_january.js"))
# python pipeline
for f in sorted(glob.glob(os.path.join(FINAL, "code", "*.py"))):
    COPY.append((f, "code/python/" + os.path.basename(f)))
# data
for f, sub in [
    ("01_analysis_ready_dataset.csv", "data/soil"),
    ("11_dataset_3x3_neighbourhood.csv", "data/soil"),
    ("01_predictor_inventory.csv", "data/soil"),
    ("01_block_design.csv", "data/spatial"),
    ("14_scene_inventory_used.csv", "data/sentinel2"),
    ("14_scene_inventory_full.csv", "data/sentinel2"),
    ("gee_S2_scene_inventory_2024_11.csv", "data/sentinel2"),
    ("gee_S2_scene_inventory_2025_01.csv", "data/sentinel2"),
]:
    COPY.append((os.path.join(RES, f), f"{sub}/{f}"))
for ext in ("shp", "shx", "dbf", "prj", "cpg"):
    COPY.append((rf"d:\Doctorat\article1\Beni_Moussa.{ext}",
                 f"data/spatial/Beni_Moussa.{ext}"))
# outputs
for f in sorted(glob.glob(os.path.join(FINAL, "figures", "*"))):
    COPY.append((f, "outputs/figures/" + os.path.basename(f)))
for f in sorted(glob.glob(os.path.join(FINAL, "tables", "*"))):
    COPY.append((f, "outputs/tables/" + os.path.basename(f)))
for f in sorted(glob.glob(os.path.join(RES, "*"))):
    b = os.path.basename(f)
    if b.startswith(("01_analysis", "01_predictor", "01_block", "14_scene",
                     "gee_S2_scene")) or b.endswith("_run_log.txt"):
        continue
    COPY.append((f, "outputs/results/" + b))

rows = []
for src, rel in COPY:
    if not os.path.exists(src):
        print("  missing (skipped):", os.path.basename(src)); continue
    dst = os.path.join(GH, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.splitext(src)[1].lower() in (".txt", ".md", ".csv", ".json"):
        # console logs redirected by PowerShell carry a UTF-8 BOM; strip it and
        # normalise line endings so the repository is clean text throughout
        raw = open(src, "rb").read()
        for enc in ("utf-8-sig", "utf-16", "cp1252"):
            try:
                txt = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            txt = raw.decode("utf-8", errors="replace")
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt.replace("\r\n", "\n"))
    else:
        shutil.copy2(src, dst)
    rows.append(dict(path=rel.replace("\\", "/"), size_bytes=os.path.getsize(dst),
                     md5=hashlib.md5(open(dst, "rb").read()).hexdigest()))
man = pd.DataFrame(rows).sort_values("path")
man.to_csv(os.path.join(GH, "MANIFEST.csv"), index=False)


def W(name, text):
    p = os.path.join(GH, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(textwrap.dedent(text).lstrip("\n"))


# =========================================================== root README
W("README.md", f"""
# Soil macronutrient mapping in the Beni Moussa irrigated district, Morocco

Data, code and outputs for:

> Amrouss, Y., Arioua, A., Elhamdouni, D., El Baghdadi, M., Barakat, A., El Atiq, J.,
> Ouchkir, I., Bimouhen, M., Nait-taleb, O., & Hilali, A.
> *High-resolution mapping of soil macronutrients in a semi-arid climate (Morocco)
> using Sentinel-2 data and machine learning models.*
> Submitted to **Environmental Monitoring and Assessment**.

[![DOI](https://zenodo.org/badge/DOI/PENDING.svg)](https://doi.org/PENDING)
[![License: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-blue.svg)](LICENSE)
[![License: MIT](https://img.shields.io/badge/Code-MIT-green.svg)](LICENSE-CODE)

---

## What this is

110 composite topsoil samples (0–20 cm) from the Beni Moussa irrigated district
(Tadla Plain, Morocco), collected between November 2024 and January 2025, are used
to predict total nitrogen, Olsen phosphorus and exchangeable potassium from
Sentinel-2 surface reflectance.

Performance is measured under **nested spatial block cross-validation**: every
tuning decision is taken inside an inner loop on the training blocks, and all
reported statistics come from untouched outer folds.

| Nutrient | R² | RMSE (mg kg⁻¹) |
|---|---|---|
| Total N | {sp('N','RF').R2:.3f} | {sp('N','RF').RMSE:,.1f} |
| Olsen P | {sp('P','RF').R2:.3f} | {sp('P','RF').RMSE:.2f} |
| Exchangeable K | {sp('K','RF').R2:.3f} | {sp('K','RF').RMSE:.2f} |

Random Forest and XGBoost are **statistically indistinguishable** here; for
potassium a ridge regression on the same predictors does at least as well. Predictive
importance is concentrated in raw near-infrared and red-edge reflectance from the
November composite, which indicates the models track canopy condition rather than
soil composition directly. The maps are reconnaissance products, delivered with local
uncertainty and an explicit area of applicability, and are **not** a basis for
variable-rate fertiliser prescription.

---

## Repository layout

```
code/
  earthengine/   00  the export used for the FIRST submission - archived, do not run
                 01  metadata report: scene inventory, cloud, tiles, composite depth
                 02  corrected covariate export - USE THIS ONE
                 03  single-band re-export of B7 for January
  python/        01-19  the analysis pipeline, in execution order

data/
  soil/          110 observations with coordinates and {s01['n_predictors']} predictors,
                 the 3x3 extraction variant, and the predictor inventory
  spatial/       district boundary shapefile and the cross-validation block design
  sentinel2/     inventory of the {int(c11.n_scenes)+int(c01.n_scenes)} scenes behind
                 the two monthly composites

outputs/
  figures/       all 12 manuscript figures, 400 dpi PNG and vector PDF
  tables/        all 13 manuscript and 9 supplementary tables
  results/       metrics, out-of-fold predictions, importance, diagnostics
  maps/          README only - the 10 m rasters are on Zenodo (see below)
```

Start with [`data/README.md`](data/README.md) for the data dictionary and
[`code/README.md`](code/README.md) for how to run the pipeline.

```bash
git clone https://github.com/{USER}/{REPO}.git
cd {REPO}
```

---

## The 10 m rasters

Eleven GeoTIFFs (predictions, uncertainty, dissimilarity index, applicability mask
for N, P and K) total 271 MB. They are **not** tracked in Git — they would exhaust
GitHub's free LFS bandwidth in about three clones. They are attached to the Zenodo
record instead, and can also be regenerated exactly by running
`code/python/03_predict_10m_maps.py`. See [`outputs/maps/README.md`](outputs/maps/README.md).

---

## Reproducing the analysis

```bash
conda env create -f environment.yml     # or: pip install -r requirements.txt
conda activate benimoussa
python run_all.py
```

`run_all.py` prints the pipeline in order and checks that the inputs each step needs
are present. Steps 03 and 11 additionally require the 20 Sentinel-2 band rasters
(10 bands × 2 monthly composites) at 10 m; regenerate them with
`code/earthengine/02_export_covariates.js`.

Every script has a `BASE` path constant at the top pointing at the directory the
analysis was originally run in. Edit that one line, or place the repository at the
same path, before running.

---

## How the covariates were built

| Item | Value |
|---|---|
| Collection | `COPERNICUS/S2_SR_HARMONIZED` |
| Area of interest | 7.152655° W – 6.309455° W, 32.143829° N – 32.619321° N |
| Scene filter | `CLOUDY_PIXEL_PERCENTAGE < 40` |
| SCL classes masked | 3 cloud shadow, 8 cloud medium, 9 cloud high, 10 thin cirrus, 11 snow/ice |
| Scaling | divide by 10 000 after masking |
| Compositing | per-pixel **median** over each calendar month |
| November 2024 | {int(c11.n_scenes)} scenes, {int(c11.n_dates)} dates, cloud {c11.cloud_min:.2f}–{c11.cloud_max:.2f} % |
| January 2025 | {int(c01.n_scenes)} scenes, {int(c01.n_dates)} dates, cloud {c01.cloud_min:.3f}–{c01.cloud_max:.2f} % |
| MGRS tiles | 29SPR, 29SPS, 29SQR, 29SQS (two relative orbits, 94 and 137) |
| Processing baseline | 05.11, `BOA_ADD_OFFSET = −1000`, applied by the harmonized collection |
| Export | 10 m, EPSG:4326, clipped to the AOI |

Full inventory: [`data/sentinel2/14_scene_inventory_used.csv`](data/sentinel2/14_scene_inventory_used.csv).

---

## Analysis summary

| Item | Value |
|---|---|
| Observations | 110 composite topsoil samples, 0–20 cm, three analytical replicates each |
| Predictors | {s01['n_predictors']} (10 bands + 10 indices × 2 composites) |
| Duplicate predictor pairs | 0 (max abs. correlation 0.998; numerical rank {s01['numerical_rank']}) |
| Primary validation | nested CV, leave-one-block-out over {s01['n_blocks']} spatial blocks |
| Inner loop | GroupKFold(5) on training blocks only |
| Fold sizes | {', '.join(str(n) for n in s01['fold_sizes'])} |
| Median block separation | {s01['median_block_separation_km']:.2f} km |
| Prediction grid | 10 m, {msum['n_valid_pixels']:,} valid pixels, {msum['mapped_area_ha']:,.0f} ha |
| Raster CRS | EPSG:4326; figures drawn in EPSG:26191 (Merchich / Nord Maroc) |
| Area of applicability | {msum['pct_inside_aoa']:.1f} % ({msum['ha_inside_aoa']:,.0f} ha) inside |
| Random seed | 42 throughout |

---

## Corrections in this version

Three predictor-construction errors in the first submission were found during audit
and are corrected here. Both the original and the corrected Earth Engine scripts are
included so the errors can be verified directly:

```js
// 00_original_as_submitted.js        // 02_export_covariates.js
SI    = (B11-B8)/(B11+B8)  // = -NDMI  SI    = B11 * B12
VSSI  = (B11-B3)/(B11+B3)  // = -NDSI  VSSI  = 2*B3 - 5*(B4+B8)
MNDWI = (B3-B12)/(B3+B12)  // wrong    MNDWI = (B3-B11)/(B3+B11)
NDSI  = (B3-B11)/(B3+B11)  // = MNDWI  (removed, it duplicated MNDWI)
```

Two of the 42 original columns were therefore sign-flipped duplicates of two others.
The predictor count is corrected from 41 to {s01['n_predictors']}.

A bibliographic error was also found: the Castaldi reference in the first submission
cited DOI `10.3390/rs11242924`, which resolves to a radar-tomography paper by Monteith
et al. The intended article is Castaldi (2021), *Remote Sensing* **13**, 3345,
`10.3390/rs13173345`. All 46 DOIs are verified in
[`outputs/results/12_doi_verification.csv`](outputs/results/12_doi_verification.csv).

---

## Licence

| | |
|---|---|
| Data and outputs | [CC BY 4.0](LICENSE) |
| Code | [MIT](LICENSE-CODE) |
| Sentinel-2 | © European Union, Copernicus Sentinel data 2024–2025 |

## Citation

See [`CITATION.cff`](CITATION.cff), or use the "Cite this repository" button on GitHub.

## Contact

Yassine Amrouss — yassine.amrouss@usms.ma
Data4Earth Laboratory, Sultan Moulay Slimane University, Beni Mellal, Morocco
""")

# =========================================================== data README
num = ds.select_dtypes("number")
W("data/README.md", f"""
# Data

## `soil/01_analysis_ready_dataset.csv`

The analysis table. {len(ds)} rows, one per sampling location, {len(ds.columns)} columns.
Every model in the paper is fitted from this file.

| Column | Type | Units | Description |
|---|---|---|---|
| `Echantillon` | integer | — | Sample identifier as recorded in the field |
| `Latitude` | float | degrees | WGS 84 latitude of the sampling point |
| `Longitude` | float | degrees | WGS 84 longitude |
| `N` | float | mg kg⁻¹ | Total nitrogen, Kjeldahl. Mean of three analytical replicates |
| `P` | float | mg kg⁻¹ | Available phosphorus, Olsen. Mean of three replicates |
| `K` | float | mg kg⁻¹ | Exchangeable potassium, NH₄OAc. Mean of three replicates |
| `x_m`, `y_m` | float | m | Projected coordinates, EPSG:26191 (Merchich / Nord Maroc) |
| `block` | integer | 1–{s01['n_blocks']} | Spatial cross-validation block |
| `<BAND>_<DATE>` | float | reflectance 0–1 | Surface reflectance, 10 bands × 2 composites |
| `<INDEX>_<DATE>` | float | see inventory | Spectral index, 10 indices × 2 composites |

`<DATE>` is `2024_11` or `2025_01` and refers to the **monthly median composite**,
not a single acquisition. Predictor definitions, formulas, source bands, native and
output resolution are in `soil/01_predictor_inventory.csv`.

Observed ranges: N {ds.N.min():,.0f}–{ds.N.max():,.0f}, P {ds.P.min():.2f}–{ds.P.max():.2f},
K {ds.K.min():.1f}–{ds.K.max():.1f} mg kg⁻¹. All values exceed the limit of
quantification of their determination.

## `soil/11_dataset_3x3_neighbourhood.csv`

The same table with every predictor re-extracted as the mean of a 3 × 3 pixel
neighbourhood (nominal 30 m) instead of the single pixel containing the sample
centroid. Used for the extraction-support sensitivity test; results in
`outputs/results/11_extraction_support_sensitivity.csv`.

## `spatial/`

`Beni_Moussa.shp` and companions: the district boundary.
`01_block_design.csv`: extent, centroid and nearest-neighbour separation of each of
the {s01['n_blocks']} spatial cross-validation blocks, in EPSG:26191.

## `sentinel2/`

`14_scene_inventory_used.csv` — the {int(c11.n_scenes)+int(c01.n_scenes)} scenes that
contribute to the two monthly median composites, with Earth Engine asset ID, ESA
product and granule identifiers, sensing time, MGRS tile, cloud and no-data
percentages, platform, processing baseline, relative orbit and solar angles.

`gee_S2_scene_inventory_*.csv` — the same inventory as exported directly from Earth
Engine by `code/earthengine/01_metadata_report.js`. These are the authoritative files.

`14_scene_inventory_full.csv` — all scenes intersecting the area of interest before
the 40 % cloud filter, for completeness.

## Coordinates

Sampling coordinates are given at full precision. If landholder privacy later
requires restriction, jittering within 250 m keeps all spatial analyses reproducible,
since that is well below both the block dimension and the distances at which
autocorrelation is detectable in these data.
""")

# =========================================================== code README
W("code/README.md", """
# Code

## `earthengine/`

| Script | Purpose |
|---|---|
| `00_original_as_submitted.js` | The export used for the **first** submission, archived verbatim. **Do not run.** Four index formulas did not match their stated definitions; the faults are annotated inline. Kept so the errors can be independently confirmed. |
| `01_metadata_report.js` | Prints and exports full scene provenance: asset IDs, sensing times, MGRS tiles, cloud percentages, SCL classes masked, composite depth, reflectance ranges. Produces Supplementary Table S8. Changes nothing. |
| `02_export_covariates.js` | **Use this one.** Corrected index formulas, redundant layer removed, explicit CRS. Exports the 10 reflectance bands per composite; indices are recomputed downstream with verified formulas. |
| `03_reexport_B7_january.js` | Single-band re-export used to repair `B7_2025_01`, retained for provenance. |

## `python/`

Run in numerical order. Steps 01–06 are the core analysis; 07–19 build the
documents, the deposit and the verification suite.

| Step | Does |
|---|---|
| `01_build_predictors_and_blocks.py` | Corrected 40-predictor set; spatial CV blocks |
| `02_nested_cv_and_baselines.py` | Nested spatial and random CV, five baselines, bootstrap CIs, permutation importance |
| `03_predict_10m_maps.py` | 10 m prediction, uncertainty, dissimilarity index, applicability mask |
| `04_figures_models.py` | Figures 4–8; variograms and Moran's I |
| `05_figures_maps.py` | Figures 3, 9–12 |
| `06_tables.py` | Every manuscript and supplementary table |
| `11_extraction_support_sensitivity.py` | 3 × 3 neighbourhood re-extraction and re-validation |
| `12_verify_dois.py` | Checks every DOI against Crossref |
| `14_scene_inventory.py` | Recovers the scene inventory from the STAC catalogue |
| `17_reconcile_scene_inventory.py` | Adopts the authoritative Earth Engine inventory |
| `16`, `18` | Automated verification of the pipeline and of the manuscript |

Steps 07, 09, 10, 13, 15, 19 build documents and the repository and are included for
completeness rather than because a reader needs them.

## Paths

Each script sets a `BASE` constant at the top pointing at the directory the analysis
was originally run in. Edit that line, or place the repository at the same path,
before running.

## Requirements

Python 3.13. See `../environment.yml` (conda) or `../requirements.txt` (pip).
Steps 03 and 11 need the 20 Sentinel-2 band rasters at 10 m; regenerate them with
`earthengine/02_export_covariates.js`.
""")

# =========================================================== outputs README
W("outputs/README.md", """
# Outputs

## `figures/`

The 12 manuscript figures, each as a 400 dpi PNG and as a vector PDF. Filenames use
the internal generation order; the mapping to manuscript figure numbers is:

| File | Manuscript |
|---|---|
| `Figure_1_study_area_and_design` | Fig. 3 — sampling design and applicability domain |
| `Figure_3_RF_observed_vs_predicted` | Fig. 4 |
| `Figure_4_XGB_observed_vs_predicted` | Fig. 5 |
| `Figure_5_validation_schemes` | Fig. 6 |
| `Figure_6_permutation_importance` | Fig. 8 |
| `Figure_7_variograms` | Fig. 7 |
| `Figure_8_continuous_maps_RF` | Fig. 9 |
| `Figure_9_continuous_maps_XGB` | Fig. 10 |
| `Figure_10_uncertainty_maps` | Fig. 11 |
| `Figure_11_fertility_classes` | Fig. 12 |

Figures 1 and 2 of the manuscript (study area, workflow) are author-supplied graphics
and are not generated by this pipeline.

## `tables/`

`All_Tables_Revision2.xlsx` holds every table as a separate sheet; the same content is
also provided as individual CSVs.

## `results/`

| File | Contents |
|---|---|
| `02_out_of_fold_predictions.csv` | One held-out prediction per observation per scheme. Every metric in the paper is recomputable from this file alone |
| `02_metrics_all_schemes.csv` | R², RMSE, MAE, bias, CCC, slope, RPD, RPIQ for all 18 model × scheme combinations |
| `02_baselines.csv` | Intercept-only, ridge, PLS, ordinary kriging, regression kriging |
| `02_bootstrap_ci.csv`, `02_paired_model_comparison.csv` | Resampling uncertainty and the RF-vs-XGBoost paired test |
| `02_permutation_importance.csv` | Per-predictor importance with between-fold standard deviation |
| `04_variogram_parameters.csv`, `04_morans_I.csv` | Spatial structure diagnostics |
| `11_extraction_support_sensitivity.csv` | Single-pixel vs 3 × 3 extraction |
| `12_doi_verification.csv` | Crossref check of every reference |
| `03_*`, `14_*` | Map summaries, class areas, algorithm agreement, composite summary |

## `maps/`

See `maps/README.md`. The rasters are on Zenodo, not in Git.
""")

W("outputs/maps/README.md", f"""
# 10 m raster products

The eleven GeoTIFFs are **not tracked in this repository**. They total 271 MB, which
would exhaust GitHub's free Git LFS bandwidth in roughly three clones.

## Where to get them

They are attached to the Zenodo record for this project: **[DOI PENDING]**.

## What they are

All on the native Sentinel-2 grid: 7093 × 2950 cells, EPSG:4326, {msum['n_valid_pixels']:,}
valid pixels covering {msum['mapped_area_ha']:,.0f} ha. Effective pixel
{msum['pixel_x_m']:.2f} m × {msum['pixel_y_m']:.2f} m at this latitude.

| File | Contents | Units |
|---|---|---|
| `N_RF_10m.tif`, `P_RF_10m.tif`, `K_RF_10m.tif` | Random Forest predictions | mg kg⁻¹ |
| `N_XGB_10m.tif`, `P_XGB_10m.tif`, `K_XGB_10m.tif` | XGBoost predictions | mg kg⁻¹ |
| `N_RF_SD_10m.tif`, `P_RF_SD_10m.tif`, `K_RF_SD_10m.tif` | Between-tree standard deviation | mg kg⁻¹ |
| `DI_10m.tif` | Predictor-space dissimilarity index | dimensionless |
| `AOA_10m.tif` | Area of applicability, 1 inside / 0 outside | boolean |

The applicability threshold is DI = {msum['aoa_threshold']:.4f};
{msum['pct_inside_aoa']:.1f} % of the mapped area ({msum['ha_inside_aoa']:,.0f} ha)
lies inside the domain. Values outside it should not be used.

## Regenerating them

```bash
# 1. export the 20 band rasters from Earth Engine
#    code/earthengine/02_export_covariates.js
# 2. place them in the covariate directory named at the top of the script
python code/python/03_predict_10m_maps.py
```

Runtime is about 13 minutes on a desktop machine.
""")

# =========================================================== support files
W(".gitattributes", """
*.csv  text eol=lf
*.py   text eol=lf
*.js   text eol=lf
*.md   text eol=lf
*.yml  text eol=lf
*.cff  text eol=lf
*.png  binary
*.pdf  binary
*.xlsx binary
*.shp  binary
*.shx  binary
*.dbf  binary
""")

W(".gitignore", """
__pycache__/
*.pyc
.ipynb_checkpoints/
.DS_Store
Thumbs.db
.vscode/
.idea/
env/
venv/
.env
*.tmp
*.log
# 10 m rasters are distributed via Zenodo, not Git
outputs/maps/*.tif
""")

W("environment.yml", """
name: benimoussa
channels:
  - conda-forge
dependencies:
  - python=3.13
  - numpy=2.5
  - pandas=2.3
  - scikit-learn=1.9
  - py-xgboost=3.4
  - scipy=1.18
  - matplotlib=3.11
  - rasterio=1.5
  - geopandas=1.1
  - pyproj=3.7
  - openpyxl=3.1
  - joblib=1.5
  - pip
  - pip:
      - python-docx
""")

W("requirements.txt", """
numpy==2.5.1
pandas==2.3.3
scikit-learn==1.9.0
xgboost==3.4.0
scipy==1.18.0
matplotlib==3.11.0
rasterio==1.5.0
geopandas==1.1.4
pyproj==3.7.2
openpyxl==3.1.5
joblib==1.5.3
python-docx==1.2.0
""")

W("CHANGELOG.md", f"""
# Changelog

## v1.0.0 — 2026-08-28

First public release, accompanying the revised submission to *Environmental
Monitoring and Assessment*.

### Analysis
- Nested spatial block cross-validation over {s01['n_blocks']} blocks is the primary
  evaluation; all reported statistics come from untouched outer folds.
- Five benchmark models added on identical folds: intercept-only, ridge, PLS,
  ordinary kriging, regression kriging.
- Permutation importance on held-out folds replaces impurity and gain importance.
- Local uncertainty and an area of applicability accompany every map.
- 10 m prediction grid ({msum['n_valid_pixels']:,} pixels), replacing the decimated
  grid used previously.

### Corrections to the first submission
- `SI` was computing −NDMI, `VSSI` was computing −NDSI, and `NDSI`/`MNDWI` were
  interchanged. Two of 42 columns were sign-flipped duplicates. Predictor count
  corrected from 41 to {s01['n_predictors']}.
- Covariates are monthly **median composites** of
  {int(c11.n_scenes)} and {int(c01.n_scenes)} scenes across four MGRS tiles, not two
  single cloud-free acquisitions.
- Castaldi reference corrected: the cited DOI resolved to an unrelated paper.
- Mean total nitrogen corrected from 1 683 to {ds.N.mean():,.1f} mg kg⁻¹.
- Claim that XGBoost outperforms Random Forest withdrawn; the paired difference is
  not significant.
""")

W("CITATION.cff", f"""
cff-version: 1.2.0
message: "If you use this dataset or code, please cite the article below."
title: "Soil macronutrient mapping in the Beni Moussa irrigated district, Morocco: data and code"
abstract: >-
  Analysis-ready data, complete analysis code, cross-validation fold assignments,
  out-of-fold predictions and georeferenced 10 m prediction, uncertainty,
  dissimilarity and applicability products for 110 composite topsoil samples from the
  Beni Moussa irrigated district, Tadla Plain, Morocco, predicted from Sentinel-2
  surface reflectance under nested spatial block cross-validation.
type: dataset
authors:
  - family-names: Amrouss
    given-names: Yassine
    email: yassine.amrouss@usms.ma
    affiliation: "Data4Earth Laboratory, Sultan Moulay Slimane University"
  - family-names: Arioua
    given-names: Abdelkrim
  - family-names: Elhamdouni
    given-names: Driss
  - family-names: El Baghdadi
    given-names: Mohamed
  - family-names: Barakat
    given-names: Ahmed
  - family-names: El Atiq
    given-names: Jaouad
  - family-names: Ouchkir
    given-names: Insaf
  - family-names: Bimouhen
    given-names: Mostafa
  - family-names: Nait-taleb
    given-names: Oussama
  - family-names: Hilali
    given-names: Abdessamad
version: 1.0.0
date-released: 2026-08-28
license: CC-BY-4.0
repository-code: "https://github.com/{USER}/{REPO}"
keywords:
  - digital soil mapping
  - spatial cross-validation
  - area of applicability
  - Sentinel-2
  - soil nitrogen
  - soil phosphorus
  - soil potassium
  - Tadla Plain
  - Morocco
""")

W(".zenodo.json", json.dumps({
    "title": ("Soil macronutrient mapping in the Beni Moussa irrigated district, "
              "Tadla Plain, Morocco: data, code and 10 m products"),
    "upload_type": "dataset",
    "license": "cc-by-4.0",
    "version": "1.0.0",
    "creators": [
        {"name": "Amrouss, Yassine",
         "affiliation": "Data4Earth Laboratory, Sultan Moulay Slimane University"},
        {"name": "Arioua, Abdelkrim"}, {"name": "Elhamdouni, Driss"},
        {"name": "El Baghdadi, Mohamed"}, {"name": "Barakat, Ahmed"},
        {"name": "El Atiq, Jaouad"}, {"name": "Ouchkir, Insaf"},
        {"name": "Bimouhen, Mostafa"}, {"name": "Nait-taleb, Oussama"},
        {"name": "Hilali, Abdessamad"}],
    "keywords": ["digital soil mapping", "spatial cross-validation",
                 "area of applicability", "Sentinel-2", "soil nitrogen",
                 "soil phosphorus", "soil potassium", "Tadla Plain", "Morocco",
                 "random forest", "XGBoost"],
    "description": (
        "Analysis-ready data, complete analysis code, cross-validation fold "
        "assignments, out-of-fold predictions and georeferenced 10 m prediction, "
        "uncertainty, dissimilarity and applicability rasters supporting the article "
        "'High-resolution mapping of soil macronutrients in a semi-arid climate "
        "(Morocco) using Sentinel-2 data and machine learning models', submitted to "
        "Environmental Monitoring and Assessment. 110 composite topsoil samples "
        f"(0-20 cm) and {s01['n_predictors']} Sentinel-2 predictors; performance "
        "assessed by nested spatial block cross-validation over "
        f"{s01['n_blocks']} spatial blocks. The eleven 10 m GeoTIFFs are included in "
        "this Zenodo record but not in the GitHub repository.")
}, indent=2, ensure_ascii=False))

W("LICENSE", """
Creative Commons Attribution 4.0 International (CC BY 4.0)

Copyright (c) 2026 Yassine Amrouss and co-authors.

You are free to share and adapt this material for any purpose, including
commercially, provided you give appropriate credit, provide a link to the licence,
and indicate if changes were made.

Full licence text: https://creativecommons.org/licenses/by/4.0/legalcode

This licence covers the data and the derived outputs. The source code is licensed
separately under the MIT License; see LICENSE-CODE.

Sentinel-2 data are (c) European Union, Copernicus Sentinel data 2024-2025, and are
redistributed here in derived form under the Copernicus open data policy.
""")

W("LICENSE-CODE", """
MIT License

Copyright (c) 2026 Yassine Amrouss

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""")

W("run_all.py", '''
# -*- coding: utf-8 -*-
"""
Run the analysis pipeline in order.

Each step is checked for its inputs before it runs, so a missing prerequisite is
reported rather than causing a traceback halfway through. Steps that need the
Sentinel-2 band rasters are skipped with a message if those are not present.

    python run_all.py            # run everything that can run
    python run_all.py --list     # show the pipeline without running it
"""
import os, sys, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "code", "python")

# (script, needs the 10 m Sentinel-2 band rasters?)
STEPS = [
    ("01_build_predictors_and_blocks.py", False),
    ("02_nested_cv_and_baselines.py",     False),
    ("03_predict_10m_maps.py",            True),
    ("04_figures_models.py",              False),
    ("05_figures_maps.py",                False),
    ("06_tables.py",                      False),
    ("11_extraction_support_sensitivity.py", True),
    ("12_verify_dois.py",                 False),
    ("14_scene_inventory.py",             False),
    ("17_reconcile_scene_inventory.py",   False),
    ("16_final_verification.py",          False),
]

COVDIR = r"d:\\Doctorat\\article1\\covariates_clipped"


def have_rasters():
    return os.path.isdir(COVDIR) and len(
        [f for f in os.listdir(COVDIR) if f.endswith(".tif")]) >= 20


def main():
    if "--list" in sys.argv:
        print("Pipeline order:")
        for s, need in STEPS:
            print(f"   {s}" + ("   [needs the 10 m band rasters]" if need else ""))
        return
    rasters = have_rasters()
    if not rasters:
        print(f"NOTE: Sentinel-2 band rasters not found in {COVDIR}.")
        print("      Steps 03 and 11 will be skipped. Regenerate the rasters with")
        print("      code/earthengine/02_export_covariates.js if you need them.\\n")
    t0 = time.time()
    for script, need in STEPS:
        path = os.path.join(PY, script)
        if not os.path.exists(path):
            print(f"SKIP  {script}  (not found)"); continue
        if need and not rasters:
            print(f"SKIP  {script}  (needs the band rasters)"); continue
        print(f"RUN   {script}")
        r = subprocess.run([sys.executable, path])
        if r.returncode != 0:
            print(f"\\nFAILED at {script} (exit {r.returncode}).")
            sys.exit(r.returncode)
    print(f"\\nPipeline finished in {(time.time()-t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
''')

W("UPLOAD.md", f"""
# Publishing this repository

## 1. Set your username

`YOUR-GITHUB-USERNAME` appears in `README.md`, `CITATION.cff` and this file.

```bash
grep -rl "YOUR-GITHUB-USERNAME" . | xargs sed -i 's/YOUR-GITHUB-USERNAME/yourname/g'
```

On Windows PowerShell:

```powershell
Get-ChildItem -Recurse -Include *.md,*.cff |
  ForEach-Object {{ (Get-Content $_ -Raw) -replace 'YOUR-GITHUB-USERNAME','yourname' |
  Set-Content $_ -Encoding utf8 }}
```

## 2. Push

No Git LFS is needed: the repository is about 35 MB because the rasters are
distributed through Zenodo instead.

```bash
cd {GH}
git init
git add .
git commit -m "v1.0.0: data, code and outputs for Beni Moussa NPK mapping"
git branch -M main
git remote add origin https://github.com/{USER}/{REPO}.git
git push -u origin main
```

Make the repository **public**.

## 3. Connect Zenodo and mint the DOI

1. Sign in at https://zenodo.org with your GitHub account.
2. Settings → GitHub → switch on the toggle for `{REPO}`.
3. On GitHub: Releases → Create a new release → tag `v1.0.0` → Publish.
4. Zenodo captures the release and issues a DOI within a minute.

`.zenodo.json` pre-fills the record's title, authors, licence, keywords and
description, so nothing needs retyping.

## 4. Attach the rasters to the Zenodo record

The eleven GeoTIFFs are not in Git. After the Zenodo record appears:

1. Open the record → Edit.
2. Upload the eleven files from `outputs_fast/FINAL/maps/`.
3. Publish. This creates a new version of the record; use that DOI.

Total upload about 271 MB; Zenodo's per-record limit is 50 GB.

## 5. Put the DOI in three places

- the manuscript, replacing `[ZENODO DOI]` in Data Availability
- `README.md`, replacing both `PENDING` placeholders in the badge
- `CITATION.cff`, as a new `doi:` field

## Checklist before pushing

- [ ] `YOUR-GITHUB-USERNAME` replaced everywhere
- [ ] repository is public
- [ ] `data/soil/01_analysis_ready_dataset.csv` holds coordinates you are willing to
      publish; if not, jitter within 250 m and say so in `data/README.md`
- [ ] the manuscript and the response letter are **not** here — they stay private
      until the paper is accepted, because the response letter quotes the referee
      report
""")

# --------------------------------------------------------------- report
man2 = pd.DataFrame(rows)
tot = man2.size_bytes.sum()
print(f"Repository assembled at {GH}")
print(f"  {len(man2)} tracked files, {tot/1e6:.1f} MB\\n")
man2["top"] = man2.path.str.split("/").str[0]
man2["sub"] = man2.path.str.rsplit("/", n=1).str[0]
print(man2.groupby("sub").agg(files=("path", "size"),
                              MB=("size_bytes", lambda s: round(s.sum() / 1e6, 2)))
      .to_string())
print(f"\\nlargest file: {man2.size_bytes.max()/1e6:.1f} MB")
print(f"files over 50 MB: {(man2.size_bytes > 50e6).sum()}  (Git LFS not required)")
print("\\nSTEP 19 complete.")
