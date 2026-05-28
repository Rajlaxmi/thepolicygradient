#!/usr/bin/env python3
"""Generate themed HTML email drafts for ICLR 2026 oral papers."""

from __future__ import annotations

import html
import json
import math
import re
import textwrap
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DRAFT_DIR = ROOT / "draft"
DATA_PATH = DRAFT_DIR / "iclr2026_orals.json"
INDEX_PATH = DRAFT_DIR / "iclr2026_oral_drafts_index.md"
API_URL = (
    "https://api2.openreview.net/notes?"
    + urllib.parse.urlencode(
        {
            "content.venueid": "ICLR.cc/2026/Conference",
            "content.venue": "ICLR 2026 Oral",
            "limit": "1000",
        }
    )
)


THEMES = [
    (
        "LLMs, Agents, and Tool Use",
        ["llm", "language model", "agent", "tool", "retrieval", "rag", "reasoning", "instruction", "chat", "memory"],
    ),
    (
        "Vision, Multimodal, and Generative Models",
        ["vision", "image", "video", "diffusion", "multimodal", "vlm", "visual", "generation", "render", "3d"],
    ),
    (
        "Reinforcement Learning and Control",
        ["reinforcement", "rl", "policy", "control", "reward", "offline rl", "robot", "planning", "mdp", "exploration"],
    ),
    (
        "Theory, Optimization, and Generalization",
        ["theory", "optimization", "generalization", "gradient", "convergence", "loss", "bound", "scaling law", "kernel"],
    ),
    (
        "Representation Learning and Architectures",
        ["representation", "transformer", "attention", "embedding", "latent", "architecture", "neural", "feature"],
    ),
    (
        "Data, Benchmarks, and Evaluation",
        ["dataset", "benchmark", "evaluation", "corpus", "data", "suite", "metric", "leaderboard"],
    ),
    (
        "Safety, Robustness, and Privacy",
        ["safety", "robust", "privacy", "adversarial", "alignment", "jailbreak", "trustworthy", "secure", "bias"],
    ),
    (
        "Science, Health, and Domain Applications",
        ["medical", "health", "biology", "protein", "molecule", "science", "climate", "physics", "chemistry", "biomedical"],
    ),
]

RL_STRONG_RELEVANCE_TERMS = [
    "reinforcement learning",
    "offline rl",
    "online rl",
    "rlhf",
    "rlvr",
    "grpo",
    "ppo",
    "dpo",
    "direct preference optimization",
    "preference optimization",
    "reward model",
    "reward function",
    "policy gradient",
    "policy optimization",
    "policy learning",
    "decision making",
    "markov decision",
    "mdp",
    "bandit",
    "imitation learning",
    "behavior cloning",
    "world model",
    "model-based planning",
    "rollout",
    "actor-critic",
    "q-learning",
]

RL_WEAK_RELEVANCE_TERMS = [
    "planning",
    "control",
    "robot",
    "embodied",
    "exploration",
    "trajectory",
]

NEXT_STEP_OVERRIDES = {
    "btEiAfnLsX": (
        "Run a controlled misspecification stress test: vary model capacity, reference-policy distance, beta, "
        "and the preference-pair sampling distribution, then compare DPO, AuxDPO, IPO/KTO-style losses, and "
        "two-stage RLHF on reward reversal. A strong follow-up is a pre-training diagnostic that predicts when "
        "DPO will hurt before you spend the alignment run; apply it first to safety refusal, summarization, and "
        "multi-objective preference data."
    ),
    "yDmb7xAfeb": (
        "Perturb the closed-loop ingredients separately: degrade visual fidelity while preserving action "
        "controllability, corrupt action conditioning while preserving video quality, and sweep rollout horizon "
        "plus inference-time compute. The ICLR-worthy extension is to turn World-In-World into a causal benchmark "
        "for embodied planning: which world-model errors actually change task success in robotics, games, and web agents?"
    ),
    "qmCpJtFZra": (
        "Ablate the design recipe along three axes: Teddymer synthetic pretraining versus experimental multimers, "
        "flow-prior sampling versus hallucination-style optimization, and test-time objectives such as interface "
        "hydrogen bonds, buried surface area, and developability. The application path is narrow but powerful: pick "
        "one target class, add a normalized compute budget and wet-lab or high-fidelity in-silico validation, and ask "
        "whether test-time compute obeys a real binder-design scaling law."
    ),
    "l1cLdEjESj": (
        "Attack the geometry channel directly: inject metric-depth scale drift, camera-pose noise, missing frames, "
        "and Cross-Task Adapter ablations, then measure whether 3D QA and grounding fail gracefully. A clean follow-up "
        "would apply Vid-LLM to egocentric robot or AR video and prove that reconstruction-reasoning co-training helps "
        "causal spatial queries, not just static benchmark labels."
    ),
    "wsnse46kRO": (
        "Treat visual plans as an intervention target: replace image-only scratchpads with text-only and hybrid "
        "scratchpads, corrupt intermediate plan frames, and increase horizon length until the policy breaks. The best "
        "application experiments are robot manipulation, UI navigation, and geometry tasks where drawing the next state "
        "should be more natural than verbalizing it; the ICLR angle is showing visual plans are causally used rather "
        "than decorative rationales."
    ),
    "3RQ863cRbx": (
        "Make the mechanism causal: patch or ablate the spatial-index components across VLM families and positional "
        "encoding schemes, then perturb object count, occlusion, attribute swaps, and layout symmetry. The useful "
        "application is a binding-repair objective: train or finetune VLMs to stabilize these indices and show gains "
        "on counting, visual search, referring-expression grounding, and compositional VQA."
    ),
}


def is_rl_related(paper: dict) -> bool:
    text = " ".join(
        [
            paper["title"],
            paper.get("abstract", ""),
            paper.get("tldr", ""),
            paper.get("primary_area", ""),
            " ".join(map(str, paper.get("keywords", []))),
        ]
    ).lower()
    titleish = " ".join(
        [
            paper["title"],
            paper.get("primary_area", ""),
            " ".join(map(str, paper.get("keywords", []))),
        ]
    ).lower()
    if re.search(r"\brl\b", text):
        return True
    for term in RL_STRONG_RELEVANCE_TERMS:
        if " " in term or "-" in term:
            if term in text:
                return True
        elif re.search(rf"\b{re.escape(term)}\w*\b", text):
            return True
    for term in RL_WEAK_RELEVANCE_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", titleish):
            return True
    return False


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


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value


def truncate(value: str, limit: int) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "..."


def author_line(authors) -> str:
    authors = [clean_text(a) for a in as_list(authors) if clean_text(a)]
    if len(authors) <= 6:
        return ", ".join(authors)
    return ", ".join(authors[:5]) + f", et al. ({len(authors)} authors)"


def theme_for(paper: dict) -> str:
    text = " ".join(
        [
            paper["title"],
            paper.get("abstract", ""),
            paper.get("tldr", ""),
            paper.get("primary_area", ""),
            " ".join(paper.get("keywords", [])),
        ]
    ).lower()
    scored = []
    for theme, keywords in THEMES:
        score = sum(text.count(k) for k in keywords)
        scored.append((score, theme))
    scored.sort(reverse=True)
    if scored[0][0] == 0:
        return "Methods, Models, and Learning Systems"
    return scored[0][1]


def paper_summary(paper: dict) -> str:
    tldr = clean_text(paper.get("tldr", ""))
    abstract = clean_text(paper.get("abstract", ""))
    area = clean_text(paper.get("primary_area", ""))
    if tldr:
        base = truncate(tldr, 330)
    elif abstract:
        sentences = re.split(r"(?<=[.!?])\s+", abstract)
        base = truncate(" ".join(sentences[:2]), 330)
    else:
        base = "This oral presents a contribution in " + (area or "machine learning") + "."
    return base


def next_steps(paper: dict) -> str:
    if paper["id"] in NEXT_STEP_OVERRIDES:
        return NEXT_STEP_OVERRIDES[paper["id"]]
    text = (
        paper["title"]
        + " "
        + paper.get("abstract", "")
        + " "
        + paper.get("tldr", "")
        + " "
        + " ".join(map(str, paper.get("keywords", [])))
    ).lower()
    titleish = (
        paper["title"]
        + " "
        + paper.get("primary_area", "")
        + " "
        + " ".join(map(str, paper.get("keywords", [])))
    ).lower()

    def has(words, haystack=text):
        return any(word in haystack for word in words)

    focus = truncate(
        clean_text(", ".join(map(str, paper.get("keywords", [])[:2])))
        or paper.get("primary_area", "")
        or paper["theme"],
        70,
    )

    if has(["medical", "health", "biology", "protein", "molecule", "chemical", "science", "physics", "climate", "biomedical"]):
        return (
            f"Use {focus} as the domain-validity test: perturb measurement noise, constraints, and out-of-"
            "distribution targets, then test whether expert-facing metrics agree with ML metrics. A strong ICLR angle "
            "is to couple the method with an executable or experimentally grounded validation loop in one narrow domain."
        )
    if has(["safety", "robust", "privacy", "adversarial", "alignment", "jailbreak", "watermark", "signature", "secure"]):
        return (
            f"Attack the {focus} claim before extending it: run adaptive adversaries, distribution shift, paraphrase/corruption "
            "tests, and capability-preservation checks. The follow-up worth writing is a threat-model-specific version "
            "with clear guarantees, costs, and failure cases on real model outputs rather than a broad safety claim."
        )
    if has(["dataset", "benchmark", "corpus", "suite", "arena", "gym", "bench"], titleish):
        return (
            f"Treat {focus} as an evaluation substrate, not just a leaderboard: perturb task difficulty, label noise, "
            "domain shift, and hidden-test leakage, then add one baseline from outside the paper's comfort zone. "
            "A publishable extension would apply the benchmark to a live research workflow and show which model "
            "ranking changes under controlled stress."
        )
    if has(["agent", "tool", "retrieval", "rag", "reasoning", "memory", "search", "planner", "planning"]):
        return (
            f"Perturb the {focus} loop directly: remove memory, corrupt retrieved evidence, cap tool calls, vary horizon "
            "length, and separate planning errors from execution errors. The ICLR-style application is to port the "
            "method to one messy environment such as code editing, web navigation, scientific QA, or data analysis and "
            "report failure taxonomy, not only aggregate success."
        )
    if has(["reinforcement", "rl", "policy", "reward", "offline rl", "control", "mdp", "exploration", "preference"]):
        return (
            f"Stress the {focus} objective, not only the score: sweep reward misspecification, dataset quality, reference-policy "
            "distance, discount/horizon, and action-noise perturbations. A strong follow-up would identify the regime "
            "boundary where the method beats simpler imitation, supervised fine-tuning, or PPO-style baselines, then "
            "apply it to one realistic control or alignment setting."
        )
    if has(["diffusion", "flow", "generative", "image", "video", "3d", "multimodal", "vision", "visual", "render"]):
        return (
            f"Make the {focus} representation earn its keep: perturb resolution, viewpoint, composition, prompt specificity, "
            "temporal consistency, and compute budget, then compare against a simpler generator or encoder with matched "
            "parameters. The application angle is strongest if you connect quality to downstream use such as planning, "
            "editing, simulation, robotics, or scientific design rather than only prettier samples."
        )
    if has(["theory", "bound", "convergence", "proof", "optimization", "gradient", "estimator", "loss"]):
        return (
            f"Turn the {focus} theorem into a falsifiable experiment: construct synthetic cases that violate each assumption, "
            "sweep condition number/model scale/noise, and test whether the predicted failure mode appears before the "
            "main metric collapses. The ICLR contribution would be a diagnostic or algorithmic patch that transfers "
            "from the toy setting to a real training run."
        )
    if has(["transformer", "attention", "architecture", "representation", "embedding", "latent", "token", "sequence"]):
        return (
            f"Ablate the {focus} architectural claim surgically: freeze or swap the proposed component, match parameter count "
            "and FLOPs, perturb sequence length or modality, and measure calibration plus robustness, not just accuracy. "
            "A good application paper would show the representation changes what a downstream system can do under a "
            "fixed compute budget."
        )
    return (
        f"Find the smallest {focus} intervention that could make the paper wrong: remove the central component, match compute "
        "against a boring baseline, perturb the data distribution, and inspect failures case by case. The follow-up "
        "becomes ICLR-shaped if the perturbation reveals a reusable design rule or a new application where the method "
        "changes the research workflow."
    )


def fetch_papers() -> list[dict]:
    with urllib.request.urlopen(API_URL, timeout=60) as response:
        data = json.load(response)
    papers = []
    for note in data.get("notes", []):
        content = note.get("content", {})
        paper = {
            "id": note["id"],
            "forum": note.get("forum", note["id"]),
            "title": clean_text(field(content, "title")),
            "authors": as_list(field(content, "authors", [])),
            "keywords": as_list(field(content, "keywords", [])),
            "tldr": clean_text(field(content, "TLDR")),
            "abstract": clean_text(field(content, "abstract")),
            "primary_area": clean_text(field(content, "primary_area")),
            "pdf": field(content, "pdf"),
        }
        paper["theme"] = theme_for(paper)
        papers.append(paper)
    papers.sort(key=lambda p: (p["theme"], p["title"].casefold()))
    return papers


def batch_papers(papers: list[dict], size: int = 6) -> list[tuple[str, list[dict]]]:
    buckets = defaultdict(list)
    for paper in papers:
        buckets[paper["theme"]].append(paper)

    batches = []
    carry = []
    for theme in [t[0] for t in THEMES] + ["Methods, Models, and Learning Systems"]:
        items = buckets.get(theme, [])
        while len(items) >= size:
            batches.append((theme, items[:size]))
            items = items[size:]
        if items:
            carry.extend(items)

    carry.sort(key=lambda p: (p["theme"], p["title"].casefold()))
    while carry:
        group = carry[:size]
        carry = carry[size:]
        theme_counts = defaultdict(int)
        for paper in group:
            theme_counts[paper["theme"]] += 1
        dominant = sorted(theme_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        label = dominant if len(theme_counts) <= 2 else "Cross-Cutting Oral Highlights"
        batches.append((label, group))
    return batches


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def paper_card(paper: dict, number: int, last: bool) -> str:
    pad_bottom = "48px" if last else "36px"
    authors = author_line(paper["authors"])
    keywords = paper.get("keywords", [])
    tag = esc(paper["theme"])
    if keywords:
        tag += " &middot; " + esc(truncate(", ".join(map(str, keywords[:2])), 48))
    pdf_link = ""
    pdf = paper.get("pdf")
    if pdf:
        pdf_url = pdf if str(pdf).startswith("http") else "https://openreview.net" + str(pdf)
        pdf_link = f'&nbsp;&nbsp;&nbsp;<a href="{esc(pdf_url)}" style="font-family:\'Courier New\', Courier, monospace; font-size:11px; color:#5b5b5b; letter-spacing:2px; text-transform:uppercase; border-bottom:1px solid #5b5b5b;">PDF</a>'
    return f"""
<!-- PAPER {number:02d} -->
<tr><td class="px-mob" style="padding: {'48px' if number == 1 else '0'} 40px 8px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td valign="top" width="80" style="padding-right:18px;">
<div style="font-family: Georgia, serif; font-size:64px; line-height:54px; color:#8a3324; font-style:italic;">{number:02d}</div>
<div style="border-top:2px solid #8a3324; width:36px; margin-top:6px;"></div>
</td>
<td valign="top">
<div style="margin-bottom:8px;">
<div style="font-family:'Courier New', Courier, monospace; font-size:10px; line-height:12px; color:#1a1a1a; letter-spacing:1px; text-transform:uppercase; margin-bottom:7px;"><span style="background:#e9b44c; color:#1a1a1a; padding:3px 8px;">&#9733; Oral</span></div>
<div style="font-family:'Courier New', Courier, monospace; font-size:10px; line-height:16px; color:#5b5b5b; letter-spacing:1px; text-transform:uppercase;">{tag}</div>
</div>
<h2 style="margin:0; font-family: Georgia, serif; font-size:22px; line-height:28px; color:#1a1a1a; font-weight:normal;">{esc(paper['title'])}</h2>
<div style="font-family: Georgia, serif; font-size:13px; color:#5b5b5b; font-style:italic; margin-top:6px;">{esc(authors)}</div>
</td></tr></table>
</td></tr>
<tr><td class="px-mob" style="padding: 18px 40px 0 40px;">
<p style="margin:0; font-family: Georgia, serif; font-size:15px; line-height:24px; color:#2a2a2a;">{esc(paper_summary(paper))}</p>
</td></tr>
<tr><td class="px-mob" style="padding: 18px 40px 0 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f3efe6; border-left:3px solid #8a3324;"><tr><td style="padding:14px 18px;">
<div style="font-family:'Courier New', Courier, monospace; font-size:10px; color:#8a3324; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;">Next steps for researchers</div>
<div style="font-family: Georgia, serif; font-size:14px; line-height:22px; color:#2a2a2a;">{esc(next_steps(paper))}</div>
</td></tr></table>
</td></tr>
<tr><td class="px-mob" style="padding: 18px 40px {pad_bottom} 40px;">
<a href="https://openreview.net/forum?id={esc(paper['forum'])}" style="font-family:'Courier New', Courier, monospace; font-size:11px; color:#1a1a1a; letter-spacing:2px; text-transform:uppercase; border-bottom:1px solid #1a1a1a;">Read on OpenReview &rarr;</a>{pdf_link}
</td></tr>
{'' if last else '<tr><td class="px-mob" align="center" style="padding: 0 40px 36px 40px;"><div style="font-family: Georgia, serif; font-size:18px; color:#8a3324; letter-spacing:18px;">&#10086;&nbsp;&#10086;&nbsp;&#10086;</div></td></tr>'}
"""


def render_issue(issue: int, theme: str, papers: list[dict], total_issues: int) -> str:
    today = date.today().strftime("%B %-d, %Y")
    count = len(papers)
    read_min = max(4, math.ceil(count * 1.5))
    cards = "\n".join(paper_card(p, i + 1, i == count - 1) for i, p in enumerate(papers))
    titles = "; ".join(truncate(p["title"], 70) for p in papers[:3])
    if count > 3:
        titles += "; and more"
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>ICLR 2026 Orals - Issue {issue:02d}</title>
<style>
body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #f3efe6; }}
a {{ color: #8a3324; text-decoration: none; }}
@media screen and (max-width: 780px) {{
  .container {{ width: 100% !important; }}
  .px-mob {{ padding-left: 24px !important; padding-right: 24px !important; }}
}}
</style>
</head>
<body style="margin:0; padding:0; background-color:#f3efe6;">
<div style="display:none; max-height:0; overflow:hidden; mso-hide:all; font-size:1px; line-height:1px; color:#f3efe6;">ICLR 2026 oral papers: {esc(titles)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f3efe6">
<tr><td align="center" style="padding: 32px 16px;">
<table role="presentation" class="container" width="760" cellpadding="0" cellspacing="0" border="0" style="width:760px; max-width:760px; background-color:#fbf8f1; border:1px solid #1a1a1a;">
<tr><td style="height:6px; background-color:#1a1a1a; line-height:6px; font-size:0;">&nbsp;</td></tr>
<tr><td class="px-mob" style="padding: 18px 40px 12px 40px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td align="left" style="font-family:'Courier New', Courier, monospace; font-size:11px; color:#1a1a1a; letter-spacing:2px;">Vol. 04 &nbsp;&middot;&nbsp; Issue {issue}</td>
<td align="right" style="font-family:'Courier New', Courier, monospace; font-size:11px; color:#1a1a1a; letter-spacing:2px;">{esc(today)}</td>
</tr></table></td></tr>
<tr><td class="px-mob" style="padding: 0 40px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:1px solid #1a1a1a; height:1px; line-height:1px; font-size:0;">&nbsp;</td></tr></table></td></tr>
<tr><td class="px-mob" align="center" style="padding: 28px 40px 8px 40px;"><div style="font-family: Georgia, 'Times New Roman', Times, serif; font-size:54px; line-height:54px; letter-spacing:2px; color:#1a1a1a; font-weight:normal;"><i>The&nbsp;</i><b>Policy</b><i>&nbsp;Gradient</i></div></td></tr>
<tr><td class="px-mob" align="center" style="padding: 4px 40px 24px 40px; font-family: 'Courier New', Courier, monospace; font-size:11px; color:#5b5b5b; letter-spacing:3px; text-transform:uppercase;">A curated digest of machine learning research</td></tr>
<tr><td class="px-mob" style="padding: 0 40px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:3px double #1a1a1a; height:3px; line-height:3px; font-size:0;">&nbsp;</td></tr></table></td></tr>
<tr><td class="px-mob" style="padding: 36px 40px 12px 40px;">
<div style="font-family:'Courier New', Courier, monospace; font-size:11px; color:#8a3324; letter-spacing:3px; text-transform:uppercase; margin-bottom:14px;">&#9670; ICLR 2026 Orals, {issue} of {total_issues}</div>
<h1 style="margin:0; font-family: Georgia, serif; font-size:38px; line-height:42px; color:#1a1a1a; font-weight:normal; letter-spacing:-0.5px;">{esc(theme)}.</h1>
<p style="margin: 18px 0 0 0; font-family: Georgia, serif; font-size:16px; line-height:26px; color:#3a3a3a;">A themed pass through the ICLR 2026 oral track. This draft collects {count} oral paper{'s' if count != 1 else ''}, with a compact research brief and concrete next steps for deciding whether to read deeply, reproduce, benchmark, or cite.</p>
</td></tr>
<tr><td class="px-mob" style="padding: 24px 40px 32px 40px; border-bottom:1px solid #d8d2c1; font-family: Georgia, serif; font-size:13px; color:#5b5b5b; font-style:italic;">Edited by the Research Desk &nbsp;&middot;&nbsp; {count} papers &nbsp;&middot;&nbsp; ~{read_min} min read</td></tr>
{cards}
<tr><td class="px-mob" style="padding: 40px 40px 0 40px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#1a1a1a;"><tr><td style="padding: 32px 32px;">
<div style="font-family:'Courier New', Courier, monospace; font-size:11px; color:#e9b44c; letter-spacing:3px; text-transform:uppercase;">From the editor</div>
<p style="margin: 16px 0 0 0; font-family: Georgia, serif; font-size:15px; line-height:24px; color:#f3efe6; font-style:italic;">This issue is a working research draft: use it as a triage layer before committing time to full papers. The next-step notes are meant to turn each oral from a title in a program into an actionable reading or replication decision.</p>
<div style="font-family:'Courier New', Courier, monospace; font-size:11px; color:#a8a094; letter-spacing:2px; margin-top:18px;">&mdash; The Research Desk</div>
</td></tr></table></td></tr>
<tr><td class="px-mob" style="padding: 40px 40px 24px 40px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-top:1px solid #1a1a1a; height:1px; line-height:1px; font-size:0;">&nbsp;</td></tr></table></td></tr>
<tr><td class="px-mob" align="center" style="padding: 0 40px 12px 40px;"><div style="font-family: Georgia, serif; font-size:14px; color:#1a1a1a; font-style:italic; letter-spacing:1px;"><i>The&nbsp;</i><b>Policy</b><i>&nbsp;Gradient</i></div></td></tr>
<tr><td class="px-mob" align="center" style="padding: 0 40px 32px 40px; font-family: Georgia, serif; font-size:11px; color:#8a8a8a; line-height:16px;">&copy; 2026 The Policy Gradient. <br/>Paper data sourced from OpenReview ICLR 2026 oral track. Abstracts and paper metadata remain &copy; their respective authors.</td></tr>
<tr><td style="height:6px; background-color:#1a1a1a; line-height:6px; font-size:0;">&nbsp;</td></tr>
</table></td></tr></table>
</body>
</html>
"""


def main():
    DRAFT_DIR.mkdir(exist_ok=True)
    all_papers = fetch_papers()
    papers = [paper for paper in all_papers if is_rl_related(paper)]
    for paper in papers:
        paper["summary"] = paper_summary(paper)
        paper["next_steps"] = next_steps(paper)
    DATA_PATH.write_text(json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8")
    batches = batch_papers(papers)
    total = len(batches)
    for stale in DRAFT_DIR.glob("iclr2026_orals_issue*.html"):
        stale.unlink()
    index_lines = [
        "# ICLR 2026 RL-Oral Drafts",
        "",
        f"Generated {total} email drafts from {len(papers)} RL-related OpenReview oral papers.",
        "Issues 1-9 contain 6 oral papers each; Issue 10 contains the remaining 4 RL-related oral papers.",
        f"Filtered out {len(all_papers) - len(papers)} non-RL oral papers.",
        "",
    ]
    for issue, (theme, group) in enumerate(batches, start=1):
        slug = re.sub(r"[^a-z0-9]+", "_", theme.lower()).strip("_")
        filename = f"iclr2026_orals_issue{issue:02d}_{slug}.html"
        path = DRAFT_DIR / filename
        path.write_text(render_issue(issue, theme, group, total), encoding="utf-8")
        index_lines.append(f"- Issue {issue:02d}: `{filename}` - {theme} ({len(group)} papers)")
        for paper in group:
            index_lines.append(f"  - {paper['title']} ({paper['id']})")
    INDEX_PATH.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"Fetched {len(all_papers)} oral papers")
    print(f"Kept {len(papers)} RL-related oral papers")
    print(f"Drafted {len(papers)} RL-related oral papers")
    print(f"Filtered out {len(all_papers) - len(papers)} non-RL oral papers")
    print(f"Wrote {total} HTML drafts to {DRAFT_DIR}")
    print(f"Wrote cache: {DATA_PATH}")
    print(f"Wrote index: {INDEX_PATH}")


if __name__ == "__main__":
    main()
