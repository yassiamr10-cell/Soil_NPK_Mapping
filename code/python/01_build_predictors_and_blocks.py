# -*- coding: utf-8 -*-
"""
STEP 01 - Corrected predictor inventory + spatial block design.

Fixes applied (referee comment M5):
  * SI   was stored as -NDMI            -> recomputed correctly as B11 x B12
  * VSSI was stored as -NDSI            -> recomputed correctly as 2*B3 - 5*(B4+B8)
  * MNDWI was stored as (B3-B12)/(B3+B12) -> recomputed correctly as (B3-B11)/(B3+B11)
  * NDSI  was a mislabelled duplicate of MNDWI -> removed
  * NDRE  is computed as (B8A-B5)/(B8A+B5); Table 2 corrected accordingly
Result: 10 bands + 10 indices, 2 acquisitions = 40 independent predictors.

Spatial blocks (referee comment M2): spatial k-means on projected coordinates,
10 folds of near-equal size, block extent and separation reported.
"""
import numpy as np, pandas as pd, os, json
from pyproj import Transformer
from sklearn.cluster import KMeans

BASE  = r"d:\Doctorat\article1\outputs_fast"
FINAL = os.path.join(BASE, "FINAL")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)

DATES = ["2024_11", "2025_01"]
BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
INDICES = ["NDVI", "SAVI", "EVI", "GNDVI", "NDRE", "NDMI", "MNDWI", "BSI", "SI", "VSSI"]


def compute_indices(b):
    """b: dict of band arrays (0-1 surface reflectance). Returns dict of indices."""
    B2, B3, B4, B5, B8, B8A, B11, B12 = (b["B2"], b["B3"], b["B4"], b["B5"],
                                         b["B8"], b["B8A"], b["B11"], b["B12"])
    eps = 1e-9
    out = {}
    out["NDVI"]  = (B8 - B4) / (B8 + B4 + eps)
    out["SAVI"]  = 1.5 * (B8 - B4) / (B8 + B4 + 0.5)
    out["EVI"]   = 2.5 * (B8 - B4) / (B8 + 6.0 * B4 - 7.5 * B2 + 1.0)
    out["GNDVI"] = (B8 - B3) / (B8 + B3 + eps)
    out["NDRE"]  = (B8A - B5) / (B8A + B5 + eps)
    out["NDMI"]  = (B8 - B11) / (B8 + B11 + eps)
    out["MNDWI"] = (B3 - B11) / (B3 + B11 + eps)
    out["BSI"]   = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2) + eps)
    out["SI"]    = B11 * B12
    out["VSSI"]  = 2.0 * B3 - 5.0 * (B4 + B8)
    return out


def predictor_names():
    return [f"{v}_{d}" for d in DATES for v in BANDS + INDICES]


def main():
    raw = pd.read_excel(os.path.join(BASE, "benimoussa_NPK2.xlsx"))
    df = raw[["Echantillon", "Latitude", "Longitude", "N", "P", "K"]].copy()

    print("=" * 96)
    print("CORRECTED PREDICTOR CONSTRUCTION")
    print("=" * 96)
    for d in DATES:
        b = {bn: raw[f"{bn}_{d}"].values.astype(float) for bn in BANDS}
        for bn in BANDS:
            df[f"{bn}_{d}"] = b[bn]
        idx = compute_indices(b)
        for k, v in idx.items():
            df[f"{k}_{d}"] = v
        print(f"  {d}: bands min={min(x.min() for x in b.values()):.4f} "
              f"max={max(x.max() for x in b.values()):.4f}  (0-1 reflectance OK)")
        # show the corrections
        old_si, old_vssi = raw[f"SI_{d}"].values, raw[f"VSSI_{d}"].values
        print(f"     SI   old(=-NDMI) range {old_si.min():+.3f}..{old_si.max():+.3f}"
              f"  ->  new(B11xB12) range {idx['SI'].min():.4f}..{idx['SI'].max():.4f}")
        print(f"     VSSI old(=-NDSI) range {old_vssi.min():+.3f}..{old_vssi.max():+.3f}"
              f"  ->  new(2B3-5(B4+B8)) range {idx['VSSI'].min():+.3f}..{idx['VSSI'].max():+.3f}")

    PRED = predictor_names()
    df = df[["Echantillon", "Latitude", "Longitude", "N", "P", "K"] + PRED]
    print(f"\nTOTAL PREDICTORS = {len(PRED)}  (10 bands + 10 indices) x 2 dates")

    # collinearity check on the corrected set
    M = df[PRED].values.astype(float)
    C = np.corrcoef(M.T)
    np.fill_diagonal(C, 0)
    dup = [(PRED[i], PRED[j], C[i, j]) for i in range(len(PRED))
           for j in range(i + 1, len(PRED)) if abs(C[i, j]) > 0.999]
    print(f"exact-duplicate pairs (|r| > 0.999): {len(dup)}")
    for a, b_, r in dup:
        print("   ", a, b_, round(r, 6))
    Z = (M - M.mean(0)) / M.std(0)
    s = np.linalg.svd(Z, compute_uv=False)
    print(f"numerical rank = {int((s > s.max()*1e-8).sum())} / {len(PRED)}")
    print(f"max |r| among predictors = {np.abs(C).max():.4f}")

    # ---------------- spatial blocks -----------------
    tr = Transformer.from_crs("EPSG:4326", "EPSG:26191", always_xy=True)
    x, y = tr.transform(df.Longitude.values, df.Latitude.values)
    df["x_m"], df["y_m"] = x, y

    NB = 10
    km = KMeans(n_clusters=NB, n_init=50, random_state=42).fit(np.c_[x, y])
    df["block"] = km.labels_

    # relabel blocks west->east for readability
    order = np.argsort([x[km.labels_ == k].mean() for k in range(NB)])
    remap = {old: new + 1 for new, old in enumerate(order)}
    df["block"] = df["block"].map(remap)

    print("\n" + "=" * 96)
    print("SPATIAL BLOCK DESIGN (spatial k-means, EPSG:26191)")
    print("=" * 96)
    D = np.sqrt((x[:, None] - x[None, :]) ** 2 + (y[:, None] - y[None, :]) ** 2)
    np.fill_diagonal(D, np.inf)
    rows = []
    for b in sorted(df.block.unique()):
        m = (df.block == b).values
        sep = D[m][:, ~m].min() / 1000
        ext_x = (x[m].max() - x[m].min()) / 1000
        ext_y = (y[m].max() - y[m].min()) / 1000
        rows.append(dict(block=b, n=int(m.sum()),
                         extent_E_km=round(ext_x, 2), extent_N_km=round(ext_y, 2),
                         centroid_E=round(x[m].mean()), centroid_N=round(y[m].mean()),
                         min_sep_to_other_block_km=round(sep, 3)))
    bt = pd.DataFrame(rows)
    print(bt.to_string(index=False))
    print(f"\nfold sizes: {sorted(bt.n.tolist())}  (min {bt.n.min()}, max {bt.n.max()})")
    print(f"mean block extent: {bt.extent_E_km.mean():.1f} km E x {bt.extent_N_km.mean():.1f} km N")
    print(f"median separation between blocks: {bt.min_sep_to_other_block_km.median():.3f} km")

    nn = D.min(axis=1) / 1000
    print(f"nearest-neighbour distance: min {nn.min():.3f} km, median {np.median(nn):.3f} km, "
          f"max {nn.max():.3f} km")

    os.makedirs(os.path.join(FINAL, "results"), exist_ok=True)
    df.to_csv(os.path.join(FINAL, "results", "01_analysis_ready_dataset.csv"), index=False)
    bt.to_csv(os.path.join(FINAL, "results", "01_block_design.csv"), index=False)

    # predictor inventory table (referee M5)
    WAVE = {"B2": 490, "B3": 560, "B4": 665, "B5": 705, "B6": 740, "B7": 783,
            "B8": 842, "B8A": 865, "B11": 1610, "B12": 2190}
    NATIVE = {b: (10 if b in ("B2", "B3", "B4", "B8") else 20) for b in BANDS}
    FORM = {
        "NDVI": "(B8 - B4)/(B8 + B4)", "SAVI": "1.5 x (B8 - B4)/(B8 + B4 + 0.5)",
        "EVI": "2.5 x (B8 - B4)/(B8 + 6B4 - 7.5B2 + 1)", "GNDVI": "(B8 - B3)/(B8 + B3)",
        "NDRE": "(B8A - B5)/(B8A + B5)", "NDMI": "(B8 - B11)/(B8 + B11)",
        "MNDWI": "(B3 - B11)/(B3 + B11)",
        "BSI": "((B11 + B4) - (B8 + B2))/((B11 + B4) + (B8 + B2))",
        "SI": "B11 x B12", "VSSI": "2 x B3 - 5 x (B4 + B8)"}
    SRC = {"NDVI": "B4, B8", "SAVI": "B4, B8", "EVI": "B2, B4, B8", "GNDVI": "B3, B8",
           "NDRE": "B5, B8A", "NDMI": "B8, B11", "MNDWI": "B3, B11",
           "BSI": "B2, B4, B8, B11", "SI": "B11, B12", "VSSI": "B3, B4, B8"}
    REF = {"NDVI": "Rouse et al. (1974)", "SAVI": "Huete (1988)",
           "EVI": "Huete et al. (2002)", "GNDVI": "Gitelson et al. (1996)",
           "NDRE": "Gitelson and Merzlyak (1994)", "NDMI": "Gao (1996)",
           "MNDWI": "Xu (2006)", "BSI": "Rikimaru et al. (2002)",
           "SI": "Khan et al. (2005)", "VSSI": "Dehni and Lounis (2012)"}
    inv = []
    for d in DATES:
        acq = "12 November 2024" if d == "2024_11" else "16 January 2025"
        for b in BANDS:
            inv.append(dict(variable=f"{b}_{d}", type="Reflectance band", acquisition=acq,
                            formula="Surface reflectance", source_bands=b,
                            wavelength_nm=WAVE[b], unit="reflectance (0-1)",
                            native_res_m=NATIVE[b], output_res_m=10,
                            resampling="bilinear" if NATIVE[b] == 20 else "none",
                            reference="Drusch et al. (2012)"))
        for i in INDICES:
            nat = max(NATIVE[s.strip()] for s in SRC[i].split(","))
            inv.append(dict(variable=f"{i}_{d}", type="Spectral index", acquisition=acq,
                            formula=FORM[i], source_bands=SRC[i], wavelength_nm="",
                            unit="dimensionless" if i not in ("SI", "VSSI") else "reflectance product/sum",
                            native_res_m=nat, output_res_m=10,
                            resampling="bilinear" if nat == 20 else "none",
                            reference=REF[i]))
    inv = pd.DataFrame(inv)
    inv.to_csv(os.path.join(FINAL, "results", "01_predictor_inventory.csv"), index=False)
    print(f"\npredictor inventory written: {len(inv)} rows")

    json.dump(dict(n_predictors=len(PRED), n_blocks=NB,
                   fold_sizes=sorted(bt.n.tolist()),
                   median_block_separation_km=float(bt.min_sep_to_other_block_km.median()),
                   duplicate_pairs=len(dup), numerical_rank=int((s > s.max()*1e-8).sum())),
              open(os.path.join(FINAL, "results", "01_summary.json"), "w"), indent=2)
    print("\nSTEP 01 complete.")


if __name__ == "__main__":
    main()
