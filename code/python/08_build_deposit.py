# -*- coding: utf-8 -*-
"""
STEP 08 - Assemble the reproducibility deposit required by referee comment M11
and write its README and MANIFEST.
"""
import os, shutil, hashlib, json, glob
import pandas as pd

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
DEP   = os.path.join(FINAL, "deposit")
for sub in ("data", "code", "results", "maps", "figures", "tables", "metadata"):
    os.makedirs(os.path.join(DEP, sub), exist_ok=True)

COPY = [
    (os.path.join(FINAL, "results", "01_analysis_ready_dataset.csv"), "data"),
    (os.path.join(FINAL, "results", "01_predictor_inventory.csv"), "data"),
    (os.path.join(FINAL, "results", "01_block_design.csv"), "data"),
    (os.path.join(FINAL, "results", "02_out_of_fold_predictions.csv"), "results"),
    (os.path.join(FINAL, "results", "02_metrics_all_schemes.csv"), "results"),
    (os.path.join(FINAL, "results", "02_selected_hyperparameters.csv"), "results"),
    (os.path.join(FINAL, "results", "02_baselines.csv"), "results"),
    (os.path.join(FINAL, "results", "02_bootstrap_ci.csv"), "results"),
    (os.path.join(FINAL, "results", "02_paired_model_comparison.csv"), "results"),
    (os.path.join(FINAL, "results", "02_permutation_importance.csv"), "results"),
    (os.path.join(FINAL, "results", "02_session_info.txt"), "metadata"),
    (os.path.join(FINAL, "results", "02_run_log.txt"), "metadata"),
    (os.path.join(FINAL, "results", "03_map_summary.json"), "results"),
    (os.path.join(FINAL, "results", "03_class_areas.csv"), "results"),
    (os.path.join(FINAL, "results", "03_raster_summary.csv"), "results"),
    (os.path.join(FINAL, "results", "04_variogram_parameters.csv"), "results"),
    (os.path.join(FINAL, "results", "04_morans_I.csv"), "results"),
    (r"d:\Doctorat\article1\Beni_Moussa.shp", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.shx", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.dbf", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.prj", "data"),
    (r"d:\Doctorat\article1\Beni_Moussa.cpg", "data"),
    (r"d:\Doctorat\article1\gee_redownload_B7_2025_01.js", "code"),
]
for pat, sub in [(os.path.join(FINAL, "code", "*.py"), "code"),
                 (os.path.join(FINAL, "maps", "*.tif"), "maps"),
                 (os.path.join(FINAL, "figures", "*.png"), "figures"),
                 (os.path.join(FINAL, "figures", "*.pdf"), "figures"),
                 (os.path.join(FINAL, "tables", "*.csv"), "tables"),
                 (os.path.join(FINAL, "tables", "*.xlsx"), "tables")]:
    for f in glob.glob(pat):
        COPY.append((f, sub))

rows = []
for src, sub in COPY:
    if not os.path.exists(src):
        print("  missing (skipped):", src)
        continue
    dst = os.path.join(DEP, sub, os.path.basename(src))
    shutil.copy2(src, dst)
    h = hashlib.md5(open(dst, "rb").read()).hexdigest()
    rows.append(dict(folder=sub, file=os.path.basename(src),
                     size_bytes=os.path.getsize(dst), md5=h))
man = pd.DataFrame(rows).sort_values(["folder", "file"])
man.to_csv(os.path.join(DEP, "MANIFEST.csv"), index=False)
print(f"deposit assembled: {len(man)} files, "
      f"{man.size_bytes.sum()/1e6:.1f} MB")

msum = json.load(open(os.path.join(FINAL, "results", "03_map_summary.json")))
s01 = json.load(open(os.path.join(FINAL, "results", "01_summary.json")))

readme = f"""# Reproducibility deposit

High-resolution mapping of soil macronutrients in a semi-arid climate (Morocco)
using Sentinel-2 data and machine learning — Beni Moussa irrigated district,
Tadla Plain, Morocco.

Amrouss, Y., Arioua, A., Elhamdouni, D., El Baghdadi, M., Barakat, A.,
El Atiq, J., Ouchkir, I., Bimouhen, M., Nait-taleb, O., Hilali, A.
Submitted to *Environmental Monitoring and Assessment*.

This archive supports referee comment M11. Every number, figure, table and raster
in the manuscript can be regenerated from the contents of `data/` by running the
scripts in `code/` in numerical order.

## Contents

    data/       110 soil observations with coordinates and the {s01['n_predictors']}
                analysis-ready predictors; the predictor inventory; the spatial
                block design; the district boundary shapefile
    code/       01-08, the complete analysis pipeline, plus the Earth Engine export script
    results/    out-of-fold predictions, metrics for every scheme, selected
                hyperparameters, baselines, bootstrap intervals, permutation
                importance, variogram parameters, map summaries
    maps/       georeferenced 10 m rasters: predictions, uncertainty,
                dissimilarity index and applicability mask
    figures/    all manuscript figures at 400 dpi (PNG) and as vector PDF
    tables/     all manuscript and supplementary tables
    metadata/   session information and the full analysis run log

## How to reproduce

    python code/01_build_predictors_and_blocks.py
    python code/02_nested_cv_and_baselines.py
    python code/03_predict_10m_maps.py
    python code/04_figures_models.py
    python code/05_figures_maps.py
    python code/06_tables.py
    python code/07_build_response_docx.py

Step 03 additionally requires the 20 Sentinel-2 reflectance band rasters
(10 bands x 2 acquisitions) at 10 m. These are exported by the Earth Engine
script in `code/`; they are not redistributed here because of their size, and
because Sentinel-2 L2A is freely available from the Copernicus Data Space.

## Analysis summary

  Observations                110 composite topsoil samples, 0-20 cm
  Predictors                  {s01['n_predictors']} (10 reflectance bands + 10 spectral
                              indices, 2 acquisitions), numerical rank {s01['numerical_rank']}
  Primary validation          nested cross-validation, leave-one-block-out over
                              {s01['n_blocks']} spatial blocks; all tuning inside the
                              inner GroupKFold(5) loop on training blocks only
  Fold sizes                  {', '.join(str(n) for n in s01['fold_sizes'])}
  Median block separation     {s01['median_block_separation_km']:.2f} km
  Prediction grid             10 m, {msum['n_valid_pixels']:,} valid pixels,
                              {msum['mapped_area_ha']:,.0f} ha
  Raster CRS                  EPSG:4326 (WGS 84); figures drawn in EPSG:26191
                              (Merchich / Nord Maroc)
  Area of applicability       {msum['pct_inside_aoa']:.1f} % of the mapped area
                              ({msum['ha_inside_aoa']:,.0f} ha) inside the domain
  Random seed                 42 throughout

## Corrections applied in this revision

Three predictor-construction errors present in the previously submitted version
were found during the audit prompted by referee comment M5 and are corrected here:

  * the layer labelled SI was computing -(NDMI), not B11 x B12
  * the layer labelled VSSI was computing -(NDSI), not 2*B3 - 5*(B4 + B8)
  * the layers labelled NDSI and MNDWI were mislabelled with respect to their
    formulas; the redundant one has been removed

The predictor count is corrected from 41 to {s01['n_predictors']}, and all results
in this deposit were produced with the corrected set.

## Licence

Data and code are released under CC BY 4.0. Please cite the article.

## Contact

yassine.amrouss@usms.ma
"""
open(os.path.join(DEP, "README.md"), "w", encoding="utf-8").write(readme)
print("wrote README.md and MANIFEST.csv")
print(man.groupby("folder").agg(files=("file", "size"),
                                MB=("size_bytes", lambda s: round(s.sum() / 1e6, 1))).to_string())
print("STEP 08 complete.")
