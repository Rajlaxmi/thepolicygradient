#!/usr/bin/env python3
"""Generate ICLR 2026 poster issue pages and update the landing page."""

from __future__ import annotations

import html
import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

from generate_iclr_oral_drafts import is_rl_related


ROOT = Path(__file__).resolve().parent
DRAFT_DIR = ROOT / "draft"
POSTER_DIR = DRAFT_DIR / "posters"
POSTER_DATA_PATH = DRAFT_DIR / "iclr2026_posters.json"
POSTER_INDEX_PATH = DRAFT_DIR / "iclr2026_poster_drafts_index.md"
SITE_INDEX_PATH = ROOT / "index.html"
BATCH_SIZE = 50
API_BASE = "https://api2.openreview.net/notes"


ORAL_ISSUES = [
    (
        "draft/iclr2026_orals_issue01_llms_agents_and_tool_use.html",
        "Issue 01 - LLMs, Agents, and Tool Use",
        "AgentGym-RL; EmotionThinker; Gaia2; GEPA; In-the-Flow Agentic System Optimization; MedAgentGym.",
    ),
    (
        "draft/iclr2026_orals_issue02_llms_agents_and_tool_use.html",
        "Issue 02 - LLMs, Agents, and Tool Use",
        "MemAgent; spatial intelligence in MLLMs; online learning with ranking feedback; OpenApps; MoE reasoning sparsity; Q-RAG.",
    ),
    (
        "draft/iclr2026_orals_issue03_llms_agents_and_tool_use.html",
        "Issue 03 - LLMs, Agents, and Tool Use",
        "Visual RL for image quality; sampling-based reasoning; belief-deviation reduction; RefineStat; social-learning control; coverage principle.",
    ),
    (
        "draft/iclr2026_orals_issue04_vision_multimodal_and_generative_models.html",
        "Issue 04 - Vision, Multimodal, and Generative Models",
        "Compositional diffusion for planning; DiffusionNFT; FlashWorld; latent particle world models; MotionStream; safety-guided flow.",
    ),
    (
        "draft/iclr2026_orals_issue05_reinforcement_learning_and_control.html",
        "Issue 05 - Reinforcement Learning and Control",
        "Differentiable MPC; offline reward evaluation for bidding; exploratory diffusion; recursive likelihood-ratio optimization; hyperparameter trajectories; reward hacking.",
    ),
    (
        "draft/iclr2026_orals_issue06_reinforcement_learning_and_control.html",
        "Issue 06 - Reinforcement Learning and Control",
        "LongWriter-Zero; LoongRL; sparse CUDA generation with DRL; Mean Flow Policy; Nash preference optimization; Omni-Reward.",
    ),
    (
        "draft/iclr2026_orals_issue07_reinforcement_learning_and_control.html",
        "Issue 07 - Reinforcement Learning and Control",
        "Optimistic task inference; overthinking reduction; TD-JEPA; scaling RL compute for LLMs; ride-sharing dispatch; TROLL trust regions.",
    ),
    (
        "draft/iclr2026_orals_issue08_cross_cutting_oral_highlights.html",
        "Issue 08 - Cross-Cutting Oral Highlights",
        "MomaGraph; semi-supervised preference optimization; human feedback descriptions; DPO misspecification; World-In-World; robot action learning.",
    ),
    (
        "draft/iclr2026_orals_issue09_safety_robustness_and_privacy.html",
        "Issue 09 - Safety, Robustness, and Privacy",
        "Conformal robustness control; personalized generative reward models; PateGAIL++; SafeDPO; dormant adversarial behaviors; discount model search.",
    ),
    (
        "draft/iclr2026_orals_issue10_theory_optimization_and_generalization.html",
        "Issue 10 - Theory, Optimization, and Generalization",
        "FIRE; sticky Track-and-Stop; token-importance guided DPO; Visual Planning.",
    ),
]


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def field(content: dict, key: str, default=""):
    value = content.get(key, default)
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def author_line(authors) -> str:
    authors = [clean_text(str(author)) for author in as_list(authors) if clean_text(str(author))]
    if len(authors) <= 6:
        return ", ".join(authors)
    return ", ".join(authors[:5]) + f", et al. ({len(authors)} authors)"


def fetch_posters() -> list[dict]:
    notes = []
    offset = 0
    while True:
        url = API_BASE + "?" + urllib.parse.urlencode(
            {
                "content.venueid": "ICLR.cc/2026/Conference",
                "content.venue": "ICLR 2026 Poster",
                "limit": "1000",
                "offset": str(offset),
            }
        )
        with urllib.request.urlopen(url, timeout=90) as response:
            data = json.load(response)
        batch = data.get("notes", [])
        notes.extend(batch)
        if len(batch) < 1000:
            break
        offset += len(batch)

    posters = []
    for note in notes:
        content = note.get("content", {})
        posters.append(
            {
                "id": note["id"],
                "forum": note.get("forum", note["id"]),
                "title": clean_text(field(content, "title")),
                "authors": as_list(field(content, "authors", [])),
                "keywords": as_list(field(content, "keywords", [])),
                "primary_area": clean_text(field(content, "primary_area")),
                "pdf": field(content, "pdf"),
            }
        )
    posters.sort(key=lambda paper: paper["title"].casefold())
    return posters


def poster_meta(paper: dict) -> str:
    bits = []
    if paper.get("primary_area"):
        bits.append(paper["primary_area"])
    keywords = [clean_text(str(keyword)) for keyword in paper.get("keywords", [])[:3]]
    if keywords:
        bits.append(", ".join(keywords))
    return " · ".join(bits)


def render_poster_issue(issue: int, total: int, papers: list[dict]) -> str:
    items = []
    for index, paper in enumerate(papers, start=1):
        pdf = paper.get("pdf")
        pdf_url = pdf if str(pdf).startswith("http") else "https://openreview.net" + str(pdf)
        pdf_link = f' · <a href="{esc(pdf_url)}">PDF</a>' if pdf else ""
        items.append(
            f"""      <li>
        <span class="paper-num">{index:02d}</span>
        <div>
          <a href="https://openreview.net/forum?id={esc(paper['forum'])}">{esc(paper['title'])}</a>
          <span class="authors">{esc(author_line(paper['authors']))}</span>
          <span class="paper-meta">{esc(poster_meta(paper))}{pdf_link}</span>
        </div>
      </li>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ICLR 2026 Posters - Issue {issue:03d}</title>
  <style>
    body {{ margin: 0; background: #f3efe6; color: #1a1a1a; font-family: Georgia, "Times New Roman", Times, serif; line-height: 1.5; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 44px 24px 72px; }}
    h1 {{ font-size: 42px; line-height: 1.1; margin: 0 0 8px; font-weight: normal; }}
    h2 {{ font-size: 22px; line-height: 1.25; margin: 0 0 30px; font-weight: normal; color: #5b5b5b; }}
    a {{ color: #8a3324; text-decoration: none; border-bottom: 1px solid #8a3324; }}
    .meta {{ font-family: "Courier New", Courier, monospace; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #5b5b5b; margin-bottom: 18px; }}
    .poster-list {{ list-style: none; margin: 0; padding: 0; }}
    .poster-list li {{ border-top: 1px solid #d8d2c1; display: grid; grid-template-columns: 48px 1fr; gap: 18px; padding: 16px 0; }}
    .paper-num {{ color: #8a3324; font-family: "Courier New", Courier, monospace; font-size: 13px; letter-spacing: 1px; padding-top: 3px; }}
    .authors, .paper-meta {{ display: block; color: #5b5b5b; font-size: 14px; margin-top: 4px; }}
    .paper-meta {{ font-family: "Courier New", Courier, monospace; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; }}
    .nav {{ display: flex; justify-content: space-between; gap: 16px; margin-top: 36px; }}
    @media (max-width: 640px) {{
      h1 {{ font-size: 32px; }}
      .poster-list li {{ grid-template-columns: 1fr; gap: 6px; }}
      .nav {{ display: block; }}
      .nav a {{ display: inline-block; margin: 8px 14px 0 0; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="meta">The Policy Gradient · ICLR 2026 Posters</div>
    <h1>Poster Issue {issue:03d}</h1>
    <h2>{len(papers)} poster papers · issue {issue} of {total}</h2>
    <ol class="poster-list">
{chr(10).join(items)}
    </ol>
    <div class="nav">
      <a href="../../index.html#posters">Back to poster index</a>
      {"<a href=\"iclr2026_posters_issue%03d.html\">Previous issue</a>" % (issue - 1) if issue > 1 else "<span></span>"}
      {"<a href=\"iclr2026_posters_issue%03d.html\">Next issue</a>" % (issue + 1) if issue < total else "<span></span>"}
    </div>
  </main>
</body>
</html>
"""


def render_site_index(total_poster_issues: int, poster_count: int) -> str:
    oral_items = "\n".join(
        f"""        <li>
          <a href="{esc(href)}">{esc(title)}</a>
          <span class="issue-summary">{esc(summary)}</span>
        </li>"""
        for href, title, summary in ORAL_ISSUES
    )
    poster_items = "\n".join(
        f"""        <li><a href="draft/posters/iclr2026_posters_issue{issue:03d}.html">Poster Issue {issue:03d}</a></li>"""
        for issue in range(1, total_poster_issues + 1)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Policy Gradient - ICLR 2026</title>
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
      <div class="meta">Current issue: 10 oral drafts · {total_poster_issues} RL poster drafts</div>
      <h1>The Policy Gradient</h1>
      <ul class="tabs">
        <li><a href="#orals">ICLR 2026 Orals</a></li>
        <li><a href="#posters">ICLR 2026 Posters</a></li>
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
    </main>
  </div>
</body>
</html>
"""


def main():
    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    all_posters = fetch_posters()
    posters = [poster for poster in all_posters if is_rl_related(poster)]
    POSTER_DATA_PATH.write_text(json.dumps(posters, indent=2, ensure_ascii=False), encoding="utf-8")
    for stale in POSTER_DIR.glob("iclr2026_posters_issue*.html"):
        stale.unlink()

    total = math.ceil(len(posters) / BATCH_SIZE)
    index_lines = [
        "# ICLR 2026 Poster Drafts",
        "",
        f"Generated {total} poster issues from {len(posters)} RL-related OpenReview poster papers.",
        f"Filtered out {len(all_posters) - len(posters)} non-RL poster papers.",
        f"Issues contain {BATCH_SIZE} poster papers each, except the final issue.",
        "",
    ]
    for issue in range(1, total + 1):
        batch = posters[(issue - 1) * BATCH_SIZE : issue * BATCH_SIZE]
        filename = f"iclr2026_posters_issue{issue:03d}.html"
        (POSTER_DIR / filename).write_text(render_poster_issue(issue, total, batch), encoding="utf-8")
        index_lines.append(f"- Poster Issue {issue:03d}: `posters/{filename}` ({len(batch)} papers)")
    POSTER_INDEX_PATH.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    SITE_INDEX_PATH.write_text(render_site_index(total, len(posters)), encoding="utf-8")
    print(f"Fetched {len(all_posters)} poster papers")
    print(f"Kept {len(posters)} RL-related poster papers")
    print(f"Filtered out {len(all_posters) - len(posters)} non-RL poster papers")
    print(f"Wrote {total} poster issue pages to {POSTER_DIR}")
    print(f"Updated {SITE_INDEX_PATH}")


if __name__ == "__main__":
    main()
