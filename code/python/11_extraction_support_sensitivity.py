# -*- coding: utf-8 -*-
"""
STEP 11 - Extraction-support sensitivity test (referee comment M3).

Re-extracts every predictor as the mean of a 3 x 3 pixel neighbourhood (nominal
30 m) instead of the single pixel containing the sample centroid, rebuilds the
predictor set with the corrected index formulas, and re-runs the identical
nested spatial block cross-validation. This brackets the combined effect of the
+/- 3 m GPS uncertainty, the 10 m composite sampling radius and the 20 m native
support of the red-edge and SWIR bands.
"""
import numpy as np, pandas as pd, os, time, warnings
import rasterio
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold, ParameterGrid
warnings.filterwarnings("ignore")

SEED = 42
BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
COV   = r"d:\Doctorat\article1\covariates_clipped"

DATES = ["2024_11", "2025_01"]
BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
INDICES = ["NDVI", "SAVI", "EVI", "GNDVI", "NDRE", "NDMI", "MNDWI", "BSI", "SI", "VSSI"]
PRED = [f"{v}_{d}" for d in DATES for v in BANDS + INDICES]
TARGETS = ["N", "P", "K"]

RF_GRID = list(ParameterGrid({"max_features": [0.2, 0.4, 0.7],
                              "min_samples_leaf": [1, 3]}))
RF_FIXED = dict(n_estimators=500, random_state=SEED, n_jobs=1)


def indices_from_bands(b):
    eps = 1e-9
    B2, B3, B4, B5, B8, B8A, B11, B12 = (b["B2"], b["B3"], b["B4"], b["B5"],
                                         b["B8"], b["B8A"], b["B11"], b["B12"])
    return {
        "NDVI":  (B8 - B4) / (B8 + B4 + eps),
        "SAVI":  1.5 * (B8 - B4) / (B8 + B4 + 0.5),
        "EVI":   2.5 * (B8 - B4) / (B8 + 6.0 * B4 - 7.5 * B2 + 1.0),
        "GNDVI": (B8 - B3) / (B8 + B3 + eps),
        "NDRE":  (B8A - B5) / (B8A + B5 + eps),
        "NDMI":  (B8 - B11) / (B8 + B11 + eps),
        "MNDWI": (B3 - B11) / (B3 + B11 + eps),
        "BSI":   ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2) + eps),
        "SI":    B11 * B12,
        "VSSI":  2.0 * B3 - 5.0 * (B4 + B8),
    }


def metrics(y, p):
    y = np.asarray(y, float); p = np.asarray(p, float)
    sse = float(np.sum((y - p) ** 2)); sst = float(np.sum((y - y.mean()) ** 2))
    rmse = float(np.sqrt(sse / len(y)))
    ccc = float(2 * np.cov(y, p, ddof=0)[0, 1] /
                (y.var() + p.var() + (y.mean() - p.mean()) ** 2))
    sl, ic = np.polyfit(y, p, 1)
    return dict(R2=1 - sse / sst, RMSE=rmse, MAE=float(np.mean(np.abs(y - p))),
                bias=float(np.mean(p - y)), CCC=ccc, slope=float(sl))


def outer_fold(X, y, groups, b):
    te = groups == b; tr = ~te
    Xtr, ytr, gtr = X[tr], y[tr], groups[tr]
    gkf = list(GroupKFold(n_splits=min(5, len(np.unique(gtr)))).split(Xtr, ytr, gtr))
    best, best_e = None, np.inf
    for prm in RF_GRID:
        e = np.mean([np.sqrt(np.mean((ytr[va] - RandomForestRegressor(**RF_FIXED, **prm)
                                      .fit(Xtr[itr], ytr[itr]).predict(Xtr[va])) ** 2))
                     for itr, va in gkf])
        if e < best_e:
            best_e, best = e, dict(prm)
    m = RandomForestRegressor(**RF_FIXED, **best).fit(Xtr, ytr)
    return np.where(te)[0], m.predict(X[te])


def nested_spatial(X, y, groups):
    out = Parallel(n_jobs=-1)(delayed(outer_fold)(X, y, groups, b)
                              for b in np.unique(groups))
    oof = np.full(len(y), np.nan)
    for idx, pr in out:
        oof[idx] = pr
    return oof


def main():
    t0 = time.time()
    df = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
    lon, lat = df.Longitude.values, df.Latitude.values

    # ---------------- 3 x 3 neighbourhood extraction ----------------
    print("Extracting 3 x 3 neighbourhood means from the 10 m band rasters ...")
    nb = {}
    for d in DATES:
        for b in BANDS:
            with rasterio.open(os.path.join(COV, f"{b}_{d}.tif")) as src:
                vals = np.empty(len(df))
                for i, (x, y_) in enumerate(zip(lon, lat)):
                    r, c = src.index(x, y_)
                    w = rasterio.windows.Window(c - 1, r - 1, 3, 3)
                    a = src.read(1, window=w, boundless=True, fill_value=np.nan)
                    vals[i] = np.nanmean(a)
            nb[f"{b}_{d}"] = vals
        print(f"   {d} done  [{time.time()-t0:.0f}s]")

    n3 = df[["Echantillon", "Latitude", "Longitude", "N", "P", "K", "block"]].copy()
    for d in DATES:
        bd = {b: nb[f"{b}_{d}"] for b in BANDS}
        for b in BANDS:
            n3[f"{b}_{d}"] = bd[b]
        for k, v in indices_from_bands(bd).items():
            n3[f"{k}_{d}"] = v
    n3.to_csv(os.path.join(RES, "11_dataset_3x3_neighbourhood.csv"), index=False)

    # how different are the two extractions?
    cmp_rows = []
    for p in PRED:
        a, b_ = df[p].values.astype(float), n3[p].values.astype(float)
        cmp_rows.append(dict(predictor=p, r=np.corrcoef(a, b_)[0, 1],
                             mean_abs_diff=np.mean(np.abs(a - b_)),
                             rel_diff_pct=100 * np.mean(np.abs(a - b_)) /
                                          max(np.mean(np.abs(a)), 1e-12)))
    cmpd = pd.DataFrame(cmp_rows)
    cmpd.to_csv(os.path.join(RES, "11_extraction_agreement.csv"), index=False)
    print(f"\nAgreement between single-pixel and 3 x 3 extraction across "
          f"{len(PRED)} predictors:")
    print(f"   Pearson r : min {cmpd.r.min():.4f}  median {cmpd.r.median():.4f}  "
          f"max {cmpd.r.max():.4f}")
    print(f"   mean relative difference : median {cmpd.rel_diff_pct.median():.2f} %  "
          f"max {cmpd.rel_diff_pct.max():.2f} %")
    print("\n   five predictors least stable to extraction support:")
    print(cmpd.nsmallest(5, "r")[["predictor", "r", "rel_diff_pct"]].round(4)
          .to_string(index=False))

    # ---------------- re-run the identical validation ----------------
    groups = df["block"].values
    rows = []
    for tgt in TARGETS:
        y = df[tgt].values.astype(float)
        for label, D in [("single pixel (10 m)", df), ("3 x 3 mean (30 m)", n3)]:
            X = D[PRED].values.astype(float)
            oof = nested_spatial(X, y, groups)
            m = metrics(y, oof)
            m.update(target=tgt, extraction=label)
            rows.append(m)
            print(f"   [{time.time()-t0:6.0f}s] {tgt} {label:22s} "
                  f"R2={m['R2']:.4f}  RMSE={m['RMSE']:9.3f}")

    res = pd.DataFrame(rows)[["target", "extraction", "R2", "RMSE", "MAE", "bias",
                              "CCC", "slope"]]
    res.to_csv(os.path.join(RES, "11_extraction_support_sensitivity.csv"), index=False)

    print("\n" + "=" * 92)
    print("EXTRACTION-SUPPORT SENSITIVITY (Random Forest, nested spatial block CV)")
    print("=" * 92)
    print(res.round(4).to_string(index=False))
    print()
    for tgt in TARGETS:
        a = res[(res.target == tgt) & (res.extraction == "single pixel (10 m)")].iloc[0]
        b_ = res[(res.target == tgt) & (res.extraction == "3 x 3 mean (30 m)")].iloc[0]
        print(f"   {tgt}: dR2 = {b_.R2 - a.R2:+.4f}   dRMSE = {b_.RMSE - a.RMSE:+.3f} "
              f"({100*(b_.RMSE - a.RMSE)/a.RMSE:+.1f} %)")
    print(f"\nSTEP 11 complete in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
