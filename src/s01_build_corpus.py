"""Step 1 - Build the paper-level and authorship-level tables.

Input : WoS Core Collection export (932 records, exported 23 Feb 2023)
Output: data/processed/papers.csv            one row per paper (2008-2023)
        data/raw/authorships_private.csv      one row per author slot (contains names)
        data/processed/authorships.csv        same, names removed (shareable)
"""
import numpy as np
import pandas as pd

from common import (GENDER_FILE, PROCESSED, RAW, WOS_FILE, YEAR_MAX, YEAR_MIN,
                    country_of, org_of, split_addresses)

wos = pd.read_excel(WOS_FILE)
n_all = len(wos)
wos = wos.rename(columns={"UT (Unique WOS ID)": "ut", "Publication Year": "year"})
# 5 early-access records have no publication year: use the early-access year (all 2022)
ea_year = pd.to_numeric(wos["Early Access Date"].astype(str).str[-4:], errors="coerce")
wos["year"] = wos["year"].fillna(ea_year).astype(int)
win = wos[(wos["year"] >= YEAR_MIN) & (wos["year"] <= YEAR_MAX)].copy()

# ---------------------------------------------------------------- papers
p = pd.DataFrame({
    "ut": win["ut"],
    "doi": win["DOI"],
    "pmid": win["Pubmed Id"],
    "year": win["year"],
    "doc_type": win["Document Type"].str.split(";").str[0].str.strip().str.lower(),
    "journal": win["Source Title"].str.title(),
    "wos_categories": win["WoS Categories"],
    "cites_wos": win["Times Cited, WoS Core"].fillna(0).astype(int),
    "cites_all": win["Times Cited, All Databases"].fillna(0).astype(int),
    "funded": win["Funding Name Preferred"].notna().astype(int),
    "oa": win["Open Access Designations"].notna().astype(int),
    "oa_types": win["Open Access Designations"],
})
p["review"] = (p["doc_type"] == "review").astype(int)

# Field- and age-normalised citations: citations / mean citations of all papers
# published the same year (mean-normalised citation score, MNCS-style).
p["cites_norm"] = p["cites_wos"] / p.groupby("year")["cites_wos"].transform("mean")
p["cites_pct"] = p.groupby("year")["cites_wos"].rank(pct=True)  # percentile within year

# ---------------------------------------------------------------- authorships
gender = pd.read_csv(GENDER_FILE)
gender["key"] = gender["full_name"].str.strip().str.lower()
gmap = gender.drop_duplicates("key").set_index("key")
rows = []
for _, r in win.iterrows():
    names = [n.strip() for n in str(r["Author Full Names"]).split(";") if n.strip()]
    addrs = split_addresses(r["Addresses"])
    rp = r["Reprint Addresses"]
    for i, name in enumerate(names):
        key = name.lower()
        mine = [a for who, a in addrs if key in who]
        if not mine and addrs and all(not who for who, _ in addrs):
            mine = [a for _, a in addrs]  # old format: addresses not linked to authors
        countries = sorted({c for c in (country_of(a) for a in mine) if c})
        orgs = sorted({org_of(a) for a in mine})
        g = gmap["ga_gender"].get(key, "not_in_file")
        rows.append({
            "ut": r["ut"], "year": r["year"], "position": i + 1, "n_authors": len(names),
            "name": name, "gender": g,
            "ga_accuracy": gmap["ga_accuracy"].get(key, np.nan),
            "countries": "|".join(countries), "n_affil_countries": len(countries),
            "orgs": "|".join(orgs),
        })
au = pd.DataFrame(rows)
au["is_first"] = (au["position"] == 1).astype(int)
au["is_last"] = ((au["position"] == au["n_authors"]) & (au["n_authors"] > 1)).astype(int)
au["gender"] = au["gender"].replace({"unknown": "unclassified", "not_in_file": "unclassified"})

# ---------------------------------------------------------------- paper-level author summaries
def first_country(s):
    return s.split("|")[0] if isinstance(s, str) and s else None

agg = au.groupby("ut").agg(
    n_authors=("position", "size"),
    n_women=("gender", lambda s: (s == "female").sum()),
    n_men=("gender", lambda s: (s == "male").sum()),
    n_unclass=("gender", lambda s: (s == "unclassified").sum()),
)
first = au[au.is_first == 1].set_index("ut")
last = au[au.is_last == 1].set_index("ut")
agg["first_gender"] = first["gender"]
agg["last_gender"] = last["gender"]
agg["first_countries"] = first["countries"]
agg["last_countries"] = last["countries"]

# countries and unique organisations per paper (from all addresses, not per author)
geo = []
for _, r in win.iterrows():
    addrs = split_addresses(r["Addresses"])
    cs = sorted({c for c in (country_of(a) for _, a in addrs) if c})
    if not cs and isinstance(r["Reprint Addresses"], str):
        c = country_of(r["Reprint Addresses"].rstrip("."))
        cs = [c] if c else []
    geo.append({"ut": r["ut"], "countries": "|".join(cs), "n_countries": len(cs),
                "n_orgs": len({org_of(a) for _, a in addrs}) or np.nan})
geo = pd.DataFrame(geo).set_index("ut")

p = p.set_index("ut").join(agg).join(geo).reset_index()
p["share_women"] = p["n_women"] / (p["n_women"] + p["n_men"]).replace(0, np.nan)
p["intl_collab"] = (p["n_countries"] > 1).astype(int)
p["solo"] = (p["n_authors"] == 1).astype(int)

p.to_csv(PROCESSED / "papers.csv", index=False)
au.to_csv(RAW / "authorships_private.csv", index=False)
au.drop(columns=["name", "orgs"]).to_csv(PROCESSED / "authorships.csv", index=False)

print(f"WoS records: {n_all}; in window {YEAR_MIN}-{YEAR_MAX}: {len(p)}")
print(f"authorships: {len(au)}; unique names: {au['name'].str.lower().nunique()}")
print("gender of authorships:", au["gender"].value_counts().to_dict())
print("papers missing country:", (p["n_countries"] == 0).sum())
print("authors without country:", (au["n_affil_countries"] == 0).sum())
