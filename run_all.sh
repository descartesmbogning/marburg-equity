#!/usr/bin/env bash
# Rebuild every table and figure from the raw Web of Science export.
# Needs data/raw/woscc_bon_23_02_verif_on_wos.xls and data/raw/author_names_gender_2007.csv
set -euo pipefail
cd "$(dirname "$0")/src"
python s01_build_corpus.py
python s02_enrich.py
python s03_topics.py
python s04_analysis.py
python s05_figures.py
python s06_export_public.py
python s07_sensitivity.py
echo "Done. See outputs/tables and outputs/figures."
