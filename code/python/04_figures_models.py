# -*- coding: utf-8 -*-
"""
STEP 04 - Publication figures for the model-evaluation part, plus variograms.
Figures 3, 4, 5, 6, 7 and the sampling-design map (Figure 1b).
"""
import numpy as np, pandas as pd, os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
from scipy.optimize import curve_fit

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
FIG   = os.path.join(FINAL, "figures")
os.makedirs(FIG, exist_ok=True)

TARGETS = ["N", "P", "K"]
LABEL = {"N": "Total nitrogen (N)", "P": "Available phosphorus (P)",
         "K": "Exchangeable potassium (K)"}
PANEL = ["(a)", "(b)", "(c)"]
DPI = 400

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.linewidth": 0.8, "axes.edgecolor": "#333333",
    "axes.labelsize": 9.5, "axes.titlesize": 10,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "xtick.direction": "out", "ytick.direction": "out",
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "legend.frameon": False, "legend.fontsize": 8.5,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.06,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

C_RF, C_XGB = "#1F5F6B", "#B5522F"
C_GRID = "#E4E8E5"


def panel_tag(ax, i, dx=-0.16, dy=1.045):
    ax.text(dx, dy, PANEL[i], transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top", ha="left")


def softgrid(ax):
    ax.grid(True, color=C_GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ======================================================================= data
ovp = pd.read_csv(os.path.join(RES, "02_out_of_fold_predictions.csv"))
mt  = pd.read_csv(os.path.join(RES, "02_metrics_all_schemes.csv"))
bl  = pd.read_csv(os.path.join(RES, "02_baselines.csv"))
ci  = pd.read_csv(os.path.join(RES, "02_bootstrap_ci.csv"))
pi  = pd.read_csv(os.path.join(RES, "02_permutation_importance.csv"))
bd  = pd.read_csv(os.path.join(RES, "01_block_design.csv"))


# ================================================= Fig 3 / 4 : obs vs pred
def obs_pred_figure(algo, fname, color):
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.75))
    for i, tgt in enumerate(TARGETS):
        ax = axes[i]
        y = ovp[tgt].values
        p = ovp[f"{tgt}_{algo}_spatialCV"].values
        r = mt[(mt.target == tgt) & (mt.model == algo) &
               (mt.scheme == "nested spatial CV")].iloc[0]
        lo = min(y.min(), p.min()); hi = max(y.max(), p.max())
        pad = 0.06 * (hi - lo); lo -= pad; hi += pad

        ax.plot([lo, hi], [lo, hi], ls=(0, (5, 4)), color="#6E7B75", lw=1.0, zorder=2,
                label="1:1 line")
        ax.scatter(y, p, s=26, facecolor=color, edgecolor="white", lw=0.5,
                   alpha=0.85, zorder=3)
        xs = np.linspace(lo, hi, 50)
        ax.plot(xs, r.slope * xs + r.intercept, color="#B5522F" if algo == "RF" else "#1F5F6B",
                lw=1.5, zorder=4, label=f"fitted (slope {r.slope:.2f})")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
        softgrid(ax)
        ax.set_xlabel(f"Observed {tgt} (mg kg$^{{-1}}$)")
        ax.set_ylabel(f"Predicted {tgt} (mg kg$^{{-1}}$)" if i == 0 else "")
        ax.set_title(LABEL[tgt], pad=8)
        panel_tag(ax, i, dx=-0.20 if i == 0 else -0.13)

        txt = (f"$R^2$ = {r.R2:.3f}\nRMSE = {r.RMSE:,.2f}\nMAE = {r.MAE:,.2f}\n"
               f"bias = {r.bias:+,.2f}\nCCC = {r.CCC:.3f}\nslope = {r.slope:.2f}\nn = {int(r.n)}")
        ax.text(0.035, 0.965, txt, transform=ax.transAxes, va="top", ha="left",
                fontsize=7.4, linespacing=1.42,
                bbox=dict(boxstyle="round,pad=0.42", fc="white", ec="#D9DFD8", lw=0.7, alpha=0.94))
        ax.legend(loc="lower right", fontsize=7.2, handlelength=1.8)
        ax.xaxis.set_major_locator(MaxNLocator(5)); ax.yaxis.set_major_locator(MaxNLocator(5))

    fig.suptitle(f"{'Random Forest' if algo=='RF' else 'XGBoost'} — held-out predictions "
                 f"from nested spatial block cross-validation", y=1.03, fontsize=10.5)
    fig.tight_layout(w_pad=2.2)
    fig.savefig(os.path.join(FIG, fname), dpi=DPI)
    fig.savefig(os.path.join(FIG, fname.replace(".png", ".pdf")))
    plt.close(fig)
    print("wrote", fname)


obs_pred_figure("RF", "Figure_3_RF_observed_vs_predicted.png", C_RF)
obs_pred_figure("XGB", "Figure_4_XGB_observed_vs_predicted.png", C_XGB)


# ============================================ Fig 5 : schemes + baselines
fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.4))
schemes = ["calibration", "nested random CV", "nested spatial CV"]
snames = ["Calibration\n(not validation)", "Nested\nrandom CV", "Nested\nspatial CV"]
BSTYLE = [("Ridge regression", (0, (5, 2)), "#8A6212"),
          ("PLS regression", (0, (2, 2)), "#3F6B33"),
          ("Ordinary kriging", (0, (6, 2, 1, 2)), "#5B7C99")]
for i, tgt in enumerate(TARGETS):
    ax = axes[i]
    xpos = np.arange(3); wbar = 0.34
    for j, (algo, col) in enumerate([("RF", C_RF), ("XGB", C_XGB)]):
        vals = [mt[(mt.target == tgt) & (mt.model == algo) & (mt.scheme == s)].R2.iloc[0]
                for s in schemes]
        ax.bar(xpos + (j - 0.5) * wbar, vals, wbar, color=col, edgecolor="white", lw=0.6,
               label="Random Forest" if algo == "RF" else "XGBoost", zorder=3)
        c = ci[(ci.target == tgt) & (ci.model == algo)].iloc[0]
        ax.errorbar(xpos[2] + (j - 0.5) * wbar, c.R2,
                    yerr=[[c.R2 - c.R2_lo], [c.R2_hi - c.R2]],
                    fmt="none", ecolor="#1A211E", elinewidth=1.1, capsize=3.2, zorder=5)
        for k, v in enumerate(vals):
            yoff = 0.022 if k < 2 else (c.R2_hi - v) + 0.028
            ax.text(xpos[k] + (j - 0.5) * wbar, v + yoff, f"{v:.3f}", ha="center",
                    fontsize=6.8, color="#46524D", rotation=90 if k == 2 else 0,
                    va="bottom")
    for nm, ls, cc in BSTYLE:
        v = bl[(bl.target == tgt) & (bl.model == nm)].R2.iloc[0]
        ax.axhline(v, ls=ls, lw=1.1, color=cc, zorder=2, label=nm if i == 0 else None)
    ax.set_xticks(xpos); ax.set_xticklabels(snames, fontsize=7.6)
    ax.set_ylim(0, 1.16); ax.set_xlim(-0.62, 2.62)
    ax.set_ylabel("$R^2$  (1 − SSE/SST)" if i == 0 else "")
    ax.set_title(LABEL[tgt], pad=8)
    softgrid(ax); panel_tag(ax, i, dx=-0.17 if i == 0 else -0.10)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, -0.075), ncol=5, fontsize=8,
           columnspacing=1.8, handlelength=1.8)
fig.suptitle("Model performance by validation scheme, with bootstrap 95 % confidence "
             "intervals on the spatial-CV estimate and non-machine-learning baselines\n"
             "(the intercept-only model gives a negative $R^2$ for all three nutrients "
             "and is below the axis)", y=1.06, fontsize=9.6)
fig.tight_layout(w_pad=2.4)
fig.savefig(os.path.join(FIG, "Figure_5_validation_schemes.png"), dpi=DPI)
fig.savefig(os.path.join(FIG, "Figure_5_validation_schemes.pdf"))
plt.close(fig)
print("wrote Figure_5")


# ======================================== Fig 6 : permutation importance
CLASS = {}
for b in ["B2", "B3", "B4"]:              CLASS[b] = "Visible bands"
for b in ["B5", "B6", "B7"]:              CLASS[b] = "Red-edge bands"
for b in ["B8", "B8A"]:                   CLASS[b] = "NIR bands"
for b in ["B11", "B12"]:                  CLASS[b] = "SWIR bands"
for b in ["NDVI", "SAVI", "EVI", "GNDVI"]: CLASS[b] = "Vegetation-vigour indices"
CLASS["NDRE"] = "Red-edge index"
for b in ["NDMI", "MNDWI"]:               CLASS[b] = "Moisture indices"
for b in ["BSI", "SI", "VSSI"]:           CLASS[b] = "Brightness / salinity indices"
ORDER = ["NIR bands", "Red-edge bands", "SWIR bands", "Visible bands",
         "Vegetation-vigour indices", "Red-edge index", "Moisture indices",
         "Brightness / salinity indices"]
CCOL = dict(zip(ORDER, ["#1F5F6B", "#3E8C99", "#B5522F", "#8A6212",
                        "#3F6B33", "#6D9C5E", "#5B7C99", "#9A6B8C"]))
pi["family"] = pi.variable.str.rsplit("_", n=2).str[0]
pi["cls"] = pi.family.map(CLASS)
pi["date"] = pi.variable.str.rsplit("_", n=2).str[1:].str.join("_")
pi["pos"] = pi.perm_importance.clip(lower=0)

fig = plt.figure(figsize=(11.2, 8.6))
gs = fig.add_gridspec(2, 3, height_ratios=[0.72, 1.35], hspace=0.60, wspace=0.34,
                      top=0.895, bottom=0.075)

for i, tgt in enumerate(TARGETS):
    ax = fig.add_subplot(gs[0, i])
    left = np.zeros(2)
    for c in ORDER:
        vals = []
        for algo in ["RF", "XGB"]:
            s = pi[(pi.target == tgt) & (pi.model == algo)]
            vals.append(100 * s[s.cls == c].pos.sum() / s.pos.sum())
        ax.barh([1, 0], vals, left=left, height=0.62, color=CCOL[c], label=c,
                edgecolor="white", lw=0.5, zorder=3)
        left += np.array(vals)
    ax.set_yticks([1, 0]); ax.set_yticklabels(["RF", "XGB"])
    ax.set_xlim(0, 100); ax.set_xlabel("Share of permutation importance (%)")
    ax.set_title(LABEL[tgt], pad=8)
    softgrid(ax); panel_tag(ax, i, dx=-0.17 if i == 0 else -0.12)
h, l = fig.axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="center", bbox_to_anchor=(0.5, 0.508), ncol=4, fontsize=8.2,
           columnspacing=1.6, handlelength=1.3, handletextpad=0.5)

TAG2 = ["(d)", "(e)", "(f)"]
for i, tgt in enumerate(TARGETS):
    ax = fig.add_subplot(gs[1, i])
    s = (pi[(pi.target == tgt) & (pi.model == "RF")]
         .sort_values("perm_importance", ascending=False).head(15).iloc[::-1])
    ypos = np.arange(len(s))
    cols = [CCOL[c] for c in s.cls]
    ax.barh(ypos, s.perm_importance, xerr=s.perm_sd, height=0.68, color=cols,
            edgecolor="white", lw=0.5, zorder=3,
            error_kw=dict(ecolor="#46524D", elinewidth=0.9, capsize=2.2))
    ax.set_yticks(ypos); ax.set_yticklabels(s.variable, fontsize=7.2, family="DejaVu Sans Mono")
    ax.set_xlabel("Increase in RMSE when permuted\n(fraction of fold RMSE)")
    ax.axvline(0, color="#6E7B75", lw=0.8)
    nstable = int((s.perm_importance > s.perm_sd).sum())
    ax.set_title(f"{tgt} — Random Forest · {nstable}/15 exceed their between-fold SD",
                 fontsize=8.2, pad=7)
    softgrid(ax)
    ax.text(-0.42 if i == 0 else -0.38, 1.075, TAG2[i], transform=ax.transAxes,
            fontsize=11, fontweight="bold", va="top", ha="left")

fig.suptitle("Permutation importance measured on held-out spatial folds\n"
             "(a–c) aggregated by predictor class   ·   (d–f) 15 strongest individual "
             "predictors with between-fold standard deviation",
             y=0.985, fontsize=10)
fig.savefig(os.path.join(FIG, "Figure_6_permutation_importance.png"), dpi=DPI)
fig.savefig(os.path.join(FIG, "Figure_6_permutation_importance.pdf"))
plt.close(fig)
print("wrote Figure_6")


# ================================================ Fig 7 : variograms
x, y = ovp.x_m.values, ovp.y_m.values
D = np.sqrt((x[:, None] - x[None, :]) ** 2 + (y[:, None] - y[None, :]) ** 2)
iu = np.triu_indices(len(x), 1)
d = D[iu]


def emp_variogram(v, nbin=14, maxlag=None):
    g = (0.5 * (v[:, None] - v[None, :]) ** 2)[iu]
    maxlag = maxlag or np.percentile(d, 45)
    m = d <= maxlag
    edges = np.linspace(0, maxlag, nbin + 1)
    idx = np.digitize(d[m], edges) - 1
    out = [(0.5 * (edges[b] + edges[b + 1]), g[m][idx == b].mean(), (idx == b).sum())
           for b in range(nbin) if (idx == b).sum() >= 10]
    return np.array(out)


def sph(h, nug, sill, rng_):
    h = np.asarray(h, float)
    v = np.where(h < rng_, nug + sill * (1.5 * h / rng_ - 0.5 * (h / rng_) ** 3), nug + sill)
    return np.where(h == 0, nug, v)


def fit_sph(vg):
    h, g = vg[:, 0], vg[:, 1]
    try:
        p, _ = curve_fit(sph, h, g, p0=[g.min(), g.max() - g.min(), h.max() / 2],
                         bounds=([0, 0, 200], [g.max() * 1.2, 5 * g.max(), 60000]), maxfev=30000)
        return p
    except Exception:
        return None


vg_rows = []
fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.4))
for i, tgt in enumerate(TARGETS):
    for row, (lab, v) in enumerate([
            ("observed", ovp[tgt].values.astype(float)),
            ("RF residuals", ovp[tgt].values - ovp[f"{tgt}_RF_spatialCV"].values)]):
        ax = axes[row, i]
        vg = emp_variogram(v)
        p = fit_sph(vg)
        ax.scatter(vg[:, 0] / 1000, vg[:, 1], s=30, facecolor=C_RF if row == 0 else C_XGB,
                   edgecolor="white", lw=0.6, zorder=4)
        if p is not None:
            hh = np.linspace(0, vg[:, 0].max() * 1.05, 300)
            ax.plot(hh / 1000, sph(hh, *p), color="#1A211E", lw=1.3, zorder=3)
            nug, sill, rg = p
            ratio = nug / (nug + sill)
            ax.axvline(rg / 1000, ls=(0, (4, 3)), color="#6E7B75", lw=1.0)
            ax.text(0.97, 0.06,
                    f"range = {rg/1000:.1f} km\nnugget ratio = {ratio:.2f}",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=7.4,
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#D9DFD8", lw=0.6))
            vg_rows.append(dict(variable=tgt, kind=lab, nugget=nug, partial_sill=sill,
                                range_m=rg, nugget_ratio=ratio))
        ax.set_ylim(bottom=0)
        ax.set_xlabel("Lag distance (km)" if row == 1 else "")
        ax.set_ylabel("Semivariance" if i == 0 else "")
        ax.set_title(f"{tgt} — {lab}", fontsize=9, pad=6)
        softgrid(ax)
        if row == 0:
            panel_tag(ax, i, dx=-0.19 if i == 0 else -0.13)
fig.suptitle("Empirical variograms of the observed nutrients (top) and of Random Forest "
             "spatial-CV residuals (bottom), with fitted spherical models",
             y=1.005, fontsize=10)
fig.tight_layout(w_pad=2.0, h_pad=1.6)
fig.savefig(os.path.join(FIG, "Figure_7_variograms.png"), dpi=DPI)
fig.savefig(os.path.join(FIG, "Figure_7_variograms.pdf"))
plt.close(fig)
pd.DataFrame(vg_rows).to_csv(os.path.join(RES, "04_variogram_parameters.csv"), index=False)
print("wrote Figure_7")


# =============================== Moran's I table (supports block-CV choice)
def morans_I(v, bw):
    w = (D <= bw).astype(float); np.fill_diagonal(w, 0)
    z = v - v.mean()
    return (len(v) / w.sum()) * (w * np.outer(z, z)).sum() / (z ** 2).sum()


mor = [dict(bandwidth_km=bw / 1000, **{t: round(morans_I(ovp[t].values.astype(float), bw), 3)
                                       for t in TARGETS})
       for bw in [1000, 2000, 3000, 5000, 10000]]
pd.DataFrame(mor).to_csv(os.path.join(RES, "04_morans_I.csv"), index=False)
print("wrote Moran's I")
print("\nSTEP 04 complete.")
