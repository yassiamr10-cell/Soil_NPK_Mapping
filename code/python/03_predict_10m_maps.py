# -*- coding: utf-8 -*-
"""
STEP 03 - Full-resolution 10 m spatial prediction with uncertainty and
applicability domain, from the corrected 40-predictor set.

Referee comments addressed: M2/M9 (AOA + extrapolation masking), M9 (continuous
10 m surfaces, local uncertainty, class areas, RF-XGB agreement), M8 (masking of
unsupported surfaces via the district mask carried by the covariates).

Reads the 20 Sentinel-2 band rasters (10 bands x 2 dates) at native 10 m from
covariates_clipped, recomputes the 10 indices per date on the fly with the
CORRECTED formulas, and streams predictions window by window.
"""
import numpy as np, os, json, time, sys
import rasterio
from rasterio.windows import Window
from joblib import load
import pandas as pd

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
MAPS  = os.path.join(FINAL, "maps")
COV   = r"d:\Doctorat\article1\covariates_clipped"

DATES   = ["2024_11", "2025_01"]
BANDS   = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
INDICES = ["NDVI", "SAVI", "EVI", "GNDVI", "NDRE", "NDMI", "MNDWI", "BSI", "SI", "VSSI"]
PRED    = [f"{v}_{d}" for d in DATES for v in BANDS + INDICES]
TARGETS = ["N", "P", "K"]
ROWCHUNK = 100          # raster rows per window
SD_TREES = 120          # trees used for the between-tree dispersion estimate

THRESH = {"N": [1000, 1500, 3000], "P": [15, 30, 60], "K": [40, 80, 120]}


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


def main():
    t0 = time.time()
    os.makedirs(MAPS, exist_ok=True)

    # ---------- training data, models, AOA reference ----------
    df = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
    Xtr = df[PRED].values.astype(np.float64)
    blocks = df["block"].values

    models = {}
    for tgt in TARGETS:
        for algo in ["RF", "XGB"]:
            m = load(os.path.join(FINAL, "models", f"final_{algo}_{tgt}.joblib"))["model"]
            try:
                m.n_jobs = -1           # parallel prediction over the full forest
            except Exception:
                pass
            models[(tgt, algo)] = m
    print("models loaded")

    # AOA machinery (Meyer & Pebesma 2021), weighted by mean permutation importance
    pi = pd.read_csv(os.path.join(RES, "02_permutation_importance.csv"))
    w = (pi.assign(pos=pi.perm_importance.clip(lower=0))
           .groupby("variable").pos.mean().reindex(PRED).fillna(0).values)
    if w.sum() <= 0:
        w = np.ones(len(PRED))
    w = w / w.sum()
    mu, sd = Xtr.mean(0), Xtr.std(0); sd[sd == 0] = 1.0
    Ztr = ((Xtr - mu) / sd) * np.sqrt(w)
    Dtr = np.sqrt(((Ztr[:, None, :] - Ztr[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(Dtr, np.inf)
    dbar = float(Dtr[np.isfinite(Dtr)].mean())
    dk = np.array([Dtr[i][blocks != blocks[i]].min() for i in range(len(Ztr))]) / dbar
    q25, q75 = np.percentile(dk, [25, 75])
    AOA_THR = float(q75 + 1.5 * (q75 - q25))
    Ztr_sq = (Ztr ** 2).sum(1)
    print(f"AOA threshold = {AOA_THR:.4f}  (training DI median {np.median(dk):.3f})")

    # ---------- raster template ----------
    src0 = rasterio.open(os.path.join(COV, f"B2_{DATES[0]}.tif"))
    H, W = src0.height, src0.width
    prof = src0.profile.copy()
    prof.update(dtype="float32", count=1, nodata=np.nan, compress="deflate",
                predictor=3, tiled=True, blockxsize=256, blockysize=256, BIGTIFF="IF_SAFER")
    print(f"grid {W} x {H} = {W*H/1e6:.1f} M pixels @ {src0.res[0]*111320:.1f} m")
    src0.close()

    band_src = {f"{b}_{d}": rasterio.open(os.path.join(COV, f"{b}_{d}.tif"))
                for d in DATES for b in BANDS}

    # ---------- output rasters ----------
    outs = {}
    for tgt in TARGETS:
        outs[f"{tgt}_RF"]    = rasterio.open(os.path.join(MAPS, f"{tgt}_RF_10m.tif"), "w", **prof)
        outs[f"{tgt}_RF_SD"] = rasterio.open(os.path.join(MAPS, f"{tgt}_RF_SD_10m.tif"), "w", **prof)
        outs[f"{tgt}_XGB"]   = rasterio.open(os.path.join(MAPS, f"{tgt}_XGB_10m.tif"), "w", **prof)
    outs["DI"]  = rasterio.open(os.path.join(MAPS, "DI_10m.tif"), "w", **prof)
    outs["AOA"] = rasterio.open(os.path.join(MAPS, "AOA_10m.tif"), "w", **prof)

    # accumulators
    stats = {k: dict(n=0, s=0.0, ss=0.0, mn=np.inf, mx=-np.inf) for k in
             [f"{t}_{m}" for t in TARGETS for m in ("RF", "XGB", "RF_SD")] + ["DI"]}
    hist = {t: {m: np.zeros(4, np.int64) for m in ("RF", "XGB")} for t in TARGETS}
    hist_aoa = {t: np.zeros(4, np.int64) for t in TARGETS}
    agree = {t: np.zeros((4, 4), np.int64) for t in TARGETS}
    n_valid = 0; n_inside = 0
    di_samples = []

    rf_trees = {t: models[(t, "RF")].estimators_ for t in TARGETS}
    print(f"RF trees per model: {len(rf_trees['N'])}  "
          f"(dispersion estimated from {min(SD_TREES, len(rf_trees['N']))})")

    nwin = int(np.ceil(H / ROWCHUNK))
    for wi in range(nwin):
        r0 = wi * ROWCHUNK
        nr = min(ROWCHUNK, H - r0)
        win = Window(0, r0, W, nr)

        bands = {}
        for d in DATES:
            for b in BANDS:
                bands[f"{b}_{d}"] = band_src[f"{b}_{d}"].read(1, window=win).astype(np.float32)

        valid = np.ones((nr, W), bool)
        for a in bands.values():
            valid &= np.isfinite(a)
        nv = int(valid.sum())

        blank = np.full((nr, W), np.nan, np.float32)
        if nv == 0:
            for k in outs:
                outs[k].write(blank, 1, window=win)
            continue

        cols = []
        for d in DATES:
            bd = {b: bands[f"{b}_{d}"] for b in BANDS}
            idx = indices_from_bands(bd)
            for v in BANDS:
                cols.append(bd[v][valid])
            for v in INDICES:
                cols.append(idx[v][valid].astype(np.float32))
        Xp = np.stack(cols, 1).astype(np.float32)
        del cols, bands

        # ---- DI / AOA ----
        Zp = ((Xp.astype(np.float64) - mu) / sd) * np.sqrt(w)
        DI = np.empty(nv, np.float32)
        CH = 60000
        Zp_sq = (Zp ** 2).sum(1)
        for s in range(0, nv, CH):
            e = min(s + CH, nv)
            d2 = Zp_sq[s:e, None] - 2.0 * (Zp[s:e] @ Ztr.T) + Ztr_sq[None, :]
            DI[s:e] = np.sqrt(np.maximum(d2.min(1), 0))
        DI /= dbar
        del Zp, d2
        inside = DI <= AOA_THR

        a = blank.copy(); a[valid] = DI; outs["DI"].write(a, 1, window=win)
        a = blank.copy(); a[valid] = inside.astype(np.float32); outs["AOA"].write(a, 1, window=win)

        st = stats["DI"]; st["n"] += nv; st["s"] += float(DI.sum()); st["ss"] += float((DI.astype(np.float64)**2).sum())
        st["mn"] = min(st["mn"], float(DI.min())); st["mx"] = max(st["mx"], float(DI.max()))
        n_valid += nv; n_inside += int(inside.sum())
        if wi % 4 == 0 and nv > 0:
            di_samples.append(DI[::max(1, nv // 2000)])

        # ---- predictions ----
        # mean from the complete forest (parallel); between-tree SD estimated from a
        # fixed subsample of SD_TREES trees, which is ample for a dispersion estimate
        for tgt in TARGETS:
            mean = models[(tgt, "RF")].predict(Xp).astype(np.float32)
            sub = rf_trees[tgt][:SD_TREES]
            ssum = np.zeros(nv, np.float64); ssq = np.zeros(nv, np.float64)
            for t in sub:
                pr = t.predict(Xp)
                ssum += pr; ssq += pr * pr
            nt = len(sub)
            var = np.maximum(ssq / nt - (ssum / nt) ** 2, 0)
            sdv = np.sqrt(var).astype(np.float32)
            xgbp = models[(tgt, "XGB")].predict(Xp).astype(np.float32)

            for nm, arr in (("RF", mean), ("RF_SD", sdv), ("XGB", xgbp)):
                a = blank.copy(); a[valid] = arr
                outs[f"{tgt}_{nm}"].write(a, 1, window=win)
                st = stats[f"{tgt}_{nm}"]
                st["n"] += nv; st["s"] += float(arr.sum())
                st["ss"] += float((arr.astype(np.float64) ** 2).sum())
                st["mn"] = min(st["mn"], float(arr.min())); st["mx"] = max(st["mx"], float(arr.max()))

            th = THRESH[tgt]
            crf = np.digitize(mean, th); cxg = np.digitize(xgbp, th)
            hist[tgt]["RF"] += np.bincount(crf, minlength=4)
            hist[tgt]["XGB"] += np.bincount(cxg, minlength=4)
            hist_aoa[tgt] += np.bincount(crf[inside], minlength=4)
            np.add.at(agree[tgt], (crf, cxg), 1)

        del Xp
        if wi % 5 == 0 or wi == nwin - 1:
            print(f"  window {wi+1}/{nwin}  rows {r0}-{r0+nr}  valid {nv:>8d}  "
                  f"[{time.time()-t0:7.1f}s]", flush=True)

    for s in band_src.values():
        s.close()
    for o in outs.values():
        o.close()

    # ---------- summaries ----------
    with rasterio.open(os.path.join(MAPS, "N_RF_10m.tif")) as r:
        px_m = r.res[0] * 111320 * np.cos(np.radians((r.bounds.bottom + r.bounds.top) / 2))
        py_m = r.res[1] * 110574
        px_ha = px_m * py_m / 1e4
        crs_txt = str(r.crs)
    print(f"\npixel {px_m:.2f} x {py_m:.2f} m = {px_ha:.5f} ha ; CRS {crs_txt}")

    summ = []
    for k, st in stats.items():
        if st["n"] == 0: continue
        m = st["s"] / st["n"]
        v = max(st["ss"] / st["n"] - m * m, 0)
        summ.append(dict(layer=k, n_pixels=st["n"], min=st["mn"], max=st["mx"],
                         mean=m, sd=np.sqrt(v)))
    sm = pd.DataFrame(summ)
    sm.to_csv(os.path.join(RES, "03_raster_summary.csv"), index=False)
    print("\n=== RASTER SUMMARY ===")
    print(sm.round(3).to_string(index=False))

    names = ["Very low", "Low", "Medium", "High"]
    rows = []
    for tgt in TARGETS:
        tot = hist[tgt]["RF"].sum()
        tot_a = hist_aoa[tgt].sum()
        for i, nm in enumerate(names):
            rows.append(dict(nutrient=tgt, cls=nm,
                             rf_ha=hist[tgt]["RF"][i] * px_ha,
                             rf_pct=100 * hist[tgt]["RF"][i] / tot,
                             xgb_ha=hist[tgt]["XGB"][i] * px_ha,
                             xgb_pct=100 * hist[tgt]["XGB"][i] / tot,
                             rf_inAOA_ha=hist_aoa[tgt][i] * px_ha,
                             rf_inAOA_pct=100 * hist_aoa[tgt][i] / tot_a))
    ca = pd.DataFrame(rows)
    ca.to_csv(os.path.join(RES, "03_class_areas.csv"), index=False)
    print("\n=== CLASS AREAS ===")
    print(ca.round(2).to_string(index=False))

    ag_rows = []
    for tgt in TARGETS:
        cm = agree[tgt]; n = cm.sum()
        po = np.trace(cm) / n
        pe = (cm.sum(0) * cm.sum(1)).sum() / n ** 2
        kap = (po - pe) / (1 - pe)
        ag_rows.append(dict(nutrient=tgt, overall_agreement=po, kappa=kap, n_pixels=int(n)))
        pd.DataFrame(cm, index=names, columns=names).to_csv(
            os.path.join(RES, f"03_RF_XGB_agreement_{tgt}.csv"))
    ag = pd.DataFrame(ag_rows)
    ag.to_csv(os.path.join(RES, "03_RF_XGB_agreement_summary.csv"), index=False)
    print("\n=== RF vs XGB MAP AGREEMENT ===")
    print(ag.round(4).to_string(index=False))

    di_all = np.concatenate(di_samples) if di_samples else np.array([0.0])
    js = dict(crs=crs_txt, pixel_x_m=round(float(px_m), 3), pixel_y_m=round(float(py_m), 3),
              pixel_ha=round(float(px_ha), 6), n_valid_pixels=int(n_valid),
              mapped_area_ha=round(float(n_valid * px_ha), 1),
              aoa_threshold=AOA_THR, n_inside_aoa=int(n_inside),
              pct_inside_aoa=round(100 * n_inside / n_valid, 2),
              ha_inside_aoa=round(float(n_inside * px_ha), 1),
              ha_outside_aoa=round(float((n_valid - n_inside) * px_ha), 1),
              di_median=float(np.median(di_all)))
    json.dump(js, open(os.path.join(RES, "03_map_summary.json"), "w"), indent=2)
    print("\n=== MAP SUMMARY ===")
    print(json.dumps(js, indent=2))
    print(f"\nSTEP 03 complete in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
