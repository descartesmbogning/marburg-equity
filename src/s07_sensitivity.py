"""Step 7 - Sensitivity analyses for gender inference.

S1: keep only Gender-API assignments with accuracy >= 80%
S2: exclude authors based in East Asia & Pacific (where name-based inference is least accurate)
S3: count unclassified authors as women (upper bound) and as men (lower bound)
"""
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from common import PROCESSED, REFERENCE, save

au = pd.read_csv(PROCESSED / "authorships.csv")
wb = pd.read_csv(REFERENCE / "country_wb_fy2023.csv").set_index("country")
au["region"] = au["countries"].fillna("").str.split("|").str[0].map(wb["wb_region"])


def share(df, label):
    rows = []
    for pos, s in [("All", df), ("First", df[df.is_first == 1]), ("Last", df[df.is_last == 1])]:
        k, n = (s.gender == "female").sum(), s.gender.isin(["female", "male"]).sum()
        lo, hi = proportion_confint(k, n, method="wilson")
        rows.append({"analysis": label, "position": pos, "n": int(n), "pct_women": round(100 * k / n, 1),
                     "ci_lo": round(100 * lo, 1), "ci_hi": round(100 * hi, 1)})
    return rows


rows = share(au, "Main analysis")
rows += share(au[(au.gender == "unclassified") | (au.ga_accuracy >= 80)], "Gender-API accuracy >= 80%")
rows += share(au[au.region != "East Asia & Pacific"], "Excluding East Asia & Pacific authors")
up = au.copy(); up.loc[up.gender == "unclassified", "gender"] = "female"
rows += share(up, "Unclassified counted as women (upper bound)")
lo_ = au.copy(); lo_.loc[lo_.gender == "unclassified", "gender"] = "male"
rows += share(lo_, "Unclassified counted as men (lower bound)")
out = pd.DataFrame(rows)
save(out, "t19_gender_sensitivity")
print(out.to_string(index=False))
print("share with accuracy >= 80 among classified:",
      round((au.loc[au.gender != "unclassified", "ga_accuracy"] >= 80).mean() * 100, 1))
