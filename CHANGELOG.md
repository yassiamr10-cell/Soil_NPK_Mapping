# Changelog

## v1.0.0 — 2026-08-28

First public release, accompanying the revised submission to *Environmental
Monitoring and Assessment*.

### Analysis
- Nested spatial block cross-validation over 10 blocks is the primary
  evaluation; all reported statistics come from untouched outer folds.
- Five benchmark models added on identical folds: intercept-only, ridge, PLS,
  ordinary kriging, regression kriging.
- Permutation importance on held-out folds replaces impurity and gain importance.
- Local uncertainty and an area of applicability accompany every map.
- 10 m prediction grid (9,343,965 pixels), replacing the decimated
  grid used previously.

### Corrections to the first submission
- `SI` was computing −NDMI, `VSSI` was computing −NDSI, and `NDSI`/`MNDWI` were
  interchanged. Two of 42 columns were sign-flipped duplicates. Predictor count
  corrected from 41 to 40.
- Covariates are monthly **median composites** of
  28 and 24 scenes across four MGRS tiles, not two
  single cloud-free acquisitions.
- Castaldi reference corrected: the cited DOI resolved to an unrelated paper.
- Mean total nitrogen corrected from 1 683 to 1,613.3 mg kg⁻¹.
- Claim that XGBoost outperforms Random Forest withdrawn; the paired difference is
  not significant.
