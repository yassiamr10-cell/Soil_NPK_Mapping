# -*- coding: utf-8 -*-
"""
Run the analysis pipeline in order.

Each step is checked for its inputs before it runs, so a missing prerequisite is
reported rather than causing a traceback halfway through. Steps that need the
Sentinel-2 band rasters are skipped with a message if those are not present.

    python run_all.py            # run everything that can run
    python run_all.py --list     # show the pipeline without running it
"""
import os, sys, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "code", "python")

# (script, needs the 10 m Sentinel-2 band rasters?)
STEPS = [
    ("01_build_predictors_and_blocks.py", False),
    ("02_nested_cv_and_baselines.py",     False),
    ("03_predict_10m_maps.py",            True),
    ("04_figures_models.py",              False),
    ("05_figures_maps.py",                False),
    ("06_tables.py",                      False),
    ("11_extraction_support_sensitivity.py", True),
    ("12_verify_dois.py",                 False),
    ("14_scene_inventory.py",             False),
    ("17_reconcile_scene_inventory.py",   False),
    ("16_final_verification.py",          False),
]

COVDIR = r"d:\Doctorat\article1\covariates_clipped"


def have_rasters():
    return os.path.isdir(COVDIR) and len(
        [f for f in os.listdir(COVDIR) if f.endswith(".tif")]) >= 20


def main():
    if "--list" in sys.argv:
        print("Pipeline order:")
        for s, need in STEPS:
            print(f"   {s}" + ("   [needs the 10 m band rasters]" if need else ""))
        return
    rasters = have_rasters()
    if not rasters:
        print(f"NOTE: Sentinel-2 band rasters not found in {COVDIR}.")
        print("      Steps 03 and 11 will be skipped. Regenerate the rasters with")
        print("      code/earthengine/02_export_covariates.js if you need them.\n")
    t0 = time.time()
    for script, need in STEPS:
        path = os.path.join(PY, script)
        if not os.path.exists(path):
            print(f"SKIP  {script}  (not found)"); continue
        if need and not rasters:
            print(f"SKIP  {script}  (needs the band rasters)"); continue
        print(f"RUN   {script}")
        r = subprocess.run([sys.executable, path])
        if r.returncode != 0:
            print(f"\nFAILED at {script} (exit {r.returncode}).")
            sys.exit(r.returncode)
    print(f"\nPipeline finished in {(time.time()-t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
