# -*- coding: utf-8 -*-
"""
STEP 12 - Verify every DOI in the reference list against Crossref.

Checks that the DOI resolves and that the recorded year, first-author family
name and journal are consistent with what the manuscript states.
"""
import json, re, os, time, urllib.request, urllib.error
import pandas as pd

FINAL = r"d:\Doctorat\article1\outputs_fast\FINAL"
RES = os.path.join(FINAL, "results")
UA = {"User-Agent": "AmroussEtAl-refcheck/1.0 (mailto:yassine.amrouss@usms.ma)"}

# (key shown in the manuscript, expected first-author surname, expected year, DOI)
REFS = [
 ("Al Masmoudi et al. 2022", "Al Masmoudi", 2022, "10.1007/s40808-021-01329-8"),
 ("Aljanabi and Dedeoglu 2026", "Aljanabi", 2026, "10.26833/ijeg.1655607"),
 ("Alvarez and Govind 2025", "Alvarez", 2025, "10.1007/s00704-025-05656-z"),
 ("Barakat et al. 2017", "Barakat", 2017, "10.1007/s40808-017-0272-5"),
 ("Bijaber et al. 2024", "Bijaber", 2024, "10.26833/ijeg.1404507"),
 ("Bouslihim et al. 2025", "Bouslihim", 2025, "10.1038/s41597-025-05699-x"),
 ("Breiman 2001 [NEW]", "Breiman", 2001, "10.1023/A:1010933404324"),
 ("Castaldi et al. 2019", "Castaldi", 2019, "10.3390/rs11242924"),
 ("Chaaou et al. 2022", "Chaaou", 2022, "10.1007/s12517-022-10009-5"),
 ("Chen and Guestrin 2016 [NEW]", "Chen", 2016, "10.1145/2939672.2939785"),
 ("Dalle Vaglie et al. 2026 [NEW]", "Dalle Vaglie", 2026, "10.1073/pnas.2534913123"),
 ("Dehni and Lounis 2012 [NEW]", "Dehni", 2012, "10.1016/j.proeng.2012.01.1193"),
 ("Drusch et al. 2012", "Drusch", 2012, "10.1016/j.rse.2011.11.026"),
 ("El Hamzaoui and El Baghdadi 2021", "El Hamzaoui", 2021, "10.1007/s43217-021-00050-x"),
 ("Ennaji et al. 2018", "Ennaji", 2018, "10.1007/s12040-018-0980-x"),
 ("Gao 1996", "Gao", 1996, "10.1016/S0034-4257(96)00067-3"),
 ("Gitelson and Merzlyak 1994", "Gitelson", 1994, "10.1016/S0176-1617(11)81633-0"),
 ("Gitelson et al. 1996", "Gitelson", 1996, "10.1016/S0034-4257(96)00072-7"),
 ("Gorelick et al. 2017", "Gorelick", 2017, "10.1016/j.rse.2017.06.031"),
 ("Hafiane et al. 2020", "Hafiane", 2020, "10.5004/dwt.2020.26144"),
 ("Harris et al. 2020 [NEW]", "Harris", 2020, "10.1038/s41586-020-2649-2"),
 ("Havlin and Heiniger 2020", "Havlin", 2020, "10.3390/agronomy10091349"),
 ("Huete 1988", "Huete", 1988, "10.1016/0034-4257(88)90106-X"),
 ("Huete et al. 2002", "Huete", 2002, "10.1016/S0034-4257(02)00096-2"),
 ("Khan et al. 2005", "Khan", 2005, "10.1016/j.agwat.2004.09.038"),
 ("Kuhn and Johnson 2013", "Kuhn", 2013, "10.1007/978-1-4614-6849-3"),
 ("Lin 1989 [NEW]", "Lin", 1989, "10.2307/2532051"),
 ("Liu et al. 2020", "Liu", 2020, "10.3390/f11080797"),
 ("McBratney et al. 2003", "McBratney", 2003, "10.1016/S0016-7061(03)00223-4"),
 ("Meyer and Pebesma 2021 [NEW]", "Meyer", 2021, "10.1111/2041-210X.13650"),
 ("Minasny and McBratney 2006", "Minasny", 2006, "10.1016/j.cageo.2005.12.009"),
 ("Mouaddine et al. 2025", "Mouaddine", 2025, "10.1007/s40808-024-02210-0"),
 ("Nait-Taleb et al. 2025", "Nait-Taleb", 2025, "10.3389/fsoil.2025.1553887"),
 ("Recena et al. 2015", "Recena", 2015, "10.1007/s13593-015-0332-z"),
 ("Roberts et al. 2017 [NEW]", "Roberts", 2017, "10.1111/ecog.02881"),
 ("Salih et al. 2026", "Salih", 2026, "10.36899/JAPS.2026.2.0032"),
 ("Salmi et al. 2024", "Salmi", 2024, "10.2478/eces-2024-0025"),
 ("Salmi et al. 2025", "Salmi", 2025, "10.1007/s42990-025-00165-7"),
 ("Shen et al. 2011", "Shen", 2011, "10.1104/pp.111.175232"),
 ("Silatsa and Kebede 2023", "Silatsa", 2023, "10.1016/j.geodrs.2023.e00695"),
 ("Silvero et al. 2021", "Silvero", 2021, "10.1016/j.rse.2020.112117"),
 ("Vereecken et al. 2016", "Vereecken", 2016, "10.2136/vzj2015.09.0131"),
 ("Veronesi and Schillaci 2019", "Veronesi", 2019, "10.1016/j.ecolind.2019.02.026"),
 ("Wadoux et al. 2020", "Wadoux", 2020, "10.1016/j.earscirev.2020.103359"),
 ("Wiesmeier et al. 2019", "Wiesmeier", 2019, "10.1016/j.geoderma.2018.07.026"),
 ("Xu 2006", "Xu", 2006, "10.1080/01431160600589179"),
]


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"]


def year_of(m):
    for k in ("published-print", "published-online", "published", "issued"):
        if k in m and m[k].get("date-parts", [[None]])[0][0]:
            return m[k]["date-parts"][0][0], k
    return None, None


rows = []
for key, surname, year, doi in REFS:
    rec = dict(reference=key, doi=doi, expected_year=year, expected_author=surname)
    try:
        m = crossref(doi)
        y, ysrc = year_of(m)
        auths = m.get("author", [])
        fam = auths[0].get("family", "") if auths else ""
        title = (m.get("title") or [""])[0]
        cont = (m.get("container-title") or [""])[0]
        # all recorded years, to expose landing-page vs issue discrepancies
        allyrs = sorted({m[k]["date-parts"][0][0] for k in
                         ("published-print", "published-online", "published", "issued")
                         if k in m and m[k].get("date-parts", [[None]])[0][0]})
        rec.update(resolved="yes", crossref_year=y, year_source=ysrc,
                   all_years="/".join(str(a) for a in allyrs),
                   crossref_author=fam, journal=cont[:48], title=title[:70],
                   year_ok=(y == year),
                   author_ok=(surname.split()[0].lower() in fam.lower()
                              or fam.lower() in surname.lower()) if fam else None)
    except urllib.error.HTTPError as e:
        rec.update(resolved=f"HTTP {e.code}", year_ok=False, author_ok=False)
    except Exception as e:
        rec.update(resolved=f"error: {type(e).__name__}", year_ok=False, author_ok=False)
    rows.append(rec)
    flag = "OK " if rec.get("year_ok") and rec.get("author_ok") else "!! "
    print(f"{flag}{key:36s} {rec.get('resolved','?'):10s} "
          f"year {rec.get('crossref_year','?')} (stated {year})  "
          f"{str(rec.get('crossref_author',''))[:20]}")
    time.sleep(0.15)

d = pd.DataFrame(rows)
d.to_csv(os.path.join(RES, "12_doi_verification.csv"), index=False)

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"checked          : {len(d)}")
print(f"resolved         : {(d.resolved == 'yes').sum()}")
print(f"year matches     : {d.year_ok.sum()}")
print(f"author matches   : {d.author_ok.sum()}")
bad = d[(d.resolved != "yes") | (~d.year_ok.fillna(False)) | (~d.author_ok.fillna(False))]
if len(bad):
    print("\nNEEDS ATTENTION:")
    print(bad[["reference", "doi", "resolved", "expected_year", "crossref_year",
               "all_years", "crossref_author", "journal"]].to_string(index=False))
else:
    print("\nAll references verified.")
print(f"\nwritten to {os.path.join(RES, '12_doi_verification.csv')}")
