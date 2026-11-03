"""Step 5 - Publication figures (PNG 300 dpi + PDF) from outputs/tables."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import FIGURES, TABLES

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#a3a29c", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"  # categorical slots 1-3 (validated all-pairs)
SEQ = ["#e8f1fc", "#b9d3f5", "#7fb0ec", "#4a8ee0", "#2a78d6", "#1d5aa6", "#123d73"]
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": INK, "legend.frameon": False,
})


def out(fig, name):
    fig.savefig(FIGURES / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Fig 1: women by position and period
g = pd.read_csv(TABLES / "t04_women_by_period_position.csv")
fig, ax = plt.subplots(figsize=(5.2, 3.2))
periods = list(dict.fromkeys(g.period))
x = np.arange(len(periods))
for i, (pos, col, lab) in enumerate([("First", S1, "First author"), ("All", S3, "All authorships"),
                                     ("Last", S2, "Last author")]):
    s = g[g.position == pos].set_index("period").loc[periods]
    xx = x + (i - 1) * 0.18
    ax.errorbar(xx, s.pct, yerr=[s.pct - s.ci_lo, s.ci_hi - s.pct], fmt="o", ms=6, color=col, ecolor=col,
                elinewidth=1.6, capsize=0, label=lab, mec="white", mew=1)
    ax.plot(xx, s.pct, color=col, lw=1.2, alpha=0.6)
    ax.annotate(f"{s.pct.iloc[-1]:.0f}%", (xx[-1], s.pct.iloc[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", color=INK2, fontsize=8)
ax.axhline(50, color=MUTED, lw=0.8, ls=(0, (3, 3)))
ax.text(x[0] - 0.4, 51, "parity", color=INK2, fontsize=7.5)
ax.set_xticks(x, periods); ax.set_xlim(-0.5, len(periods) - 0.3); ax.set_ylim(0, 60)
ax.set_ylabel("Women (% of classified authors)")
ax.set_title("Women hold 4 in 10 first-author but 2 in 10 last-author positions", loc="left")
ax.legend(loc="lower left", ncol=3, fontsize=8, bbox_to_anchor=(0, -0.32))
out(fig, "fig1_women_by_position_period")

# ---------------------------------------------------------------- Fig 2: local / African leadership vs benchmark
l = pd.read_csv(TABLES / "t08_local_african_leadership.csv")
order = ["First author African", "Last author African", "First author from a study country",
         "Last author from a study country"]
l = l.set_index("measure").loc[order[::-1]]
fig, ax = plt.subplots(figsize=(5.4, 2.8))
y = np.arange(len(l))
ax.barh(y, l.pct, height=0.5, color=S1, edgecolor="white")
ax.errorbar(l.pct, y, xerr=[l.pct - l.ci_lo, l.ci_hi - l.pct], fmt="none", ecolor=INK2, elinewidth=1, capsize=2)
for yi, (m, r) in zip(y, l.iterrows()):
    ax.text(1.5, yi, f"{r.pct:.0f}%", va="center", color="white", fontsize=8, fontweight="bold")
    if not np.isnan(r.benchmark_mbaye_2019):
        ax.plot([r.benchmark_mbaye_2019] * 2, [yi - 0.32, yi + 0.32], color=S2, lw=2.2)
ax.plot([], [], color=S2, lw=2.2, label="Benchmark: infectious-disease research in Africa (Mbaye et al. 2019)")
ax.set_yticks(y, [m.replace(" from a study country", " from the country studied") for m in l.index])
ax.set_xlim(0, 75); ax.set_xlabel(f"% of {int(l.n.iloc[0])} papers about an African country (95% CI)")
ax.set_title("Few papers about African countries are led from those countries", loc="left")
ax.legend(loc="lower left", bbox_to_anchor=(-0.45, -0.42), fontsize=7.5)
ax.grid(axis="y", visible=False)
out(fig, "fig2_local_african_leadership")

# ---------------------------------------------------------------- Fig 3: funder country -> last-author region
f = pd.read_csv(TABLES / "t13_funder_country_to_last_author_region.csv")
regs = ["North America", "Europe & Central Asia", "East Asia & Pacific", "Sub-Saharan Africa",
        "Latin America & Caribbean", "Middle East & North Africa", "South Asia"]
f["last_author_region"] = f.last_author_region.where(f.last_author_region.isin(regs), "Other / unknown")
cols = regs[:4] + ["Other / unknown"]
f.loc[~f.last_author_region.isin(cols), "last_author_region"] = "Other / unknown"
m = f.pivot_table(index="funder_country", columns="last_author_region", values="papers", aggfunc="sum").fillna(0)
m = m.reindex(columns=cols).fillna(0)
m = m.loc[m.sum(axis=1).sort_values(ascending=False).index]
pct = m.div(m.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(5.8, 3.4))
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("seq", SEQ)
ax.imshow(pct.values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
for i in range(pct.shape[0]):
    for j in range(pct.shape[1]):
        v = pct.values[i, j]
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 55 else INK)
ax.set_xticks(range(len(cols)), [c.replace(" & ", " &\n").replace(" / ", " /\n") for c in cols], fontsize=8)
ax.set_yticks(range(len(pct)), [f"{c} (n={int(n)})" for c, n in zip(pct.index, m.sum(axis=1))], fontsize=8)
ax.grid(False); ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Each funder country mostly funds its own region's last authors\n(% of each funder country's papers, by region of the last author)",
             loc="left", fontsize=9.5)
out(fig, "fig3_funder_country_to_last_author")

# ---------------------------------------------------------------- Fig 4: WHO priorities coverage
w = pd.read_csv(TABLES / "t18_who_priorities_coverage.csv")
w["is_who"] = w.code.str.startswith("P")
w = w.sort_values("pct")
fig, ax = plt.subplots(figsize=(5.8, 3.8))
y = np.arange(len(w))
ax.barh(y, w.pct, height=0.6, color=[S1 if t else MUTED for t in w.is_who], edgecolor="white")
for yi, (_, r) in zip(y, w.iterrows()):
    ax.text(r.pct + 1, yi, f"{r.pct:.0f}%", va="center", fontsize=8, color=INK2)
ax.set_yticks(y, [f"{r.code.replace('B1', '–').replace('B2', '–')}  {r.label.replace(' (not a WHO priority)', '')}" for _, r in w.iterrows()], fontsize=8)
ax.set_xlim(0, 72); ax.set_xlabel("% of papers mentioning the theme (one paper can match several)")
ax.grid(axis="y", visible=False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=S1, label="WHO 2025 Marburg research priority (P1–P10)"),
                   Patch(color=MUTED, label="Not a WHO priority")], loc="lower right", fontsize=7.5)
ax.set_title("Clinical care, trials, social science and capacity are each\nin fewer than 1 in 12 papers", loc="left")
out(fig, "fig4_who_priorities")

# ---------------------------------------------------------------- Fig 5: funding-acknowledgement artefact
a = pd.read_csv(TABLES / "t01_funding_ack_by_period.csv")
fig, ax = plt.subplots(figsize=(5.0, 2.8))
x = np.arange(len(a))
ax.bar(x, a.pct_funded, width=0.62, color=[MUTED if i < 3 else S1 for i in range(len(a))], edgecolor="white")
for xi, (_, r) in zip(x, a.iterrows()):
    ax.text(xi, r.pct_funded + 2, f"{r.pct_funded:.0f}%", ha="center", fontsize=8, color=INK2)
ax.set_xticks(x, [f"{b}\n(n={n})" for b, n in zip(a.band, a["size"])], fontsize=7.5)
ax.axvline(2.5, color=INK2, lw=0.8, ls=(0, (3, 3)))
ax.text(2.4, 62, "WoS indexes funding\ntext from 2008", fontsize=7.5, color=INK2, va="top", ha="right")
ax.set_ylim(0, 100); ax.set_ylabel("Papers with a funding\nacknowledgement (%)")
ax.set_title("'Unfunded' papers are mostly old papers", loc="left")
ax.grid(axis="x", visible=False)
out(fig, "fig5_funding_ack_artefact")

# ---------------------------------------------------------------- Fig 6: funding effect on citations, naive vs adjusted
c = pd.read_csv(TABLES / "t14_citations_funding_models.csv")
kn = pd.read_csv(TABLES / "key_numbers.csv").set_index("key")["value"]
fig, ax = plt.subplots(figsize=(5.2, 2.4))
labels = ["All years, raw means\n(original draft)", "2008–2023, no controls", "2008–2023, + year",
          "2008–2023, + year, OA, team,\ntopic, document type"]
ratio0 = float(kn["naive_cites_funded_all_years"]) / float(kn["naive_cites_unfunded_all_years"])
vals = [(ratio0, np.nan, np.nan)] + list(zip(c.IRR_funded, c.lo, c.hi))
y = np.arange(len(vals))[::-1]
for yi, (v, lo, hi) in zip(y, vals):
    col = S2 if yi == y[0] else S1
    if not np.isnan(lo):
        ax.plot([lo, hi], [yi, yi], color=col, lw=1.6)
    ax.plot(v, yi, "o", color=col, ms=7, mec="white", mew=1)
    ax.text(max(v, hi if not np.isnan(hi) else v) + 0.04, yi, f"{v:.2f}", va="center", fontsize=8, color=INK2)
ax.axvline(1, color=INK2, lw=0.8)
ax.set_yticks(y, labels, fontsize=7.5); ax.set_xlim(0.5, 1.9)
ax.set_xlabel("Citations of funded ÷ unfunded papers (rate ratio, 95% CI)")
ax.set_title("The 'funded papers are less cited' result disappears", loc="left")
ax.grid(axis="y", visible=False)
out(fig, "fig6_funding_citations_models")
print(sorted(p.name for p in FIGURES.glob("*.png")))
