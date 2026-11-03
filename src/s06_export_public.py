"""Step 6 - Export a public, de-identified paper-level dataset.

Web of Science records cannot be redistributed, so we share WoS accession numbers
(UT), DOIs and derived variables only. Inferred gender of named individuals is not
shared at paper level; gender results are shared as aggregate tables in outputs/.
"""
import pandas as pd

from common import PROCESSED, ROOT

p = pd.read_csv(PROCESSED / "papers_enriched.csv")
t = pd.read_csv(PROCESSED / "paper_topics.csv")[["ut", "topic", "topic_weight"]]
drop = ["first_gender", "last_gender", "n_women", "n_men", "n_unclass", "share_women", "oa_types"]
pub = p.drop(columns=[c for c in drop if c in p.columns]).merge(t, on="ut", how="left")
out = ROOT / "data" / "public"
out.mkdir(exist_ok=True)
pub.to_csv(out / "marburg_papers_2008_2023_public.csv", index=False)
pd.read_csv(PROCESSED / "paper_funders.csv").to_csv(out / "marburg_paper_funders.csv", index=False)
print(pub.shape, list(pub.columns))
