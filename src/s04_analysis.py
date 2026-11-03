"""Step 4 - All corrected analyses for the merged equity paper.

Every number used in the manuscript is written to outputs/tables/*.csv and
collected in outputs/tables/key_numbers.csv.
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

from common import PROCESSED, REFERENCE, TABLES, WOS_FILE, save

warnings.filterwarnings("ignore")
p = pd.read_csv(PROCESSED / "papers_enriched.csv")
au = pd.read_csv(PROCESSED / "authorships.csv")
tp = pd.read_csv(PROCESSED / "paper_topics.csv")[["ut", "topic"]]
pf = pd.read_csv(PROCESSED / "paper_funders.csv")
labels = pd.read_csv(REFERENCE / "topic_labels.csv").set_index("topic")["label"]
wb = pd.read_csv(REFERENCE / "country_wb_fy2023.csv").set_index("country")
code = pd.read_csv(REFERENCE / "who_priorities_codebook.csv")
p = p.merge(tp, on="ut", how="left")
p["topic_label"] = p["topic"].map(labels)
p["period"] = pd.cut(p["year"], [2007, 2012, 2017, 2023], labels=["2008-2012", "2013-2017", "2018-2023"])
K = {}  # key numbers


def prop(k, n):
    lo, hi = proportion_confint(k, n, method="wilson") if n else (np.nan, np.nan)
    return {"n": int(n), "k": int(k), "pct": round(100 * k / n, 1) if n else np.nan,
            "ci_lo": round(100 * lo, 1), "ci_hi": round(100 * hi, 1)}


def chi2(table):
    t = np.asarray(table)
    if t.shape == (2, 2) and (t < 5).any():
        return "Fisher", stats.fisher_exact(t)[1]
    c, pv, _, _ = stats.chi2_contingency(t)
    return "chi-square", pv


# ======================================================== 1. Corpus
full = pd.read_excel(WOS_FILE)
full["year"] = full["Publication Year"]
K["records_total"] = len(full)
K["papers_window"] = len(p)
K["authorships"] = len(au)
K["papers_2023_partial"] = int((p.year == 2023).sum())
K["funded_pct_window"] = round(100 * p.funded.mean(), 1)
K["oa_pct_window"] = round(100 * p.oa.mean(), 1)
K["reviews_pct"] = round(100 * p.review.mean(), 1)
K["mean_authors"] = round(p.n_authors.mean(), 2)
K["mean_countries"] = round(p.n_countries.mean(), 2)
K["mean_orgs"] = round(p.n_orgs.mean(), 2)
K["intl_collab_pct"] = round(100 * p.intl_collab.mean(), 1)
K["countries_total"] = len({c for s in p.countries.dropna() for c in s.split("|")})
K["us_author_pct"] = round(100 * p.us_author.mean(), 1)

# funding-acknowledgement indexing artefact (full corpus, all years)
full["funded"] = full["Funding Name Preferred"].notna()
full["band"] = pd.cut(full["year"].fillna(2022), [0, 1999, 2004, 2007, 2010, 2015, 2020, 2023],
                      labels=["<2000", "2000-04", "2005-07", "2008-10", "2011-15", "2016-20", "2021-23"])
fa = full.groupby("band", observed=True)["funded"].agg(["size", "mean"]).reset_index()
fa["pct_funded"] = (100 * fa["mean"]).round(1)
save(fa.drop(columns="mean"), "t01_funding_ack_by_period")
K["funded_pct_pre2005"] = round(100 * full.loc[full.year < 2005, "funded"].mean(), 1)

yr = p.groupby("year").agg(papers=("ut", "size"), funded_pct=("funded", "mean"), oa_pct=("oa", "mean"),
                           african_author_pct=("any_african_author", "mean")).reset_index()
for c in ("funded_pct", "oa_pct", "african_author_pct"):
    yr[c] = (100 * yr[c]).round(1)
save(yr, "t02_output_by_year")

# ======================================================== 2. Gender
cls = au[au.gender.isin(["female", "male"])]
K["authorships_classified_pct"] = round(100 * len(cls) / len(au), 1)
r = prop((cls.gender == "female").sum(), len(cls)); K["women_authorships_pct"] = r["pct"]
K["women_authorships_ci"] = f'{r["ci_lo"]}-{r["ci_hi"]}'
rows = []
for name, sub in [("All authorships", cls), ("First author", cls[cls.is_first == 1]),
                  ("Last author", cls[cls.is_last == 1]),
                  ("Middle author", cls[(cls.is_first == 0) & (cls.is_last == 0)]),
                  ("Single author", cls[(cls.n_authors == 1)])]:
    rows.append({"position": name, **prop((sub.gender == "female").sum(), len(sub))})
g1 = pd.DataFrame(rows); save(g1, "t03_women_by_position")
K["women_first_pct"] = g1.loc[1, "pct"]; K["women_last_pct"] = g1.loc[2, "pct"]
K["women_first_ci"] = f'{g1.loc[1, "ci_lo"]}-{g1.loc[1, "ci_hi"]}'
K["women_last_ci"] = f'{g1.loc[2, "ci_lo"]}-{g1.loc[2, "ci_hi"]}'

# by period and position
au2 = cls.merge(p[["ut", "period"]], on="ut")
rows = []
for per, sub in au2.groupby("period", observed=True):
    for name, s in [("All", sub), ("First", sub[sub.is_first == 1]), ("Last", sub[sub.is_last == 1])]:
        rows.append({"period": per, "position": name, **prop((s.gender == "female").sum(), len(s))})
g2 = pd.DataFrame(rows); save(g2, "t04_women_by_period_position")
for pos, col in [("first", "is_first"), ("last", "is_last")]:
    s = au2[au2[col] == 1].copy(); s["woman"] = (s.gender == "female").astype(int)
    m = smf.logit("woman ~ year", s).fit(disp=0)
    K[f"trend_women_{pos}_or_per_year"] = round(np.exp(m.params["year"]), 3)
    K[f"trend_women_{pos}_p"] = round(m.pvalues["year"], 3)

# first/last gender pairs (multi-author papers, both classified)
mp = p[(p.n_authors > 1) & p.first_gender.isin(["female", "male"]) & p.last_gender.isin(["female", "male"])].copy()
mp["pair"] = mp.first_gender.str[0].str.upper() + "-first / " + mp.last_gender.str[0].str.upper() + "-last"
pairs = mp["pair"].value_counts().rename("papers").reset_index()
pairs["pct"] = (100 * pairs.papers / pairs.papers.sum()).round(1)
save(pairs, "t05_first_last_gender_pairs")
ct = pd.crosstab(mp.last_gender, mp.first_gender)
test, pv = chi2(ct.values)
K["pairs_n"] = len(mp)
K["women_first_when_last_woman_pct"] = round(100 * ct.loc["female", "female"] / ct.loc["female"].sum(), 1)
K["women_first_when_last_man_pct"] = round(100 * ct.loc["male", "female"] / ct.loc["male"].sum(), 1)
K["pairs_test"] = test; K["pairs_p"] = float(f"{pv:.3g}")

# women by region and income of the author's (first listed) country
au2["country"] = au2["countries"].fillna("").str.split("|").str[0]
au2["region"] = au2["country"].map(wb["wb_region"]); au2["income"] = au2["country"].map(wb["wb_income"])
for dim in ("region", "income"):
    rows = []
    for v, s in au2.dropna(subset=[dim]).groupby(dim):
        rows.append({dim: v, "all_" + "pct": prop((s.gender == "female").sum(), len(s))["pct"], "all_n": len(s),
                     "first_pct": prop(((s.is_first == 1) & (s.gender == "female")).sum(), (s.is_first == 1).sum())["pct"],
                     "first_n": int((s.is_first == 1).sum()),
                     "last_pct": prop(((s.is_last == 1) & (s.gender == "female")).sum(), (s.is_last == 1).sum())["pct"],
                     "last_n": int((s.is_last == 1).sum())})
    save(pd.DataFrame(rows).sort_values("all_n", ascending=False), f"t06_women_by_{dim}")

# adjusted models: woman first / last author
pm = p.copy()
pm["log_auth"] = np.log(pm.n_authors)
for pos in ("first", "last"):
    s = pm[pm[f"{pos}_gender"].isin(["female", "male"])].copy()
    s["woman"] = (s[f"{pos}_gender"] == "female").astype(int)
    s["reg"] = s[f"{pos}_region"].replace({"Latin America & Caribbean": "Other", "South Asia": "Other",
                                           "Middle East & North Africa": "Other"}).fillna("Other")
    s["reg"] = pd.Categorical(s["reg"], categories=["North America", "Europe & Central Asia", "East Asia & Pacific",
                                                    "Sub-Saharan Africa", "Other"])
    s["topic_c"] = s["topic_label"].astype("category")
    m = smf.logit("woman ~ year + reg + log_auth + review + C(topic_c)", s).fit(disp=0, maxiter=200)
    out = pd.DataFrame({"OR": np.exp(m.params), "lo": np.exp(m.conf_int()[0]), "hi": np.exp(m.conf_int()[1]),
                        "p": m.pvalues}).round(3)
    save(out, f"t07_logit_woman_{pos}_author", index=True)

# ======================================================== 3. Local and African leadership
K["papers_any_african_pct"] = round(100 * p.any_african_author.mean(), 1)
K["papers_first_african_pct"] = round(100 * p.first_african.mean(), 1)
K["papers_last_african_pct"] = round(100 * p.last_african.mean(), 1)
af = p[p.about_africa == 1]
K["papers_about_africa"] = len(af)
rows = []
for lab, col in [("Any author from a study country", "any_local_author"), ("First author from a study country", "first_local"),
                 ("Last author from a study country", "last_local"), ("Any African author", "any_african_author"),
                 ("First author African", "first_african"), ("Last author African", "last_african")]:
    s = af[col].dropna()
    rows.append({"measure": lab, **prop(s.sum(), len(s))})
loc = pd.DataFrame(rows)
loc["benchmark_mbaye_2019"] = [93.2 if "Any African" in m else 49.8 if "First author African" in m
                               else 41.3 if "Last author African" in m else np.nan for m in loc.measure]
save(loc, "t08_local_african_leadership")
for _, r in loc.iterrows():
    K["africa_" + r.measure.lower().replace(" ", "_")] = r.pct
# sensitivity: study country named in the title
tit = pd.read_excel(WOS_FILE).set_index("UT (Unique WOS ID)")["Article Title"].str.lower()
af_t = af[af.apply(lambda r: any(c.lower().split()[0] in str(tit.get(r.ut, "")) for c in r.study_countries.split("|")), axis=1)]
rows = [{"measure": lab, **prop(af_t[col].sum(), af_t[col].notna().sum())}
        for lab, col in [("Any local", "any_local_author"), ("First local", "first_local"), ("Last local", "last_local"),
                         ("First African", "first_african"), ("Last African", "last_african")]]
save(pd.DataFrame(rows), "t09_leadership_country_in_title")
K["papers_country_in_title"] = len(af_t)
# by period
rows = []
for per, s in af.groupby("period", observed=True):
    for lab, col in [("First African", "first_african"), ("Last African", "last_african"), ("Any local", "any_local_author")]:
        rows.append({"period": per, "measure": lab, **prop(s[col].sum(), s[col].notna().sum())})
save(pd.DataFrame(rows), "t10_african_leadership_by_period")
# African women in lead positions (whole corpus)
K["african_women_first_n"] = int(((p.first_african == 1) & (p.first_gender == "female")).sum())
K["african_women_last_n"] = int(((p.last_african == 1) & (p.last_gender == "female")).sum())
K["african_first_n"] = int((p.first_african == 1).sum()); K["african_last_n"] = int((p.last_african == 1).sum())

# ======================================================== 4. Funders
fund = p[p.funded == 1]
fg = pf.groupby(["funder_group", "funder_country", "funder_type"])["ut"].nunique().rename("papers").reset_index()
fg["pct_of_funded"] = (100 * fg.papers / len(fund)).round(1)
save(fg.sort_values("papers", ascending=False), "t11_funder_groups")
fc = pf.groupby("funder_country")["ut"].nunique().rename("papers").reset_index()
fc["pct_of_funded"] = (100 * fc.papers / len(fund)).round(1)
save(fc.sort_values("papers", ascending=False), "t12_funder_countries")
K["funded_papers"] = len(fund)
K["us_funded_pct_of_funded"] = round(100 * fund.us_funded.mean(), 1)
K["us_defence_pct_of_funded"] = round(100 * fund.us_defence_funded.mean(), 1)
K["african_funder_pct_of_funded"] = round(100 * fund.african_funded.mean(), 1)
K["nih_pct_of_funded"] = round(100 * fund.ut.isin(pf.loc[pf.funder_group.str.startswith("US NIH"), "ut"]).mean(), 1)
K["industry_pct_of_funded"] = round(100 * fund.ut.isin(pf.loc[pf.funder_type == "Industry", "ut"]).mean(), 1)

# funder country -> last-author region
top_fc = ["United States", "Japan", "Germany", "Canada", "China", "European Union", "United Kingdom", "Africa"]
rows = []
for c in top_fc:
    uts = set(pf.loc[pf.funder_country == c, "ut"])
    s = p[p.ut.isin(uts)]
    for reg, n in s["last_region"].fillna("Unknown").value_counts().items():
        rows.append({"funder_country": c, "last_author_region": reg, "papers": n})
flow = pd.DataFrame(rows); save(flow, "t13_funder_country_to_last_author_region")
# who funds African-led work?
al = p[(p.last_african == 1) | (p.first_african == 1)]
K["african_led_papers"] = len(al)
K["african_led_funded_pct"] = round(100 * al.funded.mean(), 1)
K["african_led_african_funder_pct"] = round(100 * al.african_funded.mean(), 1)
K["african_led_us_funder_pct"] = round(100 * al.us_funded.mean(), 1)

# ======================================================== 5. Citations and open access: naive vs adjusted
naive_full = full.copy()
naive_full["cites"] = naive_full["Times Cited, All Databases"]
nf = naive_full.groupby("funded")["cites"].mean()
K["naive_cites_funded_all_years"] = round(nf[True], 1); K["naive_cites_unfunded_all_years"] = round(nf[False], 1)
K["naive_mw_p_all_years"] = float(f'{stats.mannwhitneyu(naive_full.loc[naive_full.funded, "cites"], naive_full.loc[~naive_full.funded, "cites"])[1]:.3g}')
w = p.groupby("funded")["cites_norm"].mean()
K["norm_cites_funded"] = round(w[1], 2); K["norm_cites_unfunded"] = round(w[0], 2)

pm["log_cites_norm"] = np.log1p(pm.cites_norm)
pm["log_orgs"] = np.log(pm.n_orgs.fillna(1))
pm["topic_c"] = pm["topic_label"].astype("category")
models = {
    "M1 naive (raw citations, no controls)": "cites_wos ~ funded",
    "M2 + year": "cites_wos ~ funded + C(year)",
    "M3 full": "cites_wos ~ funded + oa + log_auth + intl_collab + review + C(year) + C(topic_c)",
}
rows = []
for name, f in models.items():
    m = smf.negativebinomial(f, pm).fit(disp=0, maxiter=300)
    ci = m.conf_int().loc["funded"]
    rows.append({"model": name, "n": int(m.nobs), "IRR_funded": round(np.exp(m.params["funded"]), 2),
                 "lo": round(np.exp(ci[0]), 2), "hi": round(np.exp(ci[1]), 2), "p": float(f'{m.pvalues["funded"]:.3g}'),
                 "IRR_oa": round(np.exp(m.params["oa"]), 2) if "oa" in m.params else np.nan})
cit = pd.DataFrame(rows); save(cit, "t14_citations_funding_models")
K["irr_funded_full"] = cit.iloc[-1]["IRR_funded"]; K["irr_funded_full_ci"] = f'{cit.iloc[-1]["lo"]}-{cit.iloc[-1]["hi"]}'
K["irr_funded_full_p"] = cit.iloc[-1]["p"]; K["irr_oa_full"] = cit.iloc[-1]["IRR_oa"]

# gender pair and citations (adjusted)
mp2 = pm.merge(mp[["ut", "pair"]], on="ut")
m = smf.negativebinomial("cites_wos ~ C(pair, Treatment('M-first / M-last')) + funded + oa + log_auth + review + C(year)",
                         mp2).fit(disp=0, maxiter=300)
gp = pd.DataFrame({"IRR": np.exp(m.params), "lo": np.exp(m.conf_int()[0]), "hi": np.exp(m.conf_int()[1]),
                   "p": m.pvalues}).round(3)
save(gp[gp.index.str.startswith("C(pair")], "t15_citations_gender_pair", index=True)

# open access
rows = []
for name, f in [("naive", "oa ~ funded"), ("adjusted", "oa ~ funded + log_auth + review + C(year) + C(topic_c)")]:
    m = smf.logit(f, pm).fit(disp=0, maxiter=200)
    ci = m.conf_int().loc["funded"]
    rows.append({"model": name, "OR_funded": round(np.exp(m.params["funded"]), 2), "lo": round(np.exp(ci[0]), 2),
                 "hi": round(np.exp(ci[1]), 2), "p": float(f'{m.pvalues["funded"]:.3g}')})
save(pd.DataFrame(rows), "t16_open_access_models")
K["oa_or_funded_adj"] = rows[1]["OR_funded"]; K["oa_or_funded_adj_ci"] = f'{rows[1]["lo"]}-{rows[1]["hi"]}'

# ======================================================== 6. Topics and WHO priorities
tt = p.groupby("topic_label").agg(papers=("ut", "size"), women_first=("first_gender", lambda s: (s == "female").mean()),
                                  women_last=("last_gender", lambda s: (s == "female").mean()),
                                  african_any=("any_african_author", "mean"), funded=("funded", "mean"),
                                  us_defence=("us_defence_funded", "mean")).reset_index()
for c in tt.columns[2:]:
    tt[c] = (100 * tt[c]).round(1)
save(tt.sort_values("papers", ascending=False), "t17_topics_profile")

rows = []
for _, r in code.iterrows():
    c = r["code"]
    rows.append({"code": c, "label": r["label"], **prop(p[c].sum(), len(p)),
                 "pct_2008_2015": round(100 * p.loc[p.year <= 2015, c].mean(), 1),
                 "pct_2016_2023": round(100 * p.loc[p.year >= 2016, c].mean(), 1),
                 "pct_african_led": round(100 * al[c].mean(), 1),
                 "pct_us_defence_funded": round(100 * p.loc[p.us_defence_funded == 1, c].mean(), 1)})
pri = pd.DataFrame(rows); save(pri, "t18_who_priorities_coverage")
for _, r in pri.iterrows():
    K[f"who_{r.code}_pct"] = r.pct

# ======================================================== 7. Output around outbreaks
outbreaks = {2005: "Angola", 2007: "Uganda", 2008: "Uganda (travellers)", 2012: "Uganda", 2014: "Uganda",
             2017: "Uganda", 2021: "Guinea", 2022: "Ghana"}
yr["outbreak"] = yr["year"].map(outbreaks)
save(yr, "t02_output_by_year")

kn = pd.DataFrame([{"key": k, "value": v} for k, v in K.items()])
save(kn, "key_numbers")
print(kn.to_string(index=False))
