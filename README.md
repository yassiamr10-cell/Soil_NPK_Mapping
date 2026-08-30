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
| Total N | 0.878 | 226.4 |
| Olsen P | 0.729 | 12.11 |
| Exchangeable K | 0.724 | 13.23 |

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
  soil/          110 observations with coordinates and 40 predictors,
                 the 3x3 extraction variant, and the predictor inventory
  spatial/       district boundary shapefile and the cross-validation block design
  sentinel2/     inventory of the 52 scenes behind
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
git clone https://github.com/YOUR-GITHUB-USERNAME/beni-moussa-npk-mapping.git
cd beni-moussa-npk-mapping
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
| November 2024 | 28 scenes, 11 dates, cloud 0.00–39.60 % |
| January 2025 | 24 scenes, 9 dates, cloud 0.003–38.77 % |
| MGRS tiles | 29SPR, 29SPS, 29SQR, 29SQS (two relative orbits, 94 and 137) |
| Processing baseline | 05.11, `BOA_ADD_OFFSET = −1000`, applied by the harmonized collection |
| Export | 10 m, EPSG:4326, clipped to the AOI |

Full inventory: [`data/sentinel2/14_scene_inventory_used.csv`](data/sentinel2/14_scene_inventory_used.csv).

---

## Analysis summary

| Item | Value |
|---|---|
| Observations | 110 composite topsoil samples, 0–20 cm, three analytical replicates each |
| Predictors | 40 (10 bands + 10 indices × 2 composites) |
| Duplicate predictor pairs | 0 (max abs. correlation 0.998; numerical rank 38) |
| Primary validation | nested CV, leave-one-block-out over 10 spatial blocks |
| Inner loop | GroupKFold(5) on training blocks only |
| Fold sizes | 6, 7, 8, 11, 11, 11, 12, 13, 14, 17 |
| Median block separation | 1.81 km |
| Prediction grid | 10 m, 9,343,965 valid pixels, 78,453 ha |
| Raster CRS | EPSG:4326; figures drawn in EPSG:26191 (Merchich / Nord Maroc) |
| Area of applicability | 76.7 % (60,192 ha) inside |
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
The predictor count is corrected from 41 to 40.

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
