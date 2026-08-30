# -*- coding: utf-8 -*-
"""
STEP 05 - Publication-quality cartography from the 10 m prediction rasters.

Figures: study area + sampling design, continuous nutrient maps, local
uncertainty maps, applicability-domain map, fertility-class maps.
All panels carry a projected graticule (EPSG:26191 Merchich / Nord Maroc),
scale bar, north arrow, units, sample locations and the district boundary.
"""
import numpy as np, pandas as pd, os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Rectangle, Polygon as MplPoly
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import geopandas as gpd

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
RES   = os.path.join(FINAL, "results")
MAPS  = os.path.join(FINAL, "maps")
FIG   = os.path.join(FINAL, "figures")
SHP   = r"d:\Doctorat\article1\Beni_Moussa.shp"
os.makedirs(FIG, exist_ok=True)

DST_EPSG = 26191                     # Merchich / Nord Maroc
TARGETS = ["N", "P", "K"]
LONGNAME = {"N": "Total nitrogen (N)", "P": "Available phosphorus (P)",
            "K": "Exchangeable potassium (K)"}
PANEL = ["(a)", "(b)", "(c)"]
DPI = 400
MAXPX = 2600                          # display width in pixels

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.linewidth": 0.9, "axes.edgecolor": "#333333",
    "xtick.labelsize": 7.6, "ytick.labelsize": 7.6,
    "legend.frameon": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.07,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


# ------------------------------------------------------------------ helpers
def load_proj(path, maxpx=MAXPX, resampling=Resampling.average):
    """Reproject a raster to DST_EPSG and downsample for display."""
    with rasterio.open(path) as src:
        tr, w, h = calculate_default_transform(src.crs, f"EPSG:{DST_EPSG}",
                                               src.width, src.height, *src.bounds)
        if w > maxpx:
            sc = maxpx / w
            w2, h2 = int(w * sc), max(1, int(h * sc))
            tr = rasterio.Affine(tr.a / sc, tr.b, tr.c, tr.d, tr.e / sc, tr.f)
            w, h = w2, h2
        dst = np.full((h, w), np.nan, np.float32)
        reproject(rasterio.band(src, 1), dst, src_transform=src.transform,
                  src_crs=src.crs, dst_transform=tr, dst_crs=f"EPSG:{DST_EPSG}",
                  resampling=resampling, src_nodata=np.nan, dst_nodata=np.nan)
    left, top = tr.c, tr.f
    right, bottom = left + tr.a * w, top + tr.e * h
    return dst, (left, right, bottom, top)


def scalebar(ax, extent, length_km=10, loc=(0.66, 0.055)):
    x0, x1, y0, y1 = extent
    L = length_km * 1000
    bx = x0 + loc[0] * (x1 - x0)
    by = y0 + loc[1] * (y1 - y0)
    hgt = 0.024 * (y1 - y0)
    for i in range(2):
        ax.add_patch(Rectangle((bx + i * L / 2, by), L / 2, hgt,
                               facecolor="#1A211E" if i == 0 else "white",
                               edgecolor="#1A211E", lw=0.7, zorder=13))
    for frac, lab in [(0, "0"), (0.5, str(length_km // 2)), (1.0, f"{length_km} km")]:
        ax.text(bx + frac * L, by + hgt * 1.35, lab, ha="center", va="bottom",
                fontsize=6.6, zorder=13,
                path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])


def north_arrow(ax, extent, loc=(0.962, 0.70)):
    x0, x1, y0, y1 = extent
    cx = x0 + loc[0] * (x1 - x0)
    cy = y0 + loc[1] * (y1 - y0)
    s = 0.10 * (y1 - y0)
    ax.add_patch(MplPoly([[cx, cy + s], [cx - s * 0.34, cy - s * 0.42],
                          [cx, cy - s * 0.16], [cx + s * 0.34, cy - s * 0.42]],
                         closed=True, facecolor="#1A211E", edgecolor="white",
                         lw=0.6, zorder=13))
    ax.text(cx, cy + s * 1.18, "N", ha="center", va="bottom", fontsize=7.6,
            fontweight="bold", zorder=13,
            path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])


def graticule(ax, extent, nx=6, ny=3):
    x0, x1, y0, y1 = extent
    xt = np.linspace(x0, x1, nx + 2)[1:-1]
    yt = np.linspace(y0, y1, ny + 2)[1:-1]
    ax.set_xticks(xt); ax.set_yticks(yt)
    ax.set_xticklabels([f"{v/1000:,.0f}" for v in xt])
    ax.set_yticklabels([f"{v/1000:,.0f}" for v in yt])
    ax.tick_params(length=2.6, width=0.8, pad=1.8)
    for v in xt:
        ax.axvline(v, color="white", lw=0.35, alpha=0.45, zorder=6)
    for v in yt:
        ax.axhline(v, color="white", lw=0.35, alpha=0.45, zorder=6)


def base_panel(ax, extent, boundary, pts=None, show_pts=True, ptsize=7):
    boundary.boundary.plot(ax=ax, color="#1A211E", lw=0.8, zorder=9)
    if show_pts and pts is not None:
        ax.scatter(pts.x_p, pts.y_p, s=ptsize, facecolor="none",
                   edgecolor="#111111", lw=0.55, zorder=10)
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal")
    graticule(ax, extent)
    scalebar(ax, extent)
    north_arrow(ax, extent)


# ------------------------------------------------------------------ inputs
bnd = gpd.read_file(SHP).to_crs(epsg=DST_EPSG)
df = pd.read_csv(os.path.join(RES, "01_analysis_ready_dataset.csv"))
pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
                       crs="EPSG:4326").to_crs(epsg=DST_EPSG)
pts["x_p"] = pts.geometry.x; pts["y_p"] = pts.geometry.y
msum = json.load(open(os.path.join(RES, "03_map_summary.json")))
casum = pd.read_csv(os.path.join(RES, "03_class_areas.csv"))

aoa, ext = load_proj(os.path.join(MAPS, "AOA_10m.tif"), resampling=Resampling.nearest)
outside = (aoa < 0.5)

CRS_NOTE = (f"Projection: Merchich / Nord Maroc (EPSG:{DST_EPSG})   |   axis units km"
            f"   |   prediction grid 10 m   |   source Sentinel-2 MSI L2A")
GREY_MASK = "#C9CFC8"


# =========================================== Figure 1 : study area + design
fig, axes = plt.subplots(2, 1, figsize=(7.8, 6.6))
di, _ = load_proj(os.path.join(MAPS, "DI_10m.tif"))

ax = axes[0]
ax.imshow(np.where(np.isnan(aoa), np.nan, 1.0), extent=ext, origin="upper",
          cmap=ListedColormap(["#DCE5DA"]), zorder=2)
base_panel(ax, ext, bnd, pts, show_pts=False)
for b, g in pts.groupby("block"):
    ax.scatter(g.x_p, g.y_p, s=17, edgecolor="white", lw=0.4, zorder=11,
               label=f"{int(b)}")
ax.legend(title="Spatial CV block", ncol=5, fontsize=6.2, title_fontsize=6.8,
          loc="upper left", handletextpad=0.2, columnspacing=0.7,
          frameon=True, framealpha=0.92, edgecolor="#D9DFD8")
ax.set_title("(a)  Sampling design: 110 composite topsoil samples (0-20 cm) and the "
             "10 spatial cross-validation blocks", fontsize=8.8, loc="left", pad=6)

ax = axes[1]
im = ax.imshow(di, extent=ext, origin="upper", cmap="magma_r", vmin=0,
               vmax=np.nanpercentile(di, 99), zorder=2)
base_panel(ax, ext, bnd, pts, ptsize=5)
cb = fig.colorbar(im, ax=ax, fraction=0.021, pad=0.012)
cb.set_label("Dissimilarity index (DI)", fontsize=7.6); cb.ax.tick_params(labelsize=7)
cb.ax.axhline(msum["aoa_threshold"], color="#00E5FF", lw=1.6)
ax.set_title(f"(b)  Predictor-space dissimilarity and area of applicability "
             f"(threshold DI = {msum['aoa_threshold']:.2f}; "
             f"{msum['pct_inside_aoa']:.1f} % of the district inside)",
             fontsize=8.8, loc="left", pad=6)
fig.text(0.5, 0.004, CRS_NOTE, ha="center", fontsize=6.6, color="#46524D")
fig.tight_layout(h_pad=1.6)
fig.savefig(os.path.join(FIG, "Figure_1_study_area_and_design.png"), dpi=DPI)
fig.savefig(os.path.join(FIG, "Figure_1_study_area_and_design.pdf"))
plt.close(fig)
print("wrote Figure_1")


# ============================== Figure 8 / 9 : continuous 10 m nutrient maps
def continuous_figure(algo, fname, title):
    fig, axes = plt.subplots(3, 1, figsize=(7.8, 9.4))
    for i, tgt in enumerate(TARGETS):
        ax = axes[i]
        a, e = load_proj(os.path.join(MAPS, f"{tgt}_{algo}_10m.tif"))
        vmin, vmax = np.nanpercentile(a, [1, 99])
        am = np.where(outside, np.nan, a)
        ax.imshow(np.where(np.isnan(a), np.nan, 0.0), extent=e, origin="upper",
                  cmap=ListedColormap([GREY_MASK]), zorder=2)
        im = ax.imshow(am, extent=e, origin="upper", cmap="viridis",
                       vmin=vmin, vmax=vmax, zorder=3, interpolation="nearest")
        base_panel(ax, e, bnd, pts, ptsize=5)
        cb = fig.colorbar(im, ax=ax, fraction=0.021, pad=0.012, extend="both")
        cb.set_label("mg kg$^{-1}$", fontsize=7.6); cb.ax.tick_params(labelsize=7)
        obs = df[tgt]
        ax.set_title(f"{PANEL[i]}  {LONGNAME[tgt]} - colour range "
                     f"{vmin:,.0f}-{vmax:,.0f} mg kg$^{{-1}}$ "
                     f"(observed {obs.min():,.1f}-{obs.max():,.1f})",
                     fontsize=8.8, loc="left", pad=6)
        if i == 0:
            ax.legend(handles=[
                Line2D([], [], marker="o", ls="", mfc="none", mec="#111111", ms=4,
                       label="soil sample (n = 110)"),
                Line2D([], [], marker="s", ls="", mfc=GREY_MASK, mec="#666", ms=5,
                       label="outside area of applicability")],
                loc="upper left", fontsize=6.4, framealpha=0.92, frameon=True,
                edgecolor="#D9DFD8")
    fig.suptitle(title, y=0.999, fontsize=10)
    fig.text(0.5, 0.003, CRS_NOTE, ha="center", fontsize=6.6, color="#46524D")
    fig.tight_layout(h_pad=1.5)
    fig.savefig(os.path.join(FIG, fname), dpi=DPI)
    fig.savefig(os.path.join(FIG, fname.replace(".png", ".pdf")))
    plt.close(fig)
    print("wrote", fname)


continuous_figure("RF", "Figure_8_continuous_maps_RF.png",
                  "Random Forest predicted soil macronutrient concentrations at 10 m, "
                  "masked outside the area of applicability")
continuous_figure("XGB", "Figure_9_continuous_maps_XGB.png",
                  "XGBoost predicted soil macronutrient concentrations at 10 m, "
                  "masked outside the area of applicability")


# ==================================== Figure 10 : local uncertainty maps
fig, axes = plt.subplots(3, 1, figsize=(7.8, 9.4))
for i, tgt in enumerate(TARGETS):
    ax = axes[i]
    a, e = load_proj(os.path.join(MAPS, f"{tgt}_RF_SD_10m.tif"))
    m, _ = load_proj(os.path.join(MAPS, f"{tgt}_RF_10m.tif"))
    vmax = np.nanpercentile(a, 99)
    am = np.where(outside, np.nan, a)
    ax.imshow(np.where(np.isnan(a), np.nan, 0.0), extent=e, origin="upper",
              cmap=ListedColormap([GREY_MASK]), zorder=2)
    im = ax.imshow(am, extent=e, origin="upper", cmap="cividis", vmin=0, vmax=vmax,
                   zorder=3, interpolation="nearest")
    base_panel(ax, e, bnd, pts, ptsize=5)
    cb = fig.colorbar(im, ax=ax, fraction=0.021, pad=0.012, extend="max")
    cb.set_label("Ensemble SD (mg kg$^{-1}$)", fontsize=7.6); cb.ax.tick_params(labelsize=7)
    with np.errstate(invalid="ignore", divide="ignore"):
        rel = 100 * np.nanmedian(am / np.where(np.abs(m) < 1e-6, np.nan, m))
    ax.set_title(f"{PANEL[i]}  {LONGNAME[tgt]} - between-tree standard deviation "
                 f"(median relative uncertainty {rel:.1f} %)",
                 fontsize=8.8, loc="left", pad=6)
fig.suptitle("Local prediction uncertainty of the Random Forest maps, expressed as the "
             "standard deviation across the regression-tree ensemble", y=0.999, fontsize=10)
fig.text(0.5, 0.003, CRS_NOTE, ha="center", fontsize=6.6, color="#46524D")
fig.tight_layout(h_pad=1.5)
fig.savefig(os.path.join(FIG, "Figure_10_uncertainty_maps.png"), dpi=DPI)
fig.savefig(os.path.join(FIG, "Figure_10_uncertainty_maps.pdf"))
plt.close(fig)
print("wrote Figure_10")


# ==================================== Figure 11 : fertility class maps
CLS_COL = ["#FFFFCC", "#C2E699", "#78C679", "#238443"]     # YlGn, sequential low -> high
CLS_NAME = ["Very low", "Low", "Medium", "High"]
TH = {"N": [1000, 1500, 3000], "P": [15, 30, 60], "K": [40, 80, 120]}
cmap = ListedColormap(CLS_COL)
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N)

fig, axes = plt.subplots(3, 1, figsize=(7.8, 9.6))
for i, tgt in enumerate(TARGETS):
    ax = axes[i]
    a, e = load_proj(os.path.join(MAPS, f"{tgt}_RF_10m.tif"), resampling=Resampling.bilinear)
    cls = np.digitize(a, TH[tgt]).astype(float)
    cls[np.isnan(a)] = np.nan
    cls = np.where(outside, np.nan, cls)
    ax.imshow(np.where(np.isnan(a), np.nan, 0.0), extent=e, origin="upper",
              cmap=ListedColormap([GREY_MASK]), zorder=2)
    ax.imshow(cls, extent=e, origin="upper", cmap=cmap, norm=norm, zorder=3,
              interpolation="nearest")
    base_panel(ax, e, bnd, pts, ptsize=5)
    sub = casum[casum.nutrient == tgt].reset_index(drop=True)
    th = TH[tgt]
    lab = [f"< {th[0]:,}", f"{th[0]:,}-{th[1]:,}", f"{th[1]:,}-{th[2]:,}", f"> {th[2]:,}"]
    handles = [Rectangle((0, 0), 1, 1, facecolor=CLS_COL[j], edgecolor="#555", lw=0.5,
                         label=f"{CLS_NAME[j]} ({lab[j]}): "
                               f"{sub.iloc[j].rf_inAOA_pct:.1f} % | "
                               f"{sub.iloc[j].rf_inAOA_ha:,.0f} ha")
               for j in range(4)]
    ax.legend(handles=handles, loc="upper left", fontsize=6.2, ncol=2,
              frameon=True, framealpha=0.93, edgecolor="#D9DFD8",
              handlelength=1.1, handleheight=1.0, columnspacing=0.9,
              title=f"{tgt} class (mg kg$^{{-1}}$)", title_fontsize=6.6)
    ax.set_title(f"{PANEL[i]}  {LONGNAME[tgt]} - fertility classes within the area of "
                 f"applicability", fontsize=8.8, loc="left", pad=6)
fig.suptitle("Reclassified soil fertility maps derived from the Random Forest 10 m "
             "predictions (areas reported inside the applicability domain)",
             y=0.999, fontsize=10)
fig.text(0.5, 0.003, CRS_NOTE, ha="center", fontsize=6.6, color="#46524D")
fig.tight_layout(h_pad=1.5)
fig.savefig(os.path.join(FIG, "Figure_11_fertility_classes.png"), dpi=DPI)
fig.savefig(os.path.join(FIG, "Figure_11_fertility_classes.pdf"))
plt.close(fig)
print("wrote Figure_11")

print("\nSTEP 05 complete.")
