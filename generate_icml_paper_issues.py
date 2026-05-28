#!/usr/bin/env python3
"""Generate ICML 2026 RL paper issue pages and update the landing page."""

from __future__ import annotations

import html
import json
import math
import re
import urllib.request
from pathlib import Path

from generate_iclr_poster_issues import ORAL_ISSUES


ROOT = Path(__file__).resolve().parent
DRAFT_DIR = ROOT / "draft"
ICML_DIR = DRAFT_DIR / "icml" / "papers"
ICML_DATA_PATH = DRAFT_DIR / "icml2026_papers.json"
ICML_INDEX_PATH = DRAFT_DIR / "icml2026_paper_drafts_index.md"
SITE_INDEX_PATH = ROOT / "index.html"
BATCH_SIZE = 50
ICML_PAPERS_URL = "https://icml.cc/static/virtual/data/icml-2026-orals-posters.json"
ICML_ABSTRACTS_URL = "https://icml.cc/static/virtual/data/icml-2026-abstracts.json"
ICLR_POSTER_DIR = DRAFT_DIR / "posters"


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def author_line(authors: list[str]) -> str:
    authors = [clean_text(author) for author in authors if clean_text(author)]
    if len(authors) <= 6:
        return ", ".join(authors)
    return ", ".join(authors[:5]) + f", et al. ({len(authors)} authors)"


def truncate(value: str, limit: int = 260) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "..."


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Policy Gradient draft generator)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def openreview_pdf_url(paper_url: str) -> str:
    match = re.search(r"openreview\.net/forum\?id=([^&#]+)", paper_url or "")
    if not match:
        return ""
    return f"https://openreview.net/pdf?id={match.group(1)}"


def external_label(url: str) -> str:
    lowered = (url or "").lower()
    if "arxiv.org" in lowered:
        return "arXiv"
    if "github.com" in lowered:
        return "Code"
    if "zenodo.org" in lowered:
        return "Data"
    return "Project"


def fetch_icml_papers() -> list[dict]:
    data = fetch_json(ICML_PAPERS_URL)
    abstracts = fetch_json(ICML_ABSTRACTS_URL)

    papers = []
    for item in data.get("results", []):
        if item.get("eventtype") != "Poster":
            continue
        topic = clean_text(item.get("topic") or "")
        if not topic.startswith("Reinforcement Learning->"):
            continue
        title = clean_text(item.get("name") or "")
        if not title:
            continue
        path = item.get("virtualsite_url") or f"/virtual/2026/poster/{item['id']}"
        paper_url = item.get("paper_url") or ""
        pdf_url = item.get("paper_pdf_url") or openreview_pdf_url(paper_url)
        external_url = item.get("url") or ""
        papers.append(
            {
                "id": str(item["id"]),
                "title": title,
                "url": "https://icml.cc" + path,
                "paper_url": paper_url,
                "authors": [
                    clean_text(author.get("fullname", ""))
                    for author in item.get("authors", [])
                    if clean_text(author.get("fullname", ""))
                ],
                "topic": topic,
                "keywords": [clean_text(keyword) for keyword in item.get("keywords", []) if clean_text(keyword)],
                "abstract": clean_text(abstracts.get(str(item["id"]), "")),
                "pdf": pdf_url,
                "external_url": external_url,
                "external_label": external_label(external_url) if external_url else "",
            }
        )

    papers.sort(key=lambda paper: paper["title"].casefold())
    return papers


def render_icml_issue(issue: int, total: int, papers: list[dict]) -> str:
    items = []
    for index, paper in enumerate(papers, start=1):
        links = [f'<a href="{esc(paper["url"])}">ICML</a>']
        if paper.get("paper_url"):
            links.append(f'<a href="{esc(paper["paper_url"])}">OpenReview</a>')
        if paper.get("pdf"):
            links.append(f'<a href="{esc(paper["pdf"])}">PDF</a>')
        if paper.get("external_url"):
            links.append(f'<a href="{esc(paper["external_url"])}">{esc(paper["external_label"])}</a>')
        items.append(
            f"""      <li>
        <span class="paper-num">{index:02d}</span>
        <div>
          <a href="{esc(paper['url'])}">{esc(paper['title'])}</a>
          <span class="authors">{esc(author_line(paper.get('authors', [])))}</span>
          <span class="abstract">{esc(truncate(paper.get('abstract', '')))}</span>
          <span class="paper-meta">{esc(paper.get('topic', ''))} · {" · ".join(links)}</span>
        </div>
      </li>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ICML 2026 RL Papers - Issue {issue:03d}</title>
  <style>
    body {{ margin: 0; background: #f3efe6; color: #1a1a1a; font-family: Georgia, "Times New Roman", Times, serif; line-height: 1.5; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 44px 24px 72px; }}
    h1 {{ font-size: 42px; line-height: 1.1; margin: 0 0 8px; font-weight: normal; }}
    h2 {{ font-size: 22px; line-height: 1.25; margin: 0 0 30px; font-weight: normal; color: #5b5b5b; }}
    a {{ color: #8a3324; text-decoration: none; border-bottom: 1px solid #8a3324; }}
    .meta {{ font-family: "Courier New", Courier, monospace; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #5b5b5b; margin-bottom: 18px; }}
    .paper-list {{ list-style: none; margin: 0; padding: 0; }}
    .paper-list li {{ border-top: 1px solid #d8d2c1; display: grid; grid-template-columns: 48px 1fr; gap: 18px; padding: 16px 0; }}
    .paper-num {{ color: #8a3324; font-family: "Courier New", Courier, monospace; font-size: 13px; letter-spacing: 1px; padding-top: 3px; }}
    .authors, .abstract, .paper-meta {{ display: block; color: #5b5b5b; font-size: 14px; margin-top: 4px; }}
    .abstract {{ color: #2f2f2f; font-size: 15px; line-height: 1.45; margin-top: 8px; }}
    .paper-meta {{ font-family: "Courier New", Courier, monospace; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; }}
    .nav {{ display: flex; justify-content: space-between; gap: 16px; margin-top: 36px; }}
    @media (max-width: 640px) {{
      h1 {{ font-size: 32px; }}
      .paper-list li {{ grid-template-columns: 1fr; gap: 6px; }}
      .nav {{ display: block; }}
      .nav a {{ display: inline-block; margin: 8px 14px 0 0; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="meta">The Policy Gradient · ICML 2026 RL Papers</div>
    <h1>ICML Paper Issue {issue:03d}</h1>
    <h2>{len(papers)} reinforcement-learning-related papers · issue {issue} of {total}</h2>
    <ol class="paper-list">
{chr(10).join(items)}
    </ol>
    <div class="nav">
      <a href="../../../index.html#icml-papers">Back to ICML paper index</a>
      {"<a href=\"icml2026_papers_issue%03d.html\">Previous issue</a>" % (issue - 1) if issue > 1 else "<span></span>"}
      {"<a href=\"icml2026_papers_issue%03d.html\">Next issue</a>" % (issue + 1) if issue < total else "<span></span>"}
    </div>
  </main>
</body>
</html>
"""


def count_iclr_posters() -> int:
    data_path = DRAFT_DIR / "iclr2026_posters.json"
    if data_path.exists():
        return len(json.loads(data_path.read_text()))
    return 0


def render_site_index(total_icml_issues: int, icml_count: int) -> str:
    oral_items = "\n".join(
        f"""        <li>
          <a href="{esc(href)}">{esc(title)}</a>
          <span class="issue-summary">{esc(summary)}</span>
        </li>"""
        for href, title, summary in ORAL_ISSUES
    )
    poster_files = sorted(ICLR_POSTER_DIR.glob("iclr2026_posters_issue*.html"))
    poster_items = "\n".join(
        f"""        <li><a href="draft/posters/{path.name}">Poster Issue {index:03d}</a></li>"""
        for index, path in enumerate(poster_files, start=1)
    )
    icml_items = "\n".join(
        f"""        <li><a href="draft/icml/papers/icml2026_papers_issue{issue:03d}.html">ICML Paper Issue {issue:03d}</a></li>"""
        for issue in range(1, total_icml_issues + 1)
    )
    poster_count = count_iclr_posters()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Policy Gradient - Conference Issues</title>
  <style>
    body {{ margin: 0; background: #f3efe6; color: #1a1a1a; font-family: Georgia, "Times New Roman", Times, serif; line-height: 1.55; }}
    .page {{ display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 48px; max-width: 1180px; margin: 0 auto; padding: 48px 24px 72px; }}
    aside {{ border-right: 1px solid #d8d2c1; padding-right: 24px; }}
    main {{ max-width: 820px; }}
    h1 {{ font-size: 48px; line-height: 1.1; margin: 0 0 8px; font-weight: normal; }}
    h2 {{ font-size: 28px; line-height: 1.2; margin: 0 0 16px; font-weight: normal; }}
    h3 {{ font-size: 24px; line-height: 1.25; margin: 42px 0 10px; font-weight: normal; }}
    ol {{ padding-left: 24px; margin: 0; }}
    li {{ margin: 10px 0; font-size: 17px; }}
    a {{ color: #8a3324; text-decoration: none; border-bottom: 1px solid #8a3324; }}
    .meta {{ font-family: "Courier New", Courier, monospace; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #5b5b5b; margin-bottom: 18px; }}
    .tabs {{ list-style: none; margin: 24px 0 0; padding: 0; }}
    .tabs li {{ margin: 12px 0; font-size: 16px; }}
    .issue-list {{ list-style-position: outside; }}
    .issue-list li {{ margin: 18px 0; }}
    .issue-summary {{ color: #5b5b5b; display: block; font-size: 15px; line-height: 1.45; margin-top: 4px; }}
    .section-note {{ color: #5b5b5b; font-size: 16px; margin: 0 0 18px; }}
    .poster-grid {{ columns: 3 180px; column-gap: 28px; }}
    .poster-grid li {{ break-inside: avoid; font-size: 15px; margin: 7px 0; }}
    @media (max-width: 760px) {{
      .page {{ display: block; padding: 36px 24px 64px; }}
      aside {{ border-right: 0; border-bottom: 1px solid #d8d2c1; padding: 0 0 22px; margin-bottom: 30px; }}
      h1 {{ font-size: 38px; }}
      .poster-grid {{ columns: 1; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <aside>
      <div class="meta">Current issue: 10 oral drafts · {len(poster_files)} ICLR RL poster drafts · {total_icml_issues} ICML RL paper drafts</div>
      <h1>The Policy Gradient</h1>
      <ul class="tabs">
        <li><a href="#orals">ICLR 2026 Orals</a></li>
        <li><a href="#posters">ICLR 2026 Posters</a></li>
        <li><a href="#icml-papers">ICML 2026 Papers</a></li>
      </ul>
    </aside>
    <main>
      <section id="orals">
        <h2>ICLR 2026 Orals</h2>
        <ol class="issue-list">
{oral_items}
        </ol>
      </section>
      <section id="posters">
        <h3>ICLR 2026 Posters</h3>
        <p class="section-note">{poster_count} reinforcement-learning-related poster papers, batched 50 per issue.</p>
        <ol class="poster-grid">
{poster_items}
        </ol>
      </section>
      <section id="icml-papers">
        <h3>ICML 2026 Papers</h3>
        <p class="section-note">{icml_count} reinforcement-learning-related ICML papers, batched 50 per issue.</p>
        <ol class="poster-grid">
{icml_items}
        </ol>
      </section>
    </main>
  </div>
</body>
</html>
"""


def main() -> None:
    DRAFT_DIR.mkdir(exist_ok=True)
    ICML_DIR.mkdir(parents=True, exist_ok=True)
    rl_papers = fetch_icml_papers()
    ICML_DATA_PATH.write_text(json.dumps(rl_papers, indent=2) + "\n")

    total_issues = math.ceil(len(rl_papers) / BATCH_SIZE)
    for old_file in ICML_DIR.glob("icml2026_papers_issue*.html"):
        old_file.unlink()
    index_lines = [
        "# ICML 2026 RL Paper Drafts",
        "",
        "- Source: ICML virtual site official JSON topic metadata",
        f"- RL-topic papers kept: {len(rl_papers)}",
        f"- Issue size: {BATCH_SIZE}",
        "",
    ]
    for issue in range(1, total_issues + 1):
        chunk = rl_papers[(issue - 1) * BATCH_SIZE : issue * BATCH_SIZE]
        filename = f"icml2026_papers_issue{issue:03d}.html"
        (ICML_DIR / filename).write_text(render_icml_issue(issue, total_issues, chunk))
        index_lines.append(f"- [Issue {issue:03d}](icml/papers/{filename}) - {len(chunk)} papers")

    ICML_INDEX_PATH.write_text("\n".join(index_lines) + "\n")
    SITE_INDEX_PATH.write_text(render_site_index(total_issues, len(rl_papers)))
    print(f"Kept {len(rl_papers)} ICML RL-topic papers")
    print(f"Wrote {total_issues} ICML issue files")


if __name__ == "__main__":
    main()
