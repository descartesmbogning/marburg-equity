"""Step 3 - Topic model (LDA) on titles + abstracts + author keywords.

Fixes the old pipeline: missing abstracts are no longer turned into the word "nan";
the number of topics is chosen with c_v coherence instead of being fixed at 10.

Output: outputs/tables/topic_model_selection.csv  coherence by k
        outputs/tables/topic_top_words.csv         top 15 words per topic
        data/processed/paper_topics.csv            dominant topic + weights per paper
"""
import re

import numpy as np
import pandas as pd
from gensim.corpora import Dictionary
from gensim.models.coherencemodel import CoherenceModel
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

from common import PROCESSED, TABLES, WOS_FILE

p = pd.read_csv(PROCESSED / "papers.csv")
wos = pd.read_excel(WOS_FILE).rename(columns={"UT (Unique WOS ID)": "ut"}).set_index("ut").loc[p["ut"]]

DOMAIN_STOP = {
    "marburg", "marv", "virus", "viruses", "viral", "study", "studies", "results", "result", "using", "used",
    "use", "based", "showed", "shown", "show", "also", "may", "can", "however", "including", "new", "two",
    "one", "well", "found", "data", "high", "different", "important", "reported", "observed", "elsevier",
    "rights", "reserved", "copyright", "ltd", "authors", "author", "published", "article", "paper", "review",
    "present", "provide", "suggest", "role", "potential", "within", "among", "et", "al", "inc",
}
STOP = list(ENGLISH_STOP_WORDS | DOMAIN_STOP)


def clean(s):
    s = re.sub(r"\(c\)\s*\d{4}.*$", " ", str(s).lower())  # drop copyright tails
    s = re.sub(r"[^a-z\- ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


docs = (wos["Article Title"].fillna("") + " " + wos["Abstract"].fillna("") + " "
        + wos["Author Keywords"].fillna("").str.replace(";", " ")).map(clean)
assert not docs.str.contains(r"\bnan\b").any(), "missing values leaked into the text"

vec = CountVectorizer(stop_words=STOP, min_df=5, max_df=0.5, token_pattern=r"(?u)\b[a-z][a-z\-]{2,}\b",
                      ngram_range=(1, 1))
X = vec.fit_transform(docs)
vocab = np.array(vec.get_feature_names_out())
tokens = [[w for w in d.split() if w in set(vocab)] for d in docs]
dic = Dictionary(tokens)

rows, models = [], {}
for k in range(6, 15):
    lda = LatentDirichletAllocation(n_components=k, learning_method="batch", max_iter=100,
                                    random_state=42, doc_topic_prior=0.1, topic_word_prior=0.01)
    lda.fit(X)
    top = [list(vocab[np.argsort(c)[::-1][:12]]) for c in lda.components_]
    cv = CoherenceModel(topics=top, texts=tokens, dictionary=dic, coherence="c_v").get_coherence()
    rows.append({"k": k, "coherence_cv": round(cv, 4), "perplexity": round(lda.perplexity(X), 1)})
    models[k] = lda
sel = pd.DataFrame(rows)
sel.to_csv(TABLES / "topic_model_selection.csv", index=False)
best_k = int(sel.sort_values("coherence_cv", ascending=False).iloc[0]["k"])
lda = models[best_k]

tw = pd.DataFrame([{"topic": i, "top_words": ", ".join(vocab[np.argsort(c)[::-1][:15]])}
                   for i, c in enumerate(lda.components_)])
tw.to_csv(TABLES / "topic_top_words.csv", index=False)
theta = lda.transform(X)
pt = pd.DataFrame(theta, columns=[f"t{i}" for i in range(best_k)])
pt.insert(0, "ut", p["ut"].values)
pt["topic"] = theta.argmax(axis=1)
pt["topic_weight"] = theta.max(axis=1)
pt.to_csv(PROCESSED / "paper_topics.csv", index=False)

print(sel.to_string(index=False))
print("chosen k =", best_k)
print(tw.to_string(index=False))
print(pt["topic"].value_counts().sort_index().to_dict())
