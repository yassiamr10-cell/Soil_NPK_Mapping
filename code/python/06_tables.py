# -*- coding: utf-8 -*-
"""
STEP 06 - Build every manuscript / supplementary table into one Excel workbook
and matching CSVs.
"""
import numpy as np, pandas as pd, os, json

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
TAB   = os.path.join(FINAL, "tables")
os.makedirs(TAB, exist_ok=True)
TARGETS = ["N", "P", "K"]
CLS = ["Very low", "Low", "Medium", "High"]
TH = {"N": [1000, 1500, 3000], "P": [15, 30, 60], "K": [40, 80, 120]}

df   = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
inv  = pd.read_csv(os.path.join(RES, "01_predictor_inventory.csv"))
bdes = pd.read_csv(os.path.join(RES, "01_block_design.csv"))
mt   = pd.read_csv(os.path.join(RES, "02_metrics_all_schemes.csv"))
bl   = pd.read_csv(os.path.join(RES, "02_baselines.csv"))
ci   = pd.read_csv(os.path.join(RES, "02_bootstrap_ci.csv"))
pcmp = pd.read_csv(os.path.join(RES, "02_paired_model_comparison.csv"))
hp   = pd.read_csv(os.path.join(RES, "02_selected_hyperparameters.csv"))
pi   = pd.read_csv(os.path.join(RES, "02_permutation_importance.csv"))
ovp  = pd.read_csv(os.path.join(RES, "02_out_of_fold_predictions.csv"))
vg   = pd.read_csv(os.path.join(RES, "04_variogram_parameters.csv"))
mor  = pd.read_csv(os.path.join(RES, "04_morans_I.csv"))
ras  = pd.read_csv(os.path.join(RES, "03_raster_summary.csv"))
care = pd.read_csv(os.path.join(RES, "03_class_areas.csv"))
agr  = pd.read_csv(os.path.join(RES, "03_RF_XGB_agreement_summary.csv"))
msum = json.load(open(os.path.join(RES, "03_map_summary.json")))

T = {}

# ---------------- Table 1 : Sentinel-2 bands -------------------------------
T["T1_Sentinel2_bands"] = pd.DataFrame([
    ["B2",  "Blue",        490,  10, "10 m", "none"],
    ["B3",  "Green",       560,  10, "10 m", "none"],
    ["B4",  "Red",         665,  10, "10 m", "none"],
    ["B5",  "Red edge 1",  705,  20, "10 m", "bilinear"],
    ["B6",  "Red edge 2",  740,  20, "10 m", "bilinear"],
    ["B7",  "Red edge 3",  783,  20, "10 m", "bilinear"],
    ["B8",  "NIR",         842,  10, "10 m", "none"],
    ["B8A", "Narrow NIR",  865,  20, "10 m", "bilinear"],
    ["B11", "SWIR 1",     1610,  20, "10 m", "bilinear"],
    ["B12", "SWIR 2",     2190,  20, "10 m", "bilinear"],
], columns=["Band", "Name", "Central wavelength (nm)", "Native resolution (m)",
            "Output resolution", "Resampling"])

# ---------------- Table 2 : corrected predictor inventory ------------------
T["T2_predictor_inventory"] = inv

idx2 = (inv[inv.type == "Spectral index"]
        .drop_duplicates("formula")[["variable", "formula", "source_bands",
                                     "native_res_m", "reference"]])
idx2["Index"] = idx2.variable.str.rsplit("_", n=2).str[0]
T["T2b_index_definitions"] = idx2[["Index", "formula", "source_bands",
                                   "native_res_m", "reference"]].rename(columns={
    "formula": "Sentinel-2 formula", "source_bands": "Source bands",
    "native_res_m": "Limiting native resolution (m)", "reference": "Reference"})

# ---------------- Table 3 : descriptive statistics -------------------------
rows = []
for t in TARGETS:
    v = df[t].astype(float)
    rows.append(dict(Nutrient={"N": "Total N (Kjeldahl)", "P": "Available P (Olsen)",
                               "K": "Exchangeable K (NH4OAc)"}[t],
                     Unit="mg kg-1", n=int(v.notna().sum()),
                     Minimum=v.min(), Q1=v.quantile(.25), Median=v.median(),
                     Mean=v.mean(), Q3=v.quantile(.75), Maximum=v.max(),
                     SD=v.std(ddof=1), CV_percent=100 * v.std(ddof=1) / v.mean(),
                     Skewness=v.skew(), Kurtosis=v.kurt()))
T["T3_descriptive_statistics"] = pd.DataFrame(rows).round(3)

# ---------------- Table 4 : model performance ------------------------------
m = mt.copy()
m["scheme"] = pd.Categorical(m.scheme,
                             ["calibration", "nested random CV", "nested spatial CV"], True)
m = m.sort_values(["target", "model", "scheme"])
T["T4_model_performance"] = m[["target", "model", "scheme", "n", "R2", "R2_cor2",
                               "RMSE", "MAE", "bias", "CCC", "slope", "intercept",
                               "RPD", "RPIQ"]].round(4)

c = ci.copy()
for a, b in [("R2", "R2"), ("RMSE", "RMSE"), ("CCC", "CCC")]:
    c[f"{a}_95CI"] = c.apply(lambda r: f"[{r[b+'_lo']:.3f}, {r[b+'_hi']:.3f}]", axis=1)
T["T4b_bootstrap_CI"] = c[["target", "model", "R2", "R2_95CI", "RMSE", "RMSE_95CI",
                           "CCC", "CCC_95CI"]].round(4)
T["T4c_paired_model_test"] = pcmp.round(4)

# ---------------- Table 5 : baselines --------------------------------------
ml = mt[mt.scheme == "nested spatial CV"][["target", "model", "R2", "RMSE", "MAE",
                                           "bias", "CCC", "slope"]]
NPRED = len(inv)
ml = ml.replace({"RF": f"Random Forest ({NPRED} predictors)",
                 "XGB": f"XGBoost ({NPRED} predictors)"})
T["T5_baseline_comparison"] = (pd.concat([ml, bl[["target", "model", "R2", "RMSE",
                                                  "MAE", "bias", "CCC", "slope"]]])
                               .sort_values(["target", "R2"], ascending=[True, False])
                               .round(4))

# ---------------- Table 6 : selected hyperparameters -----------------------
T["T6_selected_hyperparameters"] = hp
sel = (hp[hp.scheme == "nested spatial CV"]
       .drop(columns=["scheme", "fold", "n_test", "inner_rmse"]))
def safe_mode(s):
    m = s.dropna().mode()
    return m.iloc[0] if len(m) else ""


modal = sel.groupby(["target", "model"]).agg(safe_mode).reset_index()
T["T6b_modal_hyperparameters"] = modal

# ---------------- Table 7 : importance by class ----------------------------
CLASSMAP = {}
for b in ["B2", "B3", "B4"]:              CLASSMAP[b] = "Visible bands (B2, B3, B4)"
for b in ["B5", "B6", "B7"]:              CLASSMAP[b] = "Red-edge bands (B5, B6, B7)"
for b in ["B8", "B8A"]:                   CLASSMAP[b] = "NIR bands (B8, B8A)"
for b in ["B11", "B12"]:                  CLASSMAP[b] = "SWIR bands (B11, B12)"
for b in ["NDVI", "SAVI", "EVI", "GNDVI"]: CLASSMAP[b] = "Vegetation-vigour indices"
CLASSMAP["NDRE"] = "Red-edge index (NDRE)"
for b in ["NDMI", "MNDWI"]:               CLASSMAP[b] = "Moisture indices"
for b in ["BSI", "SI", "VSSI"]:           CLASSMAP[b] = "Brightness / salinity indices"
pi["family"] = pi.variable.str.rsplit("_", n=2).str[0]
pi["cls"] = pi.family.map(CLASSMAP)
pi["date"] = pi.variable.str.rsplit("_", n=2).str[1:].str.join("_")
pi["pos"] = pi.perm_importance.clip(lower=0)
tot = pi.groupby(["target", "model"]).pos.sum().rename("tot")
cl = (pi.groupby(["target", "model", "cls"]).pos.sum().reset_index()
      .merge(tot, on=["target", "model"]))
cl["share_percent"] = 100 * cl.pos / cl.tot
_p = (cl.pivot_table(index="cls", columns=["target", "model"], values="share_percent")
      .round(1)
      .reindex(["NIR bands (B8, B8A)", "Red-edge bands (B5, B6, B7)",
                "SWIR bands (B11, B12)", "Visible bands (B2, B3, B4)",
                "Vegetation-vigour indices", "Red-edge index (NDRE)",
                "Moisture indices", "Brightness / salinity indices"]))
_p = _p.reindex(columns=[(t, m) for t in TARGETS for m in ["RF", "XGB"]])
_p.columns = [f"{t} - {'RF' if m == 'RF' else 'XGBoost'}" for t, m in _p.columns]
T["T7_importance_by_class"] = _p.reset_index().rename(columns={"cls": "Predictor class"})
nov = (pi[pi.date == "2024_11"].groupby(["target", "model"]).pos.sum().reset_index()
       .merge(tot, on=["target", "model"]))
nov["November_2024_share_percent"] = (100 * nov.pos / nov.tot).round(1)
T["T7b_acquisition_share"] = nov[["target", "model", "November_2024_share_percent"]]

stab = (pi.assign(stable=pi.perm_importance > pi.perm_sd)
        .groupby(["target", "model"]).stable.sum().reset_index()
        .rename(columns={"stable": "n_stable_predictors"}))
stab["n_total"] = len(pi.variable.unique())
T["T7c_importance_stability"] = stab

T["T7d_permutation_importance_full"] = pi[["target", "model", "variable", "cls", "date",
                                           "perm_importance", "perm_sd", "n_folds"]].round(5)

# ---------------- Table 8 : spatial structure ------------------------------
T["T8_variogram_parameters"] = vg.round(4)
T["T8b_morans_I"] = mor
T["T8c_block_design"] = bdes

# ---------------- Table 9 : class confusion / kappa ------------------------
def kappa_mat(a, b, k=4):
    cm = np.zeros((k, k), int)
    for i, j in zip(a, b):
        cm[i, j] += 1
    n = cm.sum(); po = np.trace(cm) / n
    pe = (cm.sum(0) * cm.sum(1)).sum() / n ** 2
    return cm, po, (po - pe) / (1 - pe)


krows, cms = [], []
for t in TARGETS:
    obs = np.digitize(ovp[t].values, TH[t])
    for algo in ["RF", "XGB"]:
        prd = np.digitize(ovp[f"{t}_{algo}_spatialCV"].values, TH[t])
        cm, po, kp = kappa_mat(obs, prd)
        with np.errstate(invalid="ignore", divide="ignore"):
            ua = np.diag(cm) / cm.sum(0); pa = np.diag(cm) / cm.sum(1)
        krows.append(dict(nutrient=t, model=algo, overall_accuracy=round(po, 3),
                          kappa=round(kp, 3),
                          **{f"producer_{c}": round(float(pa[i]), 3) for i, c in enumerate(CLS)},
                          **{f"user_{c}": round(float(ua[i]), 3) for i, c in enumerate(CLS)}))
        d = pd.DataFrame(cm, index=[f"obs {c}" for c in CLS],
                         columns=[f"pred {c}" for c in CLS])
        d.insert(0, "model", algo); d.insert(0, "nutrient", t)
        cms.append(d.reset_index().rename(columns={"index": "observed_class"}))
T["T9_class_accuracy_kappa"] = pd.DataFrame(krows)
T["T9b_confusion_matrices"] = pd.concat(cms, ignore_index=True)

obs_counts = pd.DataFrame({t: np.bincount(np.digitize(ovp[t].values, TH[t]), minlength=4)
                           for t in TARGETS}, index=CLS).T.reset_index()
obs_counts.columns = ["nutrient"] + CLS
T["T9c_observed_class_counts"] = obs_counts

# ---------------- Table 10 : map products ----------------------------------
T["T10_class_areas"] = care.round(2)
T["T10b_raster_summary"] = ras.round(3)
T["T10c_RF_XGB_map_agreement"] = agr.round(4)
T["T10d_map_metadata"] = pd.DataFrame([
    ["Coordinate reference system (rasters)", "EPSG:4326 — WGS 84 geographic"],
    ["Coordinate reference system (figures)", "EPSG:26191 — Merchich / Nord Maroc"],
    ["Nominal grid resolution", "10 m"],
    ["Effective pixel size at 32.3 N", f"{msum['pixel_x_m']:.2f} x {msum['pixel_y_m']:.2f} m"],
    ["Pixel area", f"{msum['pixel_ha']:.5f} ha"],
    ["Valid prediction pixels", f"{msum['n_valid_pixels']:,}"],
    ["Mapped area", f"{msum['mapped_area_ha']:,.0f} ha"],
    ["Area of applicability threshold (DI)", f"{msum['aoa_threshold']:.4f}"],
    ["Area inside applicability domain", f"{msum['ha_inside_aoa']:,.0f} ha "
                                         f"({msum['pct_inside_aoa']:.2f} %)"],
    ["Area outside applicability domain", f"{msum['ha_outside_aoa']:,.0f} ha "
                                          f"({100-msum['pct_inside_aoa']:.2f} %)"],
    ["Sampling density", f"1 sample per {msum['mapped_area_ha']/110:,.0f} ha"],
], columns=["Item", "Value"])

# ---------------- Table 11 : out-of-fold predictions -----------------------
T["T11_out_of_fold_predictions"] = ovp.round(4)

# ---------------- write ----------------------------------------------------
out = os.path.join(TAB, "All_Tables_Revision2.xlsx")
with pd.ExcelWriter(out, engine="openpyxl") as xl:
    for k, v in T.items():
        v.to_excel(xl, sheet_name=k[:31], index=False)
        v.to_csv(os.path.join(TAB, k + ".csv"), index=False)

print(f"wrote {out}")
for k, v in T.items():
    print(f"  {k:38s} {v.shape}")

print("\n=== KEY TABLES ===")
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 40)
print("\nT3 descriptive statistics:")
print(T["T3_descriptive_statistics"].to_string(index=False))
print("\nT4 model performance:")
print(T["T4_model_performance"].to_string(index=False))
print("\nT4b bootstrap CI:")
print(T["T4b_bootstrap_CI"].to_string(index=False))
print("\nT4c paired test:")
print(T["T4c_paired_model_test"].to_string(index=False))
print("\nT5 baselines:")
print(T["T5_baseline_comparison"].to_string(index=False))
print("\nT7 importance by class:")
print(T["T7_importance_by_class"].to_string(index=False))
print("\nT7b November share:")
print(T["T7b_acquisition_share"].to_string(index=False))
print("\nT7c stability:")
print(T["T7c_importance_stability"].to_string(index=False))
print("\nT9 class accuracy:")
print(T["T9_class_accuracy_kappa"][["nutrient", "model", "overall_accuracy", "kappa"]].to_string(index=False))
print("\nT10 class areas:")
print(T["T10_class_areas"].to_string(index=False))
print("\nT10c RF vs XGB agreement:")
print(T["T10c_RF_XGB_map_agreement"].to_string(index=False))
print("\nT10d metadata:")
print(T["T10d_map_metadata"].to_string(index=False))
print("\nSTEP 06 complete.")
