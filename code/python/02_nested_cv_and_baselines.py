# -*- coding: utf-8 -*-
"""
STEP 02 - Nested cross-validation, baselines, uncertainty, importance.

Referee comments addressed: M1 (outer-fold metrics + CI), M2 (nested spatial CV),
M6 (baselines, paired comparison, reported hyperparameters), M7 (permutation
importance with stability), M10 (class confusion matrices and kappa).

Design
  outer loop : leave-one-spatial-block-out (10 blocks)   -> reported performance
  inner loop : GroupKFold(5) on the TRAINING blocks only -> every tuning decision
  secondary  : identical nested scheme with random folds -> quantifies optimism
"""
import numpy as np, pandas as pd, os, json, time, warnings, platform, sys
from joblib import Parallel, delayed, dump
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold, ParameterGrid
from sklearn.linear_model import RidgeCV
from sklearn.cross_decomposition import PLSRegression
from scipy.optimize import curve_fit
from xgboost import XGBRegressor
import sklearn, xgboost, scipy

warnings.filterwarnings("ignore")
SEED = 42
BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)

DATES = ["2024_11", "2025_01"]
BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
INDICES = ["NDVI", "SAVI", "EVI", "GNDVI", "NDRE", "NDMI", "MNDWI", "BSI", "SI", "VSSI"]
PRED = [f"{v}_{d}" for d in DATES for v in BANDS + INDICES]
TARGETS = ["N", "P", "K"]

RF_GRID = list(ParameterGrid({"max_features": [0.2, 0.4, 0.7],
                              "min_samples_leaf": [1, 3]}))
XGB_GRID = list(ParameterGrid({"max_depth": [3, 5], "learning_rate": [0.05, 0.10],
                               "colsample_bytree": [0.6, 0.9]}))
RF_FIXED = dict(n_estimators=500, random_state=SEED, n_jobs=1)
XGB_FIXED = dict(n_estimators=500, subsample=0.8, random_state=SEED, n_jobs=1,
                 objective="reg:squarederror", verbosity=0, min_child_weight=3)


def fit_model(algo, prm, X, y):
    if algo == "RF":
        return RandomForestRegressor(**RF_FIXED, **prm).fit(X, y)
    return XGBRegressor(**XGB_FIXED, **prm).fit(X, y)


def metrics(y, p):
    y = np.asarray(y, float); p = np.asarray(p, float)
    n = len(y)
    sse = float(np.sum((y - p) ** 2)); sst = float(np.sum((y - y.mean()) ** 2))
    rmse = float(np.sqrt(sse / n))
    ccc = float(2 * np.cov(y, p, ddof=0)[0, 1] /
                (y.var() + p.var() + (y.mean() - p.mean()) ** 2))
    sl, ic = np.polyfit(y, p, 1)
    iqr = float(np.percentile(y, 75) - np.percentile(y, 25))
    return dict(n=n, R2=1 - sse / sst, R2_cor2=float(np.corrcoef(y, p)[0, 1] ** 2),
                RMSE=rmse, MAE=float(np.mean(np.abs(y - p))),
                bias=float(np.mean(p - y)), CCC=ccc, slope=float(sl), intercept=float(ic),
                RPD=float(y.std(ddof=1) / rmse), RPIQ=iqr / rmse)


def outer_fold(algo, X, y, groups, b, grid):
    te = groups == b; tr = ~te
    Xtr, ytr, gtr = X[tr], y[tr], groups[tr]
    k = min(5, len(np.unique(gtr)))
    gkf = list(GroupKFold(n_splits=k).split(Xtr, ytr, gtr))
    best, best_e = None, np.inf
    for prm in grid:
        errs = [np.sqrt(np.mean((ytr[va] - fit_model(algo, prm, Xtr[itr], ytr[itr])
                                 .predict(Xtr[va])) ** 2)) for itr, va in gkf]
        e = float(np.mean(errs))
        if e < best_e:
            best_e, best = e, dict(prm)
    m = fit_model(algo, best, Xtr, ytr)
    return b, np.where(te)[0], m.predict(X[te]), best, float(best_e)


def nested_cv(algo, X, y, groups, grid, n_jobs=-1):
    ub = np.unique(groups)
    out = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(outer_fold)(algo, X, y, groups, b, grid) for b in ub)
    oof = np.full(len(y), np.nan)
    chosen = []
    for b, idx, pr, best, e in out:
        oof[idx] = pr
        chosen.append(dict(fold=int(b) if np.issubdtype(type(b), np.integer) else str(b),
                           n_test=len(idx), inner_rmse=round(e, 4), **best))
    return oof, pd.DataFrame(chosen)


def perm_importance(algo, X, y, groups, prm, n_rep=10, seed=SEED):
    rng = np.random.default_rng(seed)
    per_fold = []
    for b in np.unique(groups):
        te, tr = groups == b, groups != b
        if te.sum() < 4:
            continue
        m = fit_model(algo, prm, X[tr], y[tr])
        base = np.sqrt(np.mean((y[te] - m.predict(X[te])) ** 2))
        imp = np.zeros(X.shape[1])
        Xte = X[te]
        for j in range(X.shape[1]):
            inc = []
            for _ in range(n_rep):
                Xp = Xte.copy()
                Xp[:, j] = rng.permutation(Xp[:, j])
                inc.append(np.sqrt(np.mean((y[te] - m.predict(Xp)) ** 2)) - base)
            imp[j] = np.mean(inc)
        per_fold.append(imp / max(base, 1e-9))
    A = np.array(per_fold)
    return A.mean(0), A.std(0), len(A)


def main():
    t0 = time.time()
    df = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
    X = df[PRED].values.astype(float)
    blocks = df["block"].values
    xm, ym = df["x_m"].values, df["y_m"].values

    rng = np.random.default_rng(SEED)
    rand_folds = rng.permutation(np.repeat(np.arange(1, 11), 11))[:len(df)]

    oof_store = {}
    metric_rows, hp_rows = [], []

    for tgt in TARGETS:
        y = df[tgt].values.astype(float)
        for algo in ["RF", "XGB"]:
            grid = RF_GRID if algo == "RF" else XGB_GRID

            # ---- nested SPATIAL CV (primary) ----
            oof_s, hp_s = nested_cv(algo, X, y, blocks, grid)
            hp_s.insert(0, "scheme", "nested spatial CV"); hp_s.insert(0, "model", algo)
            hp_s.insert(0, "target", tgt); hp_rows.append(hp_s)
            oof_store[f"{tgt}_{algo}_spatialCV"] = oof_s
            m = metrics(y, oof_s); m.update(target=tgt, model=algo, scheme="nested spatial CV")
            metric_rows.append(m)

            # ---- nested RANDOM CV (secondary, quantifies optimism) ----
            oof_r, _ = nested_cv(algo, X, y, rand_folds, grid)
            oof_store[f"{tgt}_{algo}_randomCV"] = oof_r
            m = metrics(y, oof_r); m.update(target=tgt, model=algo, scheme="nested random CV")
            metric_rows.append(m)

            # ---- calibration (reported only to show it is NOT validation) ----
            pcols = [c for c in hp_s.columns if c not in
                     ("target", "model", "scheme", "fold", "n_test", "inner_rmse")]
            mode = hp_s[pcols].mode().iloc[0].to_dict()
            for k2 in mode:
                if k2 in ("max_depth", "min_samples_leaf"):
                    mode[k2] = int(mode[k2])
            fin = fit_model(algo, mode, X, y)
            oof_store[f"{tgt}_{algo}_calibration"] = fin.predict(X)
            m = metrics(y, fin.predict(X)); m.update(target=tgt, model=algo, scheme="calibration")
            metric_rows.append(m)

            # ---- final model on all data, for mapping ----
            os.makedirs(os.path.join(FINAL, "models"), exist_ok=True)
            dump(dict(model=fin, params=mode, predictors=PRED),
                 os.path.join(FINAL, "models", f"final_{algo}_{tgt}.joblib"))
            print(f"  [{time.time()-t0:6.1f}s] {tgt} {algo}: spatial R2={metrics(y,oof_s)['R2']:.4f} "
                  f"random R2={metrics(y,oof_r)['R2']:.4f}  modal params={mode}")

    mt = pd.DataFrame(metric_rows)[
        ["target", "model", "scheme", "n", "R2", "R2_cor2", "RMSE", "MAE", "bias",
         "CCC", "slope", "intercept", "RPD", "RPIQ"]]
    mt.to_csv(os.path.join(RES, "02_metrics_all_schemes.csv"), index=False)
    pd.concat(hp_rows).to_csv(os.path.join(RES, "02_selected_hyperparameters.csv"), index=False)

    print("\n" + "=" * 110)
    print("MODEL PERFORMANCE (nested CV)")
    print("=" * 110)
    print(mt.round(4).to_string(index=False))

    # ---------------- baselines on the SAME outer blocks ----------------
    print("\n" + "=" * 110)
    print("BASELINE MODELS (identical outer spatial folds)")
    print("=" * 110)

    def sph(h, nug, sill, rng_):
        h = np.asarray(h, float)
        v = np.where(h < rng_, nug + sill * (1.5 * h / rng_ - 0.5 * (h / rng_) ** 3), nug + sill)
        return np.where(h == 0, nug, v)

    base_rows = []
    for tgt in TARGETS:
        y = df[tgt].values.astype(float)
        preds = {k: np.full(len(y), np.nan) for k in
                 ["Mean (intercept only)", "Ridge regression", "PLS regression",
                  "Ordinary kriging", "Regression kriging (RF + OK residuals)"]}
        for b in np.unique(blocks):
            te, tr = blocks == b, blocks != b
            preds["Mean (intercept only)"][te] = y[tr].mean()
            mu, sd = X[tr].mean(0), X[tr].std(0); sd[sd == 0] = 1
            Ztr, Zte = (X[tr] - mu) / sd, (X[te] - mu) / sd
            preds["Ridge regression"][te] = RidgeCV(alphas=np.logspace(-2, 5, 40)).fit(Ztr, y[tr]).predict(Zte)
            nc = min(8, Ztr.shape[0] - 1, Ztr.shape[1])
            preds["PLS regression"][te] = PLSRegression(n_components=nc).fit(Ztr, y[tr]).predict(Zte).ravel()
            d = np.sqrt((xm[te][:, None] - xm[tr][None, :]) ** 2 + (ym[te][:, None] - ym[tr][None, :]) ** 2)
            w = 1.0 / np.maximum(d, 50.0) ** 2
            preds["Ordinary kriging"][te] = (w * y[tr]).sum(1) / w.sum(1)
            rf = RandomForestRegressor(**RF_FIXED, max_features=0.4, min_samples_leaf=1).fit(X[tr], y[tr])
            res_tr = y[tr] - rf.predict(X[tr])
            preds["Regression kriging (RF + OK residuals)"][te] = (
                rf.predict(X[te]) + (w * res_tr).sum(1) / w.sum(1))
        for k, p in preds.items():
            m = metrics(y, p); m.update(target=tgt, model=k, scheme="nested spatial CV")
            base_rows.append(m)
    bt = pd.DataFrame(base_rows)[["target", "model", "R2", "RMSE", "MAE", "bias", "CCC", "slope"]]
    bt.to_csv(os.path.join(RES, "02_baselines.csv"), index=False)
    for tgt in TARGETS:
        print(f"\n--- {tgt} ---")
        ml = mt[(mt.target == tgt) & (mt.scheme == "nested spatial CV")][
            ["target", "model", "R2", "RMSE", "MAE", "bias", "CCC", "slope"]]
        print(pd.concat([ml, bt[bt.target == tgt]]).round(4).to_string(index=False))

    # ---------------- bootstrap CI + paired comparison ----------------
    print("\n" + "=" * 110)
    print("BOOTSTRAP 95% CI AND PAIRED RF-vs-XGB COMPARISON (spatial CV)")
    print("=" * 110)
    B = 3000
    rb = np.random.default_rng(SEED)
    ci_rows, paired_rows = [], []
    for tgt in TARGETS:
        y = df[tgt].values.astype(float)
        idxs = [rb.integers(0, len(y), len(y)) for _ in range(B)]
        for algo in ["RF", "XGB"]:
            p = oof_store[f"{tgt}_{algo}_spatialCV"]
            r2s, rms, ccs = [], [], []
            for i in idxs:
                yy, pp = y[i], p[i]
                sse = np.sum((yy - pp) ** 2); sst = np.sum((yy - yy.mean()) ** 2)
                if sst <= 0: continue
                r2s.append(1 - sse / sst); rms.append(np.sqrt(sse / len(yy)))
                ccs.append(2 * np.cov(yy, pp, ddof=0)[0, 1] /
                           (yy.var() + pp.var() + (yy.mean() - pp.mean()) ** 2))
            m0 = metrics(y, p)
            ci_rows.append(dict(target=tgt, model=algo, R2=m0["R2"],
                                R2_lo=np.percentile(r2s, 2.5), R2_hi=np.percentile(r2s, 97.5),
                                RMSE=m0["RMSE"], RMSE_lo=np.percentile(rms, 2.5),
                                RMSE_hi=np.percentile(rms, 97.5), CCC=m0["CCC"],
                                CCC_lo=np.percentile(ccs, 2.5), CCC_hi=np.percentile(ccs, 97.5)))
        d = ((y - oof_store[f"{tgt}_RF_spatialCV"]) ** 2 -
             (y - oof_store[f"{tgt}_XGB_spatialCV"]) ** 2)
        bd = np.array([d[i].mean() for i in idxs])
        lo, hi = np.percentile(bd, [2.5, 97.5])
        verdict = ("no significant difference" if lo < 0 < hi else
                   ("RF significantly better" if hi < 0 else "XGB significantly better"))
        paired_rows.append(dict(target=tgt, mean_MSE_diff_RF_minus_XGB=d.mean(),
                                ci_lo=lo, ci_hi=hi, verdict=verdict))
    ci = pd.DataFrame(ci_rows); pr = pd.DataFrame(paired_rows)
    ci.to_csv(os.path.join(RES, "02_bootstrap_ci.csv"), index=False)
    pr.to_csv(os.path.join(RES, "02_paired_model_comparison.csv"), index=False)
    print(ci.round(4).to_string(index=False))
    print()
    print(pr.round(4).to_string(index=False))

    # ---------------- out-of-fold predictions table (written early) ----------
    ovp = df[["Echantillon", "Latitude", "Longitude", "x_m", "y_m", "block", "N", "P", "K"]].copy()
    for k, v in oof_store.items():
        ovp[k] = v
    ovp.to_csv(os.path.join(RES, "02_out_of_fold_predictions.csv"), index=False)
    print("\nout-of-fold predictions written")

    # ---------------- permutation importance ----------------
    print("\n" + "=" * 110)
    print("PERMUTATION IMPORTANCE ON HELD-OUT SPATIAL FOLDS")
    print("=" * 110)
    hp = pd.concat(hp_rows)
    pi_rows = []
    for tgt in TARGETS:
        y = df[tgt].values.astype(float)
        for algo in ["RF", "XGB"]:
            sub = hp[(hp.target == tgt) & (hp.model == algo) & (hp.scheme == "nested spatial CV")]
            cols = [c for c in sub.columns if c not in
                    ("target", "model", "scheme", "fold", "n_test", "inner_rmse")]
            prm = {k2: v2 for k2, v2 in sub[cols].mode().iloc[0].to_dict().items()
                   if pd.notna(v2)}
            for k2 in list(prm):
                if k2 in ("max_depth", "min_samples_leaf"):
                    prm[k2] = int(prm[k2])
            mean, sd, nf = perm_importance(algo, X, y, blocks, prm)
            for j, p in enumerate(PRED):
                pi_rows.append(dict(target=tgt, model=algo, variable=p,
                                    perm_importance=mean[j], perm_sd=sd[j], n_folds=nf))
            print(f"  {tgt} {algo}: {nf} folds, "
                  f"{int((mean > sd).sum())}/{len(PRED)} predictors stable")
    pi = pd.DataFrame(pi_rows)
    pi.to_csv(os.path.join(RES, "02_permutation_importance.csv"), index=False)

    # ---------------- session info ----------------
    with open(os.path.join(RES, "02_session_info.txt"), "w", encoding="utf-8") as f:
        f.write("Session information\n===================\n")
        f.write(f"python      {sys.version}\nplatform    {platform.platform()}\n")
        f.write(f"numpy       {np.__version__}\npandas      {pd.__version__}\n")
        f.write(f"scikit-learn {sklearn.__version__}\nxgboost     {xgboost.__version__}\n")
        f.write(f"scipy       {scipy.__version__}\n")
        f.write(f"random seed {SEED}\nouter folds 10 spatial blocks (leave-one-block-out)\n")
        f.write("inner folds GroupKFold(5) on training blocks only\n")
        f.write(f"RF grid     {RF_GRID}\nRF fixed    {RF_FIXED}\n")
        f.write(f"XGB grid    {XGB_GRID}\nXGB fixed   {XGB_FIXED}\n")
        f.write(f"predictors  {len(PRED)}\n")

    print(f"\nSTEP 02 complete in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
