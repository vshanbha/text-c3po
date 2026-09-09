"""Build the static docs site from repo markdown. No new dependencies committed.

Usage (run from the project root):
    uv run --with markdown --no-project python docs/build_docs.py

Regenerates every *.html in docs/ (plus keeps .gitkeep). Re-run after any
source doc changes, then commit and push: the static.yml Pages workflow
deploys docs/ on every push to master.
"""

import datetime
import os

PAGES = [
    ("README.md", "index.html", "Overview"),
    ("blueprint.md", "blueprint.html", "Blueprint"),
    (
        "_bmad-output/planning-artifacts/briefs/brief-text-c3po-2026-09-08/brief.md",
        "brief.html",
        "Product brief",
    ),
    (
        "_bmad-output/planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md",
        "prd.html",
        "PRD",
    ),
    (
        "_bmad-output/planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/DESIGN.md",
        "design.html",
        "Design",
    ),
    (
        "_bmad-output/planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md",
        "experience.html",
        "Experience",
    ),
    (
        "_bmad-output/planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md",
        "architecture.html",
        "Architecture",
    ),
    (
        "_bmad-output/planning-artifacts/research/technical-flet-sounddevice-2026-09-08/research.md",
        "research-feasibility.html",
        "Feasibility research",
    ),
    (
        "_bmad-output/planning-artifacts/research/technical-model-quality-2026-09-08/research.md",
        "research-model-quality.html",
        "Model-quality research",
    ),
    (
        "_bmad-output/specs/spec-e1-shell-core/RETROSPECTIVE.md",
        "retrospective-e1.html",
        "E1 retrospective",
    ),
]

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — text-c3po docs</title>
<style>
body{{font-family:-apple-system,system-ui,sans-serif;max-width:860px;margin:0 auto;padding:1.5rem;line-height:1.6;color:#222}}
nav{{border-bottom:1px solid #ddd;padding-bottom:.75rem;margin-bottom:1.5rem;font-size:.9rem}}
nav a{{margin-right:.9rem;text-decoration:none;color:#0b5fff}}
nav a:hover{{text-decoration:underline}}
pre{{background:#f4f4f4;padding:1rem;overflow-x:auto;border-radius:6px}}
code{{font-family:ui-monospace,monospace;font-size:.88em}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}
footer{{margin-top:2rem;border-top:1px solid #ddd;padding-top:.75rem;font-size:.8rem;color:#666}}
</style>
</head>
<body>
<nav>{nav}</nav>
<main>{body}</main>
<footer>Generated from <code>{source}</code> on {date}. text-c3po v2 docs.</footer>
</body>
</html>
"""


def main():
    import markdown

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(root, "docs")
    nav = " ".join(
        '<a href="{f}">{t}</a>'.format(f=out, t=title) for _, out, title in PAGES
    )
    date = datetime.date.today().isoformat()
    for source, out, title in PAGES:
        src = os.path.join(root, source)
        with open(src, encoding="utf-8") as handle:
            body = markdown.markdown(
                handle.read(), extensions=["fenced_code", "tables"]
            )
        page = TEMPLATE.format(
            title=title, nav=nav, body=body, source=source, date=date
        )
        with open(os.path.join(outdir, out), "w", encoding="utf-8") as handle:
            handle.write(page)
        print("wrote docs/{} from {}".format(out, source))


if __name__ == "__main__":
    main()
