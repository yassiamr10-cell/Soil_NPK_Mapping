# -*- coding: utf-8 -*-
"""
STEP 15 - Assemble a ready-to-upload GitHub repository.

Produces outputs_fast/FINAL/github/ containing everything that should be pushed,
with README, LICENSE, CITATION.cff, .gitignore, .gitattributes (Git LFS for the
rasters), environment.yml, a Zenodo metadata file and an upload script.
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
for sub in ("data", "code", "results", "maps", "figures", "tables", "docs", "metadata"):
    os.makedirs(os.path.join(GH, sub), exist_ok=True)

s01  = json.load(open(os.path.join(RES, "01_summary.json")))
msum = json.load(open(os.path.join(RES, "03_map_summary.json")))
csum = pd.read_csv(os.path.join(RES, "14_composite_summary.csv"))
c11 = csum[csum.composite == "2024_11"].iloc[0]
c01 = csum[csum.composite == "2025_01"].iloc[0]

# ---------------------------------------------------------------- files
COPY = [
    # analysis inputs
    (os.path.join(RES, "01_analysis_ready_dataset.csv"), "data"),
    (os.path.join(RES, "01_predictor_inventory.csv"), "data"),
    (os.path.join(RES, "01_block_design.csv"), "data"),
    (os.path.join(RES, "11_dataset_3x3_neighbourhood.csv"), "data"),
    (os.path.join(RES, "14_scene_inventory_used.csv"), "data"),
    (os.path.join(RES, "14_scene_inventory_full.csv"), "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.shp", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.shx", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.dbf", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.prj", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.cpg", "data"),
    # earth engine
    (r"d:\Doctorat\article1\gee_redownload_B7_2025_01.js", "code"),
    (os.path.join(FINAL, "code", "gee_00_original_as_submitted.js"), "code"),
    (os.path.join(FINAL, "code", "gee_01_metadata_report.js"), "code"),
    (os.path.join(FINAL, "code", "gee_02_export_covariates_CORRECTED.js"), "code"),
    # results
    (os.path.join(RES, "02_out_of_fold_predictions.csv"), "results"),
    (os.path.join(RES, "02_metrics_all_schemes.csv"), "results"),
    (os.path.join(RES, "02_selected_hyperparameters.csv"), "results"),
    (os.path.join(RES, "02_baselines.csv"), "results"),
    (os.path.join(RES, "02_bootstrap_ci.csv"), "results"),
    (os.path.join(RES, "02_paired_model_comparison.csv"), "results"),
    (os.path.join(RES, "02_permutation_importance.csv"), "results"),
    (os.path.join(RES, "03_class_areas.csv"), "results"),
    (os.path.join(RES, "03_raster_summary.csv"), "results"),
    (os.path.join(RES, "03_map_summary.json"), "results"),
    (os.path.join(RES, "03_RF_XGB_agreement_summary.csv"), "results"),
    (os.path.join(RES, "04_variogram_parameters.csv"), "results"),
    (os.path.join(RES, "04_morans_I.csv"), "results"),
    (os.path.join(RES, "11_extraction_support_sensitivity.csv"), "results"),
    (os.path.join(RES, "11_extraction_agreement.csv"), "results"),
    (os.path.join(RES, "12_doi_verification.csv"), "results"),
    (os.path.join(RES, "14_composite_summary.csv"), "results"),
    # metadata
    (os.path.join(RES, "02_session_info.txt"), "metadata"),
    (os.path.join(RES, "01_summary.json"), "metadata"),
]
for pat, sub in [(os.path.join(FINAL, "code", "*.py"), "code"),
                 (os.path.join(FINAL, "maps", "*.tif"), "maps"),
                 (os.path.join(FINAL, "figures", "*.png"), "figures"),
                 (os.path.join(FINAL, "figures", "*.pdf"), "figures"),
                 (os.path.join(FINAL, "tables", "*.csv"), "tables"),
                 (os.path.join(FINAL, "tables", "*.xlsx"), "tables"),
                 (os.path.join(FINAL, "docs", "*.docx"), "docs")]:
    for f in glob.glob(pat):
        COPY.append((f, sub))

rows = []
for src, sub in COPY:
    if not os.path.exists(src):
        print("  missing (skipped):", os.path.basename(src)); continue
    dst = os.path.join(GH, sub, os.path.basename(src))
    shutil.copy2(src, dst)
    rows.append(dict(folder=sub, file=os.path.basename(src),
                     size_bytes=os.path.getsize(dst),
                     md5=hashlib.md5(open(dst, "rb").read()).hexdigest()))
man = pd.DataFrame(rows).sort_values(["folder", "file"])
man.to_csv(os.path.join(GH, "MANIFEST.csv"), index=False)


def W(name, text):
    with open(os.path.join(GH, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(textwrap.dedent(text).lstrip("\n"))


# ---------------------------------------------------------------- README
big = man[man.size_bytes > 100e6]
W("README.md", f"""
# High-resolution mapping of soil macronutrients in the Beni Moussa irrigated district

Data, code and outputs for:

> Amrouss, Y., Arioua, A., Elhamdouni, D., El Baghdadi, M., Barakat, A., El Atiq, J.,
> Ouchkir, I., Bimouhen, M., Nait-taleb, O., Hilali, A.
> *High-resolution mapping of soil macronutrients in a semi-arid climate (Morocco)
> using Sentinel-2 data and machine learning models.*
> Submitted to **Environmental Monitoring and Assessment**.

[![DOI](https://zenodo.org/badge/DOI/PENDING.svg)](https://doi.org/PENDING)

Every number, figure, table and raster in the article can be regenerated from this
repository by running the scripts in `code/` in numerical order.

---

## What this study does

110 composite topsoil samples (0–20 cm) from the Beni Moussa irrigated district
(Tadla Plain, Morocco), collected between November 2024 and January 2025, are used
to predict total nitrogen, Olsen phosphorus and exchangeable potassium from
Sentinel-2 surface reflectance. Performance is measured under **nested spatial
block cross-validation**, and the delivered maps carry **local uncertainty** and an
explicit **area of applicability**.

| | Random Forest, nested spatial CV |
|---|---|
| Total N | R² = 0.878, RMSE = 226 mg kg⁻¹ |
| Olsen P | R² = 0.729, RMSE = 12.1 mg kg⁻¹ |
| Exchangeable K | R² = 0.724, RMSE = 13.2 mg kg⁻¹ |

Random Forest and XGBoost are **statistically indistinguishable** on this dataset.
For potassium, ridge regression on the same predictors performs at least as well as
either. Predictive importance is concentrated in raw near-infrared and red-edge
reflectance from the November composite, which indicates the models track canopy
condition rather than soil composition directly. The maps are reconnaissance
products, not a basis for variable-rate fertiliser prescription.

---

## Repository layout

```
data/       110 observations with coordinates and {s01['n_predictors']} predictors;
            predictor inventory; spatial block design; 3x3 extraction variant;
            Sentinel-2 scene inventory; district boundary shapefile
code/       01-15, the complete pipeline, plus the Earth Engine export script
results/    out-of-fold predictions, metrics, hyperparameters, baselines,
            bootstrap intervals, permutation importance, variograms, map summaries
maps/       georeferenced 10 m GeoTIFFs (Git LFS) - predictions, uncertainty,
            dissimilarity index, applicability mask
figures/    all manuscript figures, 400 dpi PNG and vector PDF
tables/     all manuscript and supplementary tables
docs/       revised manuscript, response to the referee, supporting documents
metadata/   session information
```

## Reproducing the analysis

```bash
conda env create -f environment.yml
conda activate benimoussa

python code/01_build_predictors_and_blocks.py
python code/02_nested_cv_and_baselines.py
python code/03_predict_10m_maps.py          # needs the Sentinel-2 band rasters
python code/04_figures_models.py
python code/05_figures_maps.py
python code/06_tables.py
python code/11_extraction_support_sensitivity.py
python code/14_scene_inventory.py
```

Steps 03 and 11 additionally require the 20 Sentinel-2 band rasters (10 bands x 2
monthly composites) at 10 m. These are not redistributed here because of their
size. Run `code/gee_02_export_covariates_CORRECTED.js` in the Earth Engine Code
Editor to regenerate them; Sentinel-2 L2A is freely available from the Copernicus
Data Space.

### Earth Engine scripts

| Script | Purpose |
|---|---|
| `gee_00_original_as_submitted.js` | The export used for the **previous** submission, archived verbatim. **Do not run.** Four of its index formulas did not match their stated definitions — see *Corrections* below. Kept so the errors can be independently confirmed. |
| `gee_01_metadata_report.js` | Prints and exports the full scene provenance: asset IDs, sensing times, MGRS tiles, cloud percentages, SCL classes masked, composite depth, reflectance ranges. Produces Supplementary Table S8. Changes nothing. |
| `gee_02_export_covariates_CORRECTED.js` | **Use this one.** Corrected index formulas, redundant layer removed, explicit CRS. Exports the 10 reflectance bands per composite; the indices are recomputed downstream with verified formulas. |
| `gee_redownload_B7_2025_01.js` | Single-band re-export used to repair `B7_2025_01`, retained for provenance. |

## How the covariates were built

| Item | Value |
|---|---|
| Collection | `COPERNICUS/S2_SR_HARMONIZED` |
| Area of interest | 7.152655° W – 6.309455° W, 32.143829° N – 32.619321° N |
| Scene filter | `CLOUDY_PIXEL_PERCENTAGE < 40` |
| SCL classes masked | 3 (cloud shadow), 8, 9 (cloud medium/high), 10 (thin cirrus), 11 (snow/ice) |
| Scaling | divide by 10 000 after masking |
| Compositing | per-pixel **median** over each calendar month |
| November 2024 composite | {int(c11.n_scenes)} scenes, {int(c11.n_dates)} dates, 4 MGRS tiles, cloud {c11.cloud_min:.2f}–{c11.cloud_max:.2f} % |
| January 2025 composite | {int(c01.n_scenes)} scenes, {int(c01.n_dates)} dates, 4 MGRS tiles, cloud {c01.cloud_min:.3f}–{c01.cloud_max:.2f} % |
| MGRS tiles | 29SPR, 29SPS, 29SQR, 29SQS |
| Processing baseline | 05.11 (BOA_ADD_OFFSET = −1000, handled by the harmonized collection) |
| Export | 10 m, EPSG:4326, clipped to the AOI |

The full scene inventory is in `data/14_scene_inventory_used.csv`.

## Analysis summary

| Item | Value |
|---|---|
| Observations | 110 composite topsoil samples, 0–20 cm |
| Predictors | {s01['n_predictors']} (10 reflectance bands + 10 spectral indices x 2 composites) |
| Duplicate predictor pairs | 0 (max abs. correlation 0.998; numerical rank {s01['numerical_rank']}) |
| Primary validation | nested CV, leave-one-block-out over {s01['n_blocks']} spatial blocks |
| Inner loop | GroupKFold(5) on training blocks only — all tuning inside |
| Fold sizes | {', '.join(str(n) for n in s01['fold_sizes'])} |
| Median block separation | {s01['median_block_separation_km']:.2f} km |
| Prediction grid | 10 m, {msum['n_valid_pixels']:,} valid pixels, {msum['mapped_area_ha']:,.0f} ha |
| Raster CRS | EPSG:4326 (figures drawn in EPSG:26191, Merchich / Nord Maroc) |
| Area of applicability | {msum['pct_inside_aoa']:.1f} % ({msum['ha_inside_aoa']:,.0f} ha) inside |
| Random seed | 42 throughout |

## Corrections applied in this revision

Three predictor-construction errors in the previously submitted version were found
during an audit and are corrected here:

- the layer labelled **SI** computed `(B11−B8)/(B11+B8)`, the exact negative of NDMI,
  not `B11 × B12`;
- the layer labelled **VSSI** computed `(B11−B3)/(B11+B3)`, the exact negative of the
  layer labelled NDSI, not `2·B3 − 5·(B4+B8)`;
- the layers labelled **NDSI** and **MNDWI** were interchanged with respect to their
  formulas.

Two of the previous 42 columns were therefore sign-flipped duplicates of two others.
The predictor count is corrected from 41 to {s01['n_predictors']}, and every result
here was produced with the corrected set. Both the original and the corrected Earth
Engine scripts are included so the errors can be verified directly:

```js
// gee_00_original_as_submitted.js          // gee_02_..._CORRECTED.js
SI    = (B11-B8)/(B11+B8)   // = -NDMI     SI    = B11 * B12
VSSI  = (B11-B3)/(B11+B3)   // = -NDSI     VSSI  = 2*B3 - 5*(B4+B8)
MNDWI = (B3-B12)/(B3+B12)   // wrong SWIR  MNDWI = (B3-B11)/(B3+B11)
NDSI  = (B3-B11)/(B3+B11)   // = MNDWI     (removed)
```

A bibliographic error was also found: the Castaldi reference in the previous version
cited DOI `10.3390/rs11242924`, which resolves to a radar-tomography paper by
Monteith et al. The intended article is Castaldi, F. (2021), *Remote Sensing* **13**,
3345, `10.3390/rs13173345`. All 46 DOIs are verified in `results/12_doi_verification.csv`.

## Large files

The GeoTIFFs in `maps/` are tracked with **Git LFS** (see `.gitattributes`). Install
Git LFS before cloning, or the rasters will arrive as pointer files:

```bash
git lfs install
git clone https://github.com/{USER}/{REPO}.git
```

## Licence

Data and outputs: [CC BY 4.0](LICENSE). Code: MIT (see `LICENSE-CODE`).
Sentinel-2 data © European Union, Copernicus Sentinel data 2024–2025.

## Contact

Yassine Amrouss — yassine.amrouss@usms.ma
Data4Earth Laboratory, Sultan Moulay Slimane University, Beni Mellal, Morocco
""")

# ---------------------------------------------------------------- git files
W(".gitattributes", """
*.tif  filter=lfs diff=lfs merge=lfs -text
*.tiff filter=lfs diff=lfs merge=lfs -text
*.docx filter=lfs diff=lfs merge=lfs -text
*.xlsx filter=lfs diff=lfs merge=lfs -text
*.csv  text eol=lf
*.py   text eol=lf
*.md   text eol=lf
""")

W(".gitignore", """
__pycache__/
*.pyc
.ipynb_checkpoints/
.DS_Store
Thumbs.db
.vscode/
.idea/
*.tmp
*.log
env/
venv/
.env
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
  - python-docx
""")

W("LICENSE", """
Creative Commons Attribution 4.0 International (CC BY 4.0)

Copyright (c) 2026 Yassine Amrouss and co-authors.

You are free to share and adapt this material for any purpose, including
commercially, provided you give appropriate credit, provide a link to the licence,
and indicate if changes were made.

Full licence text: https://creativecommons.org/licenses/by/4.0/legalcode

Sentinel-2 data are © European Union, Copernicus Sentinel data 2024-2025, and are
redistributed here in derived form under the Copernicus open data policy.
""")

W("LICENSE-CODE", """
MIT License

Copyright (c) 2026 Yassine Amrouss

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""")

W("CITATION.cff", f"""
cff-version: 1.2.0
message: "If you use this dataset or code, please cite the article below."
title: "Data and code: high-resolution mapping of soil macronutrients in the Beni Moussa irrigated district, Morocco"
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
  - Tadla Plain
  - Morocco
""")

W(".zenodo.json", json.dumps({
    "title": ("Data and code: high-resolution mapping of soil macronutrients in the "
              "Beni Moussa irrigated district, Tadla Plain, Morocco"),
    "upload_type": "dataset",
    "license": "cc-by-4.0",
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
                 "soil phosphorus", "soil potassium", "Tadla Plain", "Morocco"],
    "description": (
        "Analysis-ready data, complete analysis code, cross-validation fold "
        "assignments, out-of-fold predictions and georeferenced 10 m prediction, "
        "uncertainty, dissimilarity and applicability rasters supporting the article "
        "'High-resolution mapping of soil macronutrients in a semi-arid climate "
        "(Morocco) using Sentinel-2 data and machine learning models', submitted to "
        "Environmental Monitoring and Assessment. 110 composite topsoil samples "
        f"(0-20 cm) and {s01['n_predictors']} Sentinel-2 predictors; performance "
        "assessed by nested spatial block cross-validation.")
}, indent=2, ensure_ascii=False))

W("UPLOAD.md", f"""
# How to publish this repository

## 1. Install Git LFS (once)

```bash
git lfs install
```

The eleven GeoTIFFs in `maps/` total about 258 MB and the largest is ~27 MB, so they
are under GitHub's 100 MB per-file hard limit but well over the 50 MB warning
threshold. LFS is already configured in `.gitattributes`.

GitHub gives 1 GB of free LFS storage and 1 GB/month of bandwidth. This repository
uses roughly 290 MB, so it fits — but if you would rather not use LFS at all, delete
the `maps/` folder before pushing and upload the rasters to Zenodo only. The README
already tells readers the rasters can be regenerated from `code/03_predict_10m_maps.py`.

## 2. Create and push

```bash
cd {GH}

git init
git lfs track "*.tif"
git add .
git commit -m "Initial release: data, code and outputs for Beni Moussa NPK mapping"
git branch -M main
git remote add origin https://github.com/{USER}/{REPO}.git
git push -u origin main
```

Replace `{USER}` with your GitHub username first — it also appears in
`README.md` and `CITATION.cff`.

## 3. Connect Zenodo and mint the DOI

1. Sign in at https://zenodo.org with your GitHub account.
2. Settings -> GitHub -> switch on the toggle for `{REPO}`.
3. Back on GitHub: Releases -> Create a new release -> tag `v1.0.0`.
4. Zenodo captures the release and issues a DOI within about a minute.
5. Paste the DOI into:
   - the manuscript, replacing `[ZENODO DOI]` in Data availability
   - `README.md`, replacing the two `PENDING` placeholders in the badge line
   - `CITATION.cff`, adding a `doi:` field

`.zenodo.json` in this folder pre-fills the Zenodo record with the title, authors,
licence, keywords and description, so you should not need to retype any of it.

## 4. Check before you push

- [ ] `{USER}` replaced everywhere (`grep -r "YOUR-GITHUB-USERNAME" .`)
- [ ] the repository is **public**
- [ ] `data/01_analysis_ready_dataset.csv` contains the coordinates you are willing
      to publish — if landholder privacy requires it, jitter them within 250 m and
      say so in the README and the manuscript
- [ ] `docs/` contains only what you intend to make public; the response letter and
      the internal notes documents may be better kept private until acceptance
""")

# ---------------------------------------------------------------- report
man2 = pd.DataFrame(rows)
tot = man2.size_bytes.sum()
print(f"GitHub folder assembled at {GH}")
print(f"  {len(man2)} files, {tot/1e6:.1f} MB total\n")
print(man2.groupby("folder").agg(files=("file", "size"),
                                 MB=("size_bytes", lambda s: round(s.sum()/1e6, 1)))
      .to_string())
print("\nsupport files written: README.md, UPLOAD.md, LICENSE, LICENSE-CODE, "
      "CITATION.cff, .zenodo.json, .gitattributes, .gitignore, environment.yml, "
      "MANIFEST.csv")
over = man2[man2.size_bytes > 50e6]
print(f"\nfiles over 50 MB (LFS recommended): {len(over)}")
if len(over):
    print(over[["folder", "file", "size_bytes"]].to_string(index=False))
over100 = man2[man2.size_bytes > 100e6]
print(f"files over 100 MB (GitHub hard limit, LFS required): {len(over100)}")
print("\nSTEP 15 complete.")
