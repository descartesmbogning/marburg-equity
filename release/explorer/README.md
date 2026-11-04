# Marburg Research Explorer

Live at https://cognosx.ca/dashboards/marburg-equity.html

Interactive page: headline + 4 KPI tiles, filters (year range, topic), 5 linked views
(gender over time, gender by topic, local African leadership, funder heatmap, WHO priorities
with group toggle), how-to-read note, CSV downloads, citation box.

## Files
- `index.html` — standalone page (Plotly 4.1.1 from cdn.plot.ly, Inter / IBM Plex Mono from Google Fonts; data inlined).
- `quarto/marburg-explorer.qmd` + `_explorer_head.html` + `_explorer_body.html` — drop into the cognosx.ca Quarto site.
- `data/*.csv`, `data/explorer_data.json` — aggregate counts only (made by `src/s08_explorer_data.py`).
- `src/template.html`, `build.py` — edit the template, then `python build.py` (needs `brand/` logos).

## Privacy rules built in
- Gender is shown by year or by topic, never year x topic; cells < 10 classified authors suppressed (none at present).
- 2023 (Jan–Feb, 3 papers) merged into "2022–23".
- Shares are hidden when fewer than 10 papers match the filters.

## Updating
- Website page: `python build.py --site /path/to/cognosx.ca` writes `dashboards/marburg-equity.qmd` and its data files.
- When the preprint and Zenodo DOIs exist, replace the "coming soon" text in the citation box of `src/template.html`, then rebuild.
