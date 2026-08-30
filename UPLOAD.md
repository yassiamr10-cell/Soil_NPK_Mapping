# Publishing this repository

## 1. Set your username

`YOUR-GITHUB-USERNAME` appears in `README.md`, `CITATION.cff` and this file.

```bash
grep -rl "YOUR-GITHUB-USERNAME" . | xargs sed -i 's/YOUR-GITHUB-USERNAME/yourname/g'
```

On Windows PowerShell:

```powershell
Get-ChildItem -Recurse -Include *.md,*.cff |
  ForEach-Object { (Get-Content $_ -Raw) -replace 'YOUR-GITHUB-USERNAME','yourname' |
  Set-Content $_ -Encoding utf8 }
```

## 2. Push

No Git LFS is needed: the repository is about 35 MB because the rasters are
distributed through Zenodo instead.

```bash
cd d:\Doctorat\article1\outputs_fast\FINAL\github
git init
git add .
git commit -m "v1.0.0: data, code and outputs for Beni Moussa NPK mapping"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-USERNAME/beni-moussa-npk-mapping.git
git push -u origin main
```

Make the repository **public**.

## 3. Connect Zenodo and mint the DOI

1. Sign in at https://zenodo.org with your GitHub account.
2. Settings → GitHub → switch on the toggle for `beni-moussa-npk-mapping`.
3. On GitHub: Releases → Create a new release → tag `v1.0.0` → Publish.
4. Zenodo captures the release and issues a DOI within a minute.

`.zenodo.json` pre-fills the record's title, authors, licence, keywords and
description, so nothing needs retyping.

## 4. Attach the rasters to the Zenodo record

The eleven GeoTIFFs are not in Git. After the Zenodo record appears:

1. Open the record → Edit.
2. Upload the eleven files from `outputs_fast/FINAL/maps/`.
3. Publish. This creates a new version of the record; use that DOI.

Total upload about 271 MB; Zenodo's per-record limit is 50 GB.

## 5. Put the DOI in three places

- the manuscript, replacing `[ZENODO DOI]` in Data Availability
- `README.md`, replacing both `PENDING` placeholders in the badge
- `CITATION.cff`, as a new `doi:` field

## Checklist before pushing

- [ ] `YOUR-GITHUB-USERNAME` replaced everywhere
- [ ] repository is public
- [ ] `data/soil/01_analysis_ready_dataset.csv` holds coordinates you are willing to
      publish; if not, jitter within 250 m and say so in `data/README.md`
- [ ] the manuscript and the response letter are **not** here — they stay private
      until the paper is accepted, because the response letter quotes the referee
      report
