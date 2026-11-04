"""Build the explorer: inlines aggregate data, findings sheet and logos into one HTML file,
and writes Quarto include files for cognosx.ca.
Usage: python build.py [--plotly URL]"""
import base64, json, sys
from pathlib import Path

HERE = Path(__file__).parent
BRAND = Path(sys.argv[sys.argv.index("--brand") + 1]) if "--brand" in sys.argv else HERE / "brand"
PLOTLY = sys.argv[sys.argv.index("--plotly") + 1] if "--plotly" in sys.argv else "https://cdn.plot.ly/plotly-4.1.1.min.js"
OUTNAME = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "index.html"
b64 = lambda p: base64.b64encode(p.read_bytes()).decode()

html = (HERE / "src" / "template.html").read_text()
data = (HERE / "data" / "explorer_data.json").read_text()
findings = (HERE.parent / "findings.csv").read_text()
html = (html.replace("/*__DATA__*/null", data)
            .replace('/*__FINDINGS__*/""', json.dumps(findings))
            .replace("__PLOTLY_SRC__", PLOTLY)
            .replace("__LOGO_LIGHT__", b64(BRAND / "logo-light.png"))
            .replace("__FAVICON__", b64(BRAND / "favicon.png")))
(HERE / OUTNAME).write_text(html)

if OUTNAME == "index.html":
    q = HERE / "quarto"; q.mkdir(exist_ok=True)
    cut = lambda a, b: html.split(a)[1].split(b)[0]
    (q / "_explorer_head.html").write_text(cut("<!--HEAD_START-->", "<!--HEAD_END-->"))
    (q / "_explorer_body.html").write_text(cut("<!--BODY_START-->", "<!--BODY_END-->"))
    (q / "marburg-explorer.qmd").write_text("""---
title: "Marburg Research Explorer"
description: "Who leads Marburg virus research, 2008–2023: gender, geography, funding and WHO priorities."
page-layout: custom
toc: false
title-block-banner: false
format:
  html:
    include-in-header: _explorer_head.html
    include-after-body: _explorer_body.html
---
""")
# ---- cognosx.ca page (dashboards/marburg-equity.qmd); data fetched from dashboards/files/marburg-equity/
if "--site" in sys.argv:
    site = Path(sys.argv[sys.argv.index("--site") + 1])
    src = (HERE / "src" / "template.html").read_text()
    head = src.split("<!--HEAD_START-->")[1].split("<!--HEAD_END-->")[0].replace("__PLOTLY_SRC__", PLOTLY)
    body = src.split("<!--BODY_START-->")[1].split("<!--BODY_END-->")[0]
    head = head.replace(".cx .x-bar{position:sticky;top:0;", ".cx .x-bar{position:static;")
    head = head.replace(".cx .x-hero{background:var(--black);color:#fff;padding:40px 0 36px}",
                        ".cx .x-hero{background:var(--black);color:#fff;padding:34px 0 32px;border-radius:var(--r);margin-top:12px}")
    body = body.replace('      <img class="x-logo" src="data:image/png;base64,__LOGO_LIGHT__" alt="CognosX">\n', "")
    body = body.split("  <footer>")[0] + "</div>\n" + body.split("</footer>\n</div>")[1]
    body = body.replace("<main class=\"x-wrap\">", "<div class=\"x-wrap cx-main\" style=\"padding:28px 0 8px\">").replace("  </main>", "  </div>")
    body = body.replace('(function(){\nconst D = /*__DATA__*/null;\nconst FINDINGS_CSV = /*__FINDINGS__*/"";',
        "Promise.all([fetch('files/marburg-equity/explorer_data.json').then(r=>r.json()),"
        "fetch('files/marburg-equity/findings.csv').then(r=>r.text())]).then(([D,FINDINGS_CSV])=>{")
    body = body.replace("fillControls(); downloads(); render();", "fillControls(); downloads(); render();", 1)
    assert body.rstrip().endswith("})();\n</script>") or "})();\n</script>" in body
    body = body.replace("})();\n</script>", "});\n</script>")
    head = "\n".join(l for l in head.splitlines() if "fonts.g" not in l).replace("<style>", "<style>\n#title-block-header{display:none}")  # site already loads Inter / IBM Plex Mono
    fm = """---
title: "Who leads Marburg virus research?"
description: "Explore gender, local leadership, funding and WHO research priorities in 684 Marburg virus papers, 2008–2023."
date: "2026-11-03"
categories: [Dashboard, Explorer, Research equity]
projects: ["research-in-africa"]
page-layout: full
title-block-style: none
---

```{=html}
"""
    (site / "dashboards" / "marburg-equity.qmd").write_text(fm + head.strip() + "\n" + body.strip() + "\n```\n")
    d = site / "dashboards" / "files" / "marburg-equity"; d.mkdir(parents=True, exist_ok=True)
    (d / "explorer_data.json").write_text(data)
    (d / "findings.csv").write_text(findings)
    print("site page written")
print("built", OUTNAME, len(html) // 1024, "KB")
