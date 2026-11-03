"""Step 2 - Add geography, funders, study countries and WHO-priority tags.

Output: data/processed/papers_enriched.csv   (one row per paper, shareable)
        data/processed/paper_funders.csv     (paper x harmonised funder group)
        outputs/tables/funder_harmonisation_check.csv (raw names -> group, for manual review)
"""
import re

import numpy as np
import pandas as pd

from common import PROCESSED, REFERENCE, TABLES, WOS_FILE, YEAR_MIN

p = pd.read_csv(PROCESSED / "papers.csv")
wos = pd.read_excel(WOS_FILE).rename(columns={"UT (Unique WOS ID)": "ut"})
wos = wos[wos["ut"].isin(p["ut"])].set_index("ut")
wb = pd.read_csv(REFERENCE / "country_wb_fy2023.csv").set_index("country")
AFRICA = set(wb.index[wb["africa"] == 1])


def split(s):
    return [x for x in str(s).split("|") if x and x != "nan"]


# ------------------------------------------------------------------ geography of authorship
def any_in(countries, group):
    return int(bool(set(split(countries)) & group))


p["any_african_author"] = p["countries"].apply(lambda s: any_in(s, AFRICA))
p["first_african"] = p["first_countries"].apply(lambda s: any_in(s, AFRICA))
p["last_african"] = p["last_countries"].apply(lambda s: any_in(s, AFRICA))
p["first_country"] = p["first_countries"].apply(lambda s: (split(s) or [None])[0])
p["last_country"] = p["last_countries"].apply(lambda s: (split(s) or [None])[0])
for pos in ("first", "last"):
    p[f"{pos}_region"] = p[f"{pos}_country"].map(wb["wb_region"])
    p[f"{pos}_income"] = p[f"{pos}_country"].map(wb["wb_income"])
p["us_author"] = p["countries"].apply(lambda s: int("United States" in split(s)))

# ------------------------------------------------------------------ study countries (African countries named in the text)
AFRICAN_NAMES = {
    "Uganda": r"ugand", "Kenya": r"\bkenya", "Angola": r"\b(in|of|from|to|across|throughout|within|northern|province of) angola\b|u[ií]ge|luanda|angola[,']s? (outbreak|epidemic|government|ministry)", "Tanzania": r"tanzani",
    "DR Congo": r"democratic republic of (the )?congo|\bdrc\b|\b(in|of|from|to|northern|southern) zaire\b|kinshasa|kikwit|yambuku|durba|watsa",
    "Congo Republic": r"(?<!democratic )republic of (the )?congo|\brep\.? congo|brazzaville",
    "Guinea": r"(?<!equatorial )(?<!papua new )\bguinea\b(?! pigs?)(?!-bissau)|conakry|gu[eé]ck[eé]dou",
    "Equatorial Guinea": r"equatorial guinea", "Ghana": r"\bghana", "Sierra Leone": r"sierra leone",
    "Liberia": r"\bliberia", "Gabon": r"\bgabon", "South Africa": r"south africa", "Zimbabwe": r"zimbabwe",
    "Rwanda": r"rwanda", "Sudan": r"\b(in|of|from|to|across|within|northern) sudan\b|khartoum|sudan[,']s? (outbreak|epidemic|government|ministry)", "South Sudan": r"south sudan|southern sudan", "Nigeria": r"nigeria",
    "Zambia": r"zambia", "Ethiopia": r"ethiopia", "Cameroon": r"cameroon", "Senegal": r"senegal",
    "Cote d'Ivoire": r"\b(in|of|from) (the )?(c[oô]te d.?ivoire|ivory coast)\b|abidjan|ta[iï] (national )?(park|forest) in", "Mali": r"\bmali\b", "Burkina Faso": r"burkina",
    "Mozambique": r"mozambiq", "Burundi": r"burundi", "Central African Republic": r"central african republic",
    "Madagascar": r"madagascar", "Malawi": r"malawi", "Egypt": r"\begypt(?!ian (fruit|rousette|bat))",
}
text = (wos["Article Title"].fillna("") + " . " + wos["Abstract"].fillna("") + " . "
        + wos["Author Keywords"].fillna("")).str.lower()
study = {}
for ut, t in text.items():
    # remove virus, strain and disease names that contain place names
    t = re.sub(r"egyptian (fruit )?(rousette|bats?)|rousettus aegyptiacus|crimean[- /]+congo", " ", t)
    t = re.sub(r"ebola[- ](sudan|zaire|reston|ivory coast)|subtype (sudan|zaire)|\b(sebov|zebov|sudv|ebov-[sz])\b"
               r"|(sudan|zaire|ta[iï] forest|ivory coast|c[oô]te d.?ivoire|bundibugyo|reston)[- ](ebola)?(virus|ebolavirus)"
               r"|(sudan|zaire|bundibugyo|ivory coast)[- ]ebola", " ", t)
    t = re.sub(r"angolan? (strain|variant|isolate|virus|lineage|marv|challenge)|(strain|variant|isolate|marv|marburg virus)[- ]angola"
               r"|\bangola[- ]?(368|2005)\b|\bangola and (ravn|musoke|popp)|(ravn|musoke|popp|ci67) and angola", " ", t)
    study[ut] = sorted(c for c, rx in AFRICAN_NAMES.items() if re.search(rx, t))
p["study_countries"] = p["ut"].map(lambda u: "|".join(study.get(u, [])))
p["about_africa"] = (p["study_countries"] != "").astype(int)


def local(row, which):
    sc = set(split(row["study_countries"]))
    return int(bool(sc & set(split(row[which])))) if sc else np.nan


p["any_local_author"] = p.apply(lambda r: local(r, "countries"), axis=1)
p["first_local"] = p.apply(lambda r: local(r, "first_countries"), axis=1)
p["last_local"] = p.apply(lambda r: local(r, "last_countries"), axis=1)

# ------------------------------------------------------------------ funders
rules = pd.read_csv(REFERENCE / "funder_rules.csv")
rules["rx"] = rules["pattern"].apply(lambda s: re.compile(s, re.I))


def classify(name):
    for _, r in rules.iterrows():
        if r["rx"].search(name):
            return r["funder_group"], r["funder_country"], r["funder_type"]
    return "Other / unclassified", "Unknown", "Unknown"


fund_rows, check = [], {}
for ut, s in wos["Funding Name Preferred"].dropna().items():
    for raw in {x.strip() for x in str(s).split(";") if x.strip()}:
        g, c, t = check.setdefault(raw, classify(raw))
        fund_rows.append({"ut": ut, "funder_raw": raw, "funder_group": g, "funder_country": c, "funder_type": t})
pf = pd.DataFrame(fund_rows)
pf_g = pf.drop_duplicates(["ut", "funder_group"])
pf_g.drop(columns="funder_raw").to_csv(PROCESSED / "paper_funders.csv", index=False)

chk = (pf.groupby(["funder_raw", "funder_group", "funder_country", "funder_type"]).size()
       .rename("papers").reset_index().sort_values("papers", ascending=False))
chk.to_csv(TABLES / "funder_harmonisation_check.csv", index=False)

fc = pf_g.groupby("ut")["funder_country"].apply(lambda s: "|".join(sorted(set(s))))
p["funder_countries"] = p["ut"].map(fc).fillna("")
p["us_funded"] = p["funder_countries"].str.contains("United States").astype(int)
p["african_funded"] = p["funder_countries"].str.contains("Africa").astype(int)
p["us_defence_funded"] = p["ut"].isin(pf_g.loc[pf_g["funder_type"] == "Government (defence)", "ut"]).astype(int)

# ------------------------------------------------------------------ WHO 2025 Marburg research priorities (dictionary tags)
code = pd.read_csv(REFERENCE / "who_priorities_codebook.csv")
for _, r in code.iterrows():
    rx = re.compile(r["regex"], re.I)
    p[r["code"]] = p["ut"].map(lambda u: int(bool(rx.search(text.get(u, ""))))).fillna(0).astype(int)
p["has_abstract"] = p["ut"].map(wos["Abstract"].notna()).astype(int)

p.to_csv(PROCESSED / "papers_enriched.csv", index=False)

print("papers:", len(p))
print("about an African country:", p["about_africa"].sum())
print("study countries:", pd.Series([c for s in p["study_countries"] for c in split(s)]).value_counts().head(12).to_dict())
print("funded papers:", p["funded"].sum(), "| funder share unclassified:",
      round((pf_g["funder_group"] == "Other / unclassified").mean(), 3))
print(pf_g["funder_group"].value_counts().head(15).to_string())
print(p[[c for c in code["code"]]].mean().round(3).to_string())
