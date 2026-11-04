"""Step 8 - Aggregate tables for the interactive explorer (release/explorer).

Only counts are written; no author names, no paper-level gender.
Privacy rules:
  * Gender is aggregated by year x position only (and by topic x position over all years),
    never by year x topic, so no cell can point to the gender of one named paper's author.
  * 2023 has only January-February papers (n=3), so it is merged with 2022 ("2022-23").
  * Any gender cell with fewer than MIN_CELL classified authors is suppressed.
"""
import json
from pathlib import Path

import pandas as pd

from common import PROCESSED, REFERENCE

MIN_CELL = 10
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "explorer" / "data"
OUT.mkdir(parents=True, exist_ok=True)

p = pd.read_csv(PROCESSED / "papers_enriched.csv")
a = pd.read_csv(PROCESSED / "authorships.csv")
pf = pd.read_csv(PROCESSED / "paper_funders.csv")
tp = pd.read_csv(PROCESSED / "paper_topics.csv")[["ut", "topic"]]
labels = pd.read_csv(REFERENCE / "topic_labels.csv")
who = pd.read_csv(REFERENCE / "who_priorities_codebook.csv")

ybin = lambda y: int(min(y, 2022))
p["year"] = p.year.map(ybin)
a["year"] = a.year.map(ybin)
p = p.merge(tp, on="ut", how="left")
p["topic"] = p.topic.fillna(-1).astype(int)

# ---- 1. papers by year x topic -------------------------------------------------------
aa = p.about_africa == 1
p["aa"] = aa.astype(int)
p["aa_first_local"] = (aa & (p.first_local == 1)).astype(int)
p["aa_last_local"] = (aa & (p.last_local == 1)).astype(int)
p["aa_first_african"] = (aa & (p.first_african == 1)).astype(int)
p["aa_last_african"] = (aa & (p.last_african == 1)).astype(int)
p["african_led"] = ((p.first_african == 1) | (p.last_african == 1)).astype(int)
cols = ["funded", "us_funded", "us_defence_funded", "african_funded", "any_african_author",
        "african_led", "aa", "aa_first_local", "aa_last_local", "aa_first_african", "aa_last_african"]
x_papers = p.groupby(["year", "topic"])[cols].sum().astype(int)
x_papers.insert(0, "papers", p.groupby(["year", "topic"]).size())
x_papers = x_papers.reset_index()

# ---- 2. gender by year x position (privacy-safe) ----------------------------------------
def gcount(df, keys):
    rows = []
    for pos, s in [("All", df), ("First", df[df.is_first == 1]), ("Last", df[df.is_last == 1])]:
        g = s.groupby(keys + ["gender"]).size().unstack(fill_value=0)
        for c in ["female", "male", "unclassified"]:
            if c not in g:
                g[c] = 0
        g = g.reset_index().rename(columns={"female": "women", "male": "men"})
        g["position"] = pos
        rows.append(g[keys + ["position", "women", "men", "unclassified"]])
    out = pd.concat(rows, ignore_index=True)
    small = (out.women + out.men) < MIN_CELL
    out.loc[small, ["women", "men", "unclassified"]] = None
    out["suppressed"] = small.astype(int)
    return out

x_gender_year = gcount(a, ["year"])
a2 = a.merge(tp, on="ut", how="left")
a2["topic"] = a2.topic.fillna(-1).astype(int)
x_gender_topic = gcount(a2, ["topic"])

# ---- 3. funders by year x topic x funder country; flow to last-author region -------------
top_fc = ["United States", "Japan", "Germany", "Canada", "China", "European Union", "United Kingdom", "Africa"]
pf["fc"] = pf.funder_country.where(pf.funder_country.isin(top_fc), "Other / unknown")
links = pf[["ut", "fc"]].drop_duplicates().merge(p[["ut", "year", "topic", "last_region"]], on="ut")
links["last_region"] = links.last_region.fillna("Unknown")
x_funder_flow = links.groupby(["year", "topic", "fc", "last_region"]).size().rename("papers").reset_index() \
    .rename(columns={"fc": "funder_country"})

# ---- 4. WHO priorities by year x topic x group -------------------------------------------
codes = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "B1", "B2"]
rows = []
for grp, mask in [("all", p.ut.notna()), ("african_led", p.african_led == 1),
                  ("us_defence", p.us_defence_funded == 1)]:
    s = p[mask]
    g = s.groupby(["year", "topic"])[codes].sum()
    g["papers"] = s.groupby(["year", "topic"]).size()
    g = g.reset_index().melt(id_vars=["year", "topic", "papers"], var_name="code", value_name="tagged")
    g["group"] = grp
    rows.append(g)
x_who = pd.concat(rows, ignore_index=True)[["year", "topic", "group", "code", "papers", "tagged"]]

# ---- write --------------------------------------------------------------------------------
tables = {"papers_by_year_topic": x_papers, "gender_by_year": x_gender_year,
          "gender_by_topic": x_gender_topic, "funder_flow": x_funder_flow, "who_priorities": x_who}
for name, df in tables.items():
    df.to_csv(OUT / f"{name}.csv", index=False)

who_labels = who.drop_duplicates("code").set_index("code")["label"].to_dict() if "label" in who else {}
meta = {"topics": labels[["topic", "label", "who_link"]].to_dict("records"),
        "who_labels": who_labels, "min_cell": MIN_CELL,
        "benchmarks": {"first_african": 49.8, "last_african": 41.3,
                       "source": "Mbaye et al. 2019, infectious-disease research in Africa"}}
bundle = {k: json.loads(v.to_json(orient="records")) for k, v in tables.items()}
bundle["meta"] = meta
(OUT / "explorer_data.json").write_text(json.dumps(bundle, separators=(",", ":")))

# ---- self-check against the findings sheet --------------------------------------------------
L = x_gender_year[x_gender_year.position == "Last"]
print("last authors n:", int(L.women.sum() + L.men.sum()), "women %:", round(100 * L.women.sum() / (L.women.sum() + L.men.sum()), 1))
print("about Africa:", x_papers.aa.sum(), "first local %:", round(100 * x_papers.aa_first_local.sum() / x_papers.aa.sum(), 1))
print("funded:", x_papers.funded.sum(), "US %:", round(100 * x_papers.us_funded.sum() / x_papers.funded.sum(), 1))
w = x_who[x_who.group == "all"].groupby("code")[["tagged", "papers"]].sum()
print("WHO P7-P10 %:", (100 * w.tagged / w.papers).round(1).loc[["P7", "P8", "P9", "P10"]].to_dict())
print("suppressed gender cells:", int(x_gender_year.suppressed.sum() + x_gender_topic.suppressed.sum()))
print("bytes:", (OUT / "explorer_data.json").stat().st_size)
