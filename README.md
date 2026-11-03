# Who leads Marburg virus research?

Code and derived data for the study **"Who leads Marburg virus research? Gender, geography and funding in authorship, 2008–2023"**.

The study looks at 684 Web of Science papers on Marburg virus published between 2008 and February 2023. It asks four questions:

1. How often are women first and last authors?
2. Are papers about African countries led by researchers from those countries?
3. Who funds the research, and does the funder's country shape who leads it?
4. How well did the research cover the [WHO 2025 Marburg research priorities](https://cdn.who.int/media/docs/default-source/blue-print/marburg-response--building-research-readiness-for-a-future-filovirus-outbreak/meeting-outcomes-top-10-priorities-for-research-to-develop-marburg-medical-countermeasures.pdf)?

The data stop just before the 2023–2025 outbreaks in Equatorial Guinea, Tanzania, Rwanda and Ethiopia, so the results serve as a **pre-outbreak baseline**.

## Main results

| Measure | Result |
|---|---|
| Women among all authors | 35.1% (95% CI 33.9–36.4) |
| Women as first author | 41.6% (37.9–45.4) |
| Women as last author | 19.6% (16.7–22.9); rising from 15.1% (2008–12) to 23.2% (2018–23) |
| Papers with any author in Africa | 14.6% |
| Papers about an African country with a first author from that country | 25.5% (102 papers) |
| Funded papers with a US funder | 69.0%; US defence funders 24.0%; African funders 3.2% |
| Funded vs unfunded citations, after adjusting for year and other factors | rate ratio 1.07 (0.87–1.33), no difference |
| Papers on WHO priorities 7–10 (clinical care, trials, social science, capacity) | 3.9–7.2% each |

Full numbers are in `outputs/tables/key_numbers.csv`.

## How to run

```bash
pip install -r requirements.txt
./run_all.sh
```

| Step | Script | What it does |
|---|---|---|
| 1 | `src/s01_build_corpus.py` | Restricts to 2008–2023, links authors to addresses, adds Gender-API results, counts unique organisations, normalises citations by year |
| 2 | `src/s02_enrich.py` | Adds World Bank region and income, harmonises funders, tags African study countries, tags WHO priority themes |
| 3 | `src/s03_topics.py` | LDA topic model; the number of topics (k = 10) is chosen by c_v coherence |
| 4 | `src/s04_analysis.py` | Proportions with Wilson 95% CIs, chi-square or Fisher tests, logistic and negative binomial regressions |
| 5 | `src/s05_figures.py` | Six figures (PNG 300 dpi + PDF) |
| 6 | `src/s06_export_public.py` | De-identified public dataset |

## Data

- **Source:** Web of Science Core Collection, exported 23 February 2023. Query: `Marburg* AND (virus* OR disease* OR hemorrhagic OR haemorrhagic OR viral* OR MARV OR fever)`. English articles, reviews and letters.
- **Not included in this repo:** the raw records, because the Web of Science licence does not allow redistribution, and the author-level gender file, because it holds personal names. Both are available from the authors on reasonable request.
- **Shared in `data/public/`:**
  - WoS accession numbers (UT), DOIs and all derived paper-level variables, so others can rebuild the corpus.
  - Inferred gender of individual authors is not shared at paper level. Gender results are shared only as the aggregate tables in `outputs/tables/`.
- **Reference tables in `data/reference/`:**
  - `country_wb_fy2023.csv`: World Bank regions and FY2023 income groups.
  - `funder_rules.csv`: the rules that group funder names.
  - `who_priorities_codebook.csv`: the dictionary used to tag WHO priority themes.
  - `topic_labels.csv`: our labels for the 10 topics.

## Methods notes and limitations

- **Gender:** inferred from first names with [Gender-API](https://gender-api.com). 96.4% of authorships were classified. Name-based inference is binary and less accurate for East Asian names, and it does not record how people identify.
- **Funding:** taken from Web of Science funding acknowledgements, which are indexed systematically only from 2008. This is why the window starts in 2008: before that, "unfunded" mostly means "not indexed" (see Figure 5).
- **Study country:** a paper is tagged with an African country when the country is named in its title, abstract or keywords. Virus and strain names (Sudan virus, Zaire ebolavirus, MARV-Angola) are removed first. A stricter version, where the country must appear in the title, is reported as a sensitivity analysis.
- **WHO priorities:** tagged with a keyword dictionary, which is transparent but approximate. A paper can match several themes.

## Licence

Code: MIT. Derived data, tables and figures: CC BY 4.0.

## Citation

Mbogning Fonkou MD, et al. *Who leads Marburg virus research? Gender, geography and funding in authorship, 2008–2023.* Preprint, 2026.
