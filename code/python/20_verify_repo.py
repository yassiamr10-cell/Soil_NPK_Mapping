# -*- coding: utf-8 -*-
"""STEP 20 - Verify the assembled GitHub repository."""
import os, json, ast, glob
import pandas as pd

GH = r"d:\Doctorat\article1\outputs_fast\FINAL\github"
ok, bad = [], []
def chk(n, c, d=""): (ok if c else bad).append((n, d))

# ---- required root files
for f in ["README.md", "UPLOAD.md", "CHANGELOG.md", "LICENSE", "LICENSE-CODE",
          "CITATION.cff", ".zenodo.json", ".gitattributes", ".gitignore",
          "environment.yml", "requirements.txt", "run_all.py", "MANIFEST.csv"]:
    chk(f"root file {f}", os.path.exists(os.path.join(GH, f)))

# ---- required folders and per-folder READMEs
for d_ in ["code/earthengine", "code/python", "data/soil", "data/spatial",
           "data/sentinel2", "outputs/figures", "outputs/tables", "outputs/results",
           "outputs/maps"]:
    chk(f"folder {d_}", os.path.isdir(os.path.join(GH, d_)))
for d_ in ["code", "data", "outputs", "outputs/maps"]:
    chk(f"{d_}/README.md", os.path.exists(os.path.join(GH, d_, "README.md")))

# ---- no rasters tracked
tifs = glob.glob(os.path.join(GH, "**", "*.tif"), recursive=True)
chk("no GeoTIFFs in the repository", not tifs, f"{len(tifs)} found")

# ---- no manuscript or response letter
docs = glob.glob(os.path.join(GH, "**", "*.docx"), recursive=True)
chk("no manuscript or response letter published", not docs,
    ", ".join(os.path.basename(x) for x in docs))

# ---- size
man = pd.read_csv(os.path.join(GH, "MANIFEST.csv"))
tot = man.size_bytes.sum()
chk("repository under 100 MB", tot < 100e6, f"{tot/1e6:.1f} MB")
chk("no file over 50 MB (Git LFS unnecessary)", man.size_bytes.max() < 50e6,
    f"largest {man.size_bytes.max()/1e6:.1f} MB")
chk("no file over GitHub's 100 MB hard limit", man.size_bytes.max() < 100e6)

# ---- generated code is valid
for f in glob.glob(os.path.join(GH, "**", "*.py"), recursive=True):
    try:
        ast.parse(open(f, encoding="utf-8").read())
        v = True; err = ""
    except SyntaxError as e:
        v = False; err = str(e)
    chk(f"valid Python: {os.path.relpath(f, GH)}", v, err)

# ---- metadata files parse
try:
    json.load(open(os.path.join(GH, ".zenodo.json"), encoding="utf-8"))
    chk(".zenodo.json is valid JSON", True)
except Exception as e:
    chk(".zenodo.json is valid JSON", False, str(e))

cff = open(os.path.join(GH, "CITATION.cff"), encoding="utf-8").read()
for k in ["cff-version:", "title:", "authors:", "license:", "version:",
          "repository-code:"]:
    chk(f"CITATION.cff has {k}", k in cff)

# ---- encoding and line endings
for f in glob.glob(os.path.join(GH, "**", "*"), recursive=True):
    if not os.path.isfile(f):
        continue
    if os.path.splitext(f)[1].lower() not in (".md", ".py", ".js", ".yml", ".cff",
                                              ".json", ".txt", ".csv"):
        continue
    b = open(f, "rb").read()
    rel = os.path.relpath(f, GH)
    try:
        b.decode("utf-8")
    except UnicodeDecodeError as e:
        chk(f"utf-8: {rel}", False, str(e)); continue
    if b[:3] == b"\xef\xbb\xbf":
        chk(f"no BOM: {rel}", False)

# ---- shapefile complete
for ext in ("shp", "shx", "dbf", "prj", "cpg"):
    chk(f"shapefile part .{ext}",
        os.path.exists(os.path.join(GH, "data", "spatial", f"Beni_Moussa.{ext}")))

# ---- key data files present
for f in ["data/soil/01_analysis_ready_dataset.csv",
          "data/soil/01_predictor_inventory.csv",
          "data/sentinel2/14_scene_inventory_used.csv",
          "outputs/results/02_out_of_fold_predictions.csv",
          "outputs/results/02_metrics_all_schemes.csv",
          "outputs/tables/All_Tables_Revision2.xlsx"]:
    chk(f"key file {f}", os.path.exists(os.path.join(GH, f)))

ds = pd.read_csv(os.path.join(GH, "data", "soil", "01_analysis_ready_dataset.csv"))
chk("analysis dataset has 110 rows", len(ds) == 110, f"{len(ds)} rows")
pred = [c for c in ds.columns if c not in
        ("Echantillon", "Latitude", "Longitude", "N", "P", "K", "x_m", "y_m", "block")]
chk("analysis dataset has 40 predictors", len(pred) == 40, f"{len(pred)}")

# ---- figures paired PNG + PDF
png = {os.path.splitext(os.path.basename(f))[0]
       for f in glob.glob(os.path.join(GH, "outputs", "figures", "*.png"))}
pdf = {os.path.splitext(os.path.basename(f))[0]
       for f in glob.glob(os.path.join(GH, "outputs", "figures", "*.pdf"))}
chk("every figure has both PNG and PDF", png == pdf and len(png) == 10,
    f"{len(png)} PNG, {len(pdf)} PDF")

# ---- placeholders flagged
rd = open(os.path.join(GH, "README.md"), encoding="utf-8").read()
chk("README flags the username placeholder", "YOUR-GITHUB-USERNAME" in rd)
chk("README flags the pending DOI", "PENDING" in rd)
chk("README explains the raster decision", "not** tracked in Git" in rd)
chk("gitignore excludes rasters", "outputs/maps/*.tif" in
    open(os.path.join(GH, ".gitignore"), encoding="utf-8").read())

print("PASSED (%d)" % len(ok))
for n, d_ in ok:
    print(f"   OK    {n}" + (f"  -  {d_}" if d_ else ""))
if bad:
    print("\nFAILED (%d)" % len(bad))
    for n, d_ in bad:
        print(f"   FAIL  {n}" + (f"  -  {d_}" if d_ else ""))
else:
    print("\nRepository verified.")

print("\n--- TREE ---")
for root, dirs, files in os.walk(GH):
    dirs.sort()
    rel = os.path.relpath(root, GH)
    depth = 0 if rel == "." else rel.count(os.sep) + 1
    if rel != ".":
        print("  " * depth + os.path.basename(root) + "/")
    for f in sorted(files):
        if depth == 0 or len(files) <= 6:
            print("  " * (depth + 1) + f)
    if depth > 0 and len(files) > 6:
        sz = sum(os.path.getsize(os.path.join(root, f)) for f in files)
        print("  " * (depth + 1) + f"... {len(files)} files, {sz/1e6:.1f} MB")
