#!/usr/bin/env python3
"""Advisory Scoring Benchmark: tests _rank_score variations against ground truth.

Loads labeled advice items from advisory_ground_truth.json and scores each
item through multiple scoring formula variations. Computes Precision@K,
Recall, Noise Rate, and Score Gap metrics to identify the best formula.

Usage:
    python benchmarks/advisory_scoring_benchmark.py [--output-dir benchmarks/results]

Output:
    - JSON results file with raw scores per variation
    - Markdown summary table
    - Per-source breakdown
    - Per-tool breakdown
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GROUND_TRUTH_FILE = PROJECT_ROOT / "benchmarks" / "data" / "advisory_ground_truth.json"

# --------------- Source quality tiers (from advisor.py:4727) ---------------
SOURCE_QUALITY_BASELINE = {
    "eidos": 0.90,
    "replay": 0.85,
    "self_awareness": 0.80,
    "trigger": 0.75,
    "opportunity": 0.72,
    "convo": 0.70,
    "engagement": 0.65,
    "mind": 0.65,
    "chip": 0.65,
    "semantic-agentic": 0.62,
    "niche": 0.60,
    "semantic-hybrid": 0.58,
    "semantic": 0.55,
    "cognitive": 0.50,
    "bank": 0.40,
}

MIN_RANK_SCORE_DEFAULT = 0.35
NOTE_THRESHOLD_DEFAULT = 0.42


@dataclass
class AdviceCase:
    case_id: str
    tool: str
    source: str
    text: str
    context_match: float
    confidence: float
    insight_key: str
    useful: bool
    reason: str


@dataclass
class ScoringVariation:
    name: str
    description: str
    score_fn: Callable[[AdviceCase], float]
    min_rank_score: float = MIN_RANK_SCORE_DEFAULT
    note_threshold: float = NOTE_THRESHOLD_DEFAULT


@dataclass
class VariationResult:
    name: str
    description: str
    precision_at_1: float = 0.0
    precision_at_2: float = 0.0
    precision_at_4: float = 0.0
    precision_at_8: float = 0.0
    recall: float = 0.0
    noise_rate: float = 0.0
    mean_useful_score: float = 0.0
    mean_noise_score: float = 0.0
    score_gap: float = 0.0
    useful_above_gate: int = 0
    noise_above_gate: int = 0
    total_above_min: int = 0
    per_source: Dict[str, Dict[str, float]] = field(default_factory=dict)
    per_tool: Dict[str, Dict[str, float]] = field(default_factory=dict)
    scored_items: List[Dict[str, Any]] = field(default_factory=list)


# --------------- Noise detection (simplified from advisor.py) ---------------

_PLATITUDE_WORDS = {
    "important", "carefully", "consider", "should", "matters", "relevant",
    "informed", "decisions", "quality", "varies", "properly",
}

_TAUTOLOGY_PHRASES = [
    "was used successfully",
    "completed without errors",
    "contains relevant information",
    "is an important step",
]


def _is_noise_text(text: str) -> float:
    """Return noise penalty multiplier (1.0 = clean, <1.0 = penalised)."""
    t = text.lower().strip()
    # Transcript artifacts
    if t.startswith("cycle summary:") or "edits (100%)" in t or "edits (75%)" in t:
        return 0.05
    if "user expressed" in t and ("satisfaction" in t or "frustration" in t):
        return 0.05
    # Leaked user prompts
    if "i meant is" in t or "lets make those" in t or "remember:" in t and "what i mean" in t:
        return 0.10
    # Tautologies
    for phrase in _TAUTOLOGY_PHRASES:
        if phrase in t:
            return 0.40
    # Platitude density
    words = set(t.split())
    platitude_count = len(words & _PLATITUDE_WORDS)
    word_count = max(1, len(t.split()))
    if platitude_count >= 3 and word_count < 15:
        return 0.60
    return 1.0


def _score_actionability(text: str) -> float:
    """Simple actionability heuristic (0-1)."""
    t = text.lower()
    score = 0.0
    # Directive verbs
    for verb in ["use", "avoid", "check", "ensure", "add", "move", "split",
                 "verify", "prefer", "run", "set", "pass", "fix", "wire"]:
        if verb in t.split():
            score += 0.15
    # Conditional context
    for cond in ["when", "if ", "before", "after", "instead of"]:
        if cond in t:
            score += 0.10
    # Specificity (tech terms, file refs)
    for spec in [".py", ".json", ".js", "git ", "pip ", "npm ", "curl ",
                 "_rank_score", "CLAUDE.md", "Meta-Ralph", "EIDOS", "tweet.py",
                 "subprocess", "asyncio", "SQLite", "JSONL"]:
        if spec in text:  # case-sensitive for filenames
            score += 0.12
    return min(1.0, max(0.05, score))


# --------------- Scoring functions ---------------

def _make_baseline_scorer(
    source_quality: Dict[str, float],
    rel_weight: float = 0.45,
    qual_weight: float = 0.30,
    trust_weight: float = 0.25,
    trust_default: float = 0.50,
    feedback_enabled: bool = False,
    category_boost_enabled: bool = False,
) -> Callable[[AdviceCase], float]:
    """Create a parameterised scoring function."""
    # Pre-load feedback cache if enabled
    fb_cache = None
    if feedback_enabled:
        try:
            from lib.feedback_effectiveness_cache import get_feedback_cache
            fb_cache = get_feedback_cache()
        except Exception:
            pass

    def score_fn(case: AdviceCase) -> float:
        # Relevance
        relevance = max(0.0, min(1.0, case.context_match))

        # Quality
        text_q = _score_actionability(case.text)
        src_q = source_quality.get(case.source, 0.50)
        quality = max(text_q, src_q)

        # Trust
        trust = max(0.0, min(1.0, case.confidence))
        if fb_cache and feedback_enabled:
            fb_eff = fb_cache.get_source_effectiveness(case.source)
            if fb_eff >= 0:
                trust = max(trust, fb_eff)
        if trust < 0.1:
            trust = trust_default

        # Additive blend
        score = (rel_weight * relevance) + (qual_weight * quality) + (trust_weight * trust)

        # Category boost
        if category_boost_enabled and fb_cache:
            cat_boost = fb_cache.get_category_boost(case.tool.lower())
            score *= max(0.9, min(1.2, cat_boost))

        # Noise penalties
        noise_mult = _is_noise_text(case.text)
        score *= noise_mult

        return round(score, 6)

    return score_fn


def build_variations() -> List[ScoringVariation]:
    """Build all scoring variations to benchmark."""
    sq = dict(SOURCE_QUALITY_BASELINE)
    sq_bank50 = dict(sq); sq_bank50["bank"] = 0.50
    sq_bank30 = dict(sq); sq_bank30["bank"] = 0.30
    sq_no_bank = dict(sq); sq_no_bank["bank"] = 0.0

    return [
        ScoringVariation(
            name="a_baseline",
            description="Current formula: 0.45*rel + 0.30*qual + 0.25*trust, trust_default=0.50",
            score_fn=_make_baseline_scorer(sq),
        ),
        ScoringVariation(
            name="b_feedback_loop",
            description="+ feedback loop: trust boosted by source effectiveness from feedback data",
            score_fn=_make_baseline_scorer(sq, feedback_enabled=True),
        ),
        ScoringVariation(
            name="c_feedback_catboost",
            description="+ feedback + category boost: multiplicative 0.9-1.2 from feedback",
            score_fn=_make_baseline_scorer(sq, feedback_enabled=True, category_boost_enabled=True),
        ),
        ScoringVariation(
            name="d_bank_quality_50",
            description="Memory banks quality raised 0.40 -> 0.50",
            score_fn=_make_baseline_scorer(sq_bank50),
        ),
        ScoringVariation(
            name="e_bank_removed",
            description="Memory banks quality set to 0 (effectively removed)",
            score_fn=_make_baseline_scorer(sq_no_bank),
        ),
        ScoringVariation(
            name="f_bank_quality_30",
            description="Memory banks quality lowered 0.40 -> 0.30",
            score_fn=_make_baseline_scorer(sq_bank30),
        ),
        ScoringVariation(
            name="g_trust_default_70",
            description="Default trust raised 0.50 -> 0.70 (less penalty for new items)",
            score_fn=_make_baseline_scorer(sq, trust_default=0.70),
        ),
        ScoringVariation(
            name="h_relevance_heavy",
            description="Relevance-heavy: 0.55*rel + 0.25*qual + 0.20*trust",
            score_fn=_make_baseline_scorer(sq, rel_weight=0.55, qual_weight=0.25, trust_weight=0.20),
        ),
        ScoringVariation(
            name="i_quality_heavy",
            description="Quality-heavy: 0.35*rel + 0.40*qual + 0.25*trust",
            score_fn=_make_baseline_scorer(sq, rel_weight=0.35, qual_weight=0.40, trust_weight=0.25),
        ),
        ScoringVariation(
            name="j_lower_gate",
            description="Gate threshold lowered 0.42 -> 0.38",
            score_fn=_make_baseline_scorer(sq),
            note_threshold=0.38,
        ),
        ScoringVariation(
            name="k_higher_gate",
            description="Gate threshold raised 0.42 -> 0.48",
            score_fn=_make_baseline_scorer(sq),
            note_threshold=0.48,
        ),
        ScoringVariation(
            name="l_combined_feedback_relevance",
            description="COMBINED: feedback loop + category boost + relevance-heavy (0.55/0.25/0.20)",
            score_fn=_make_baseline_scorer(
                sq, rel_weight=0.55, qual_weight=0.25, trust_weight=0.20,
                feedback_enabled=True, category_boost_enabled=True,
            ),
        ),
        ScoringVariation(
            name="m_combined_feedback_quality",
            description="COMBINED: feedback loop + category boost + quality-heavy (0.35/0.40/0.25)",
            score_fn=_make_baseline_scorer(
                sq, rel_weight=0.35, qual_weight=0.40, trust_weight=0.25,
                feedback_enabled=True, category_boost_enabled=True,
            ),
        ),
        ScoringVariation(
            name="n_combined_best_candidate",
            description="COMBINED: feedback + relevance-heavy + bank=0.30 + gate=0.38",
            score_fn=_make_baseline_scorer(
                sq_bank30, rel_weight=0.55, qual_weight=0.25, trust_weight=0.20,
                feedback_enabled=True, category_boost_enabled=True,
            ),
            note_threshold=0.38,
        ),
    ]


# --------------- Metrics ---------------

def compute_metrics(
    cases: List[AdviceCase],
    var: ScoringVariation,
) -> VariationResult:
    """Score all cases and compute comprehensive metrics."""
    result = VariationResult(name=var.name, description=var.description)

    # Score each case
    scored = []
    for case in cases:
        s = var.score_fn(case)
        scored.append({
            "case_id": case.case_id,
            "tool": case.tool,
            "source": case.source,
            "useful": case.useful,
            "score": s,
            "text_preview": case.text[:80],
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    result.scored_items = scored

    # Precision@K
    for k, attr in [(1, "precision_at_1"), (2, "precision_at_2"),
                     (4, "precision_at_4"), (8, "precision_at_8")]:
        top_k = scored[:k]
        if top_k:
            setattr(result, attr, sum(1 for x in top_k if x["useful"]) / len(top_k))

    # Items above thresholds
    above_min = [x for x in scored if x["score"] >= var.min_rank_score]
    above_gate = [x for x in scored if x["score"] >= var.note_threshold]
    result.total_above_min = len(above_min)

    useful_total = sum(1 for c in cases if c.useful)
    useful_above_gate = sum(1 for x in above_gate if x["useful"])
    noise_above_gate = sum(1 for x in above_gate if not x["useful"])
    result.useful_above_gate = useful_above_gate
    result.noise_above_gate = noise_above_gate

    # Recall: fraction of useful items above gate threshold
    result.recall = useful_above_gate / max(1, useful_total)

    # Noise Rate: fraction of items above gate that are noise
    total_above_gate = len(above_gate)
    result.noise_rate = noise_above_gate / max(1, total_above_gate) if total_above_gate else 0.0

    # Score gaps
    useful_scores = [x["score"] for x in scored if x["useful"]]
    noise_scores = [x["score"] for x in scored if not x["useful"]]
    result.mean_useful_score = sum(useful_scores) / max(1, len(useful_scores))
    result.mean_noise_score = sum(noise_scores) / max(1, len(noise_scores))
    result.score_gap = result.mean_useful_score - result.mean_noise_score

    # Per-source breakdown
    by_source: Dict[str, Dict[str, list]] = {}
    for item in scored:
        src = item["source"]
        if src not in by_source:
            by_source[src] = {"useful_scores": [], "noise_scores": []}
        if item["useful"]:
            by_source[src]["useful_scores"].append(item["score"])
        else:
            by_source[src]["noise_scores"].append(item["score"])

    for src, data in by_source.items():
        us = data["useful_scores"]
        ns = data["noise_scores"]
        u_above = sum(1 for s in us if s >= var.note_threshold)
        n_above = sum(1 for s in ns if s >= var.note_threshold)
        result.per_source[src] = {
            "useful_count": len(us),
            "noise_count": len(ns),
            "mean_useful": round(sum(us) / max(1, len(us)), 4),
            "mean_noise": round(sum(ns) / max(1, len(ns)), 4),
            "useful_above_gate": u_above,
            "noise_above_gate": n_above,
            "precision": round(u_above / max(1, u_above + n_above), 4) if (u_above + n_above) else 0.0,
        }

    # Per-tool breakdown
    by_tool: Dict[str, Dict[str, list]] = {}
    for item in scored:
        t = item["tool"]
        if t not in by_tool:
            by_tool[t] = {"useful_scores": [], "noise_scores": []}
        if item["useful"]:
            by_tool[t]["useful_scores"].append(item["score"])
        else:
            by_tool[t]["noise_scores"].append(item["score"])

    for tool, data in by_tool.items():
        us = data["useful_scores"]
        ns = data["noise_scores"]
        u_above = sum(1 for s in us if s >= var.note_threshold)
        n_above = sum(1 for s in ns if s >= var.note_threshold)
        result.per_tool[tool] = {
            "useful_count": len(us),
            "noise_count": len(ns),
            "mean_useful": round(sum(us) / max(1, len(us)), 4),
            "mean_noise": round(sum(ns) / max(1, len(ns)), 4),
            "useful_above_gate": u_above,
            "noise_above_gate": n_above,
            "precision": round(u_above / max(1, u_above + n_above), 4) if (u_above + n_above) else 0.0,
        }

    return result


# --------------- Output ---------------

def generate_markdown_report(results: List[VariationResult], cases: List[AdviceCase]) -> str:
    """Generate comprehensive markdown report."""
    lines = []
    lines.append("# Advisory Scoring Benchmark Results")
    lines.append(f"\nRun: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Cases: {len(cases)} ({sum(1 for c in cases if c.useful)} useful, {sum(1 for c in cases if not c.useful)} noise)")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Variation | P@1 | P@2 | P@4 | Recall | Noise Rate | Score Gap | Above Gate (U/N) |")
    lines.append("|-----------|-----|-----|-----|--------|-----------|-----------|------------------|")
    for r in results:
        lines.append(
            f"| {r.name} | {r.precision_at_1:.0%} | {r.precision_at_2:.0%} | {r.precision_at_4:.0%} "
            f"| {r.recall:.0%} | {r.noise_rate:.0%} | {r.score_gap:+.3f} "
            f"| {r.useful_above_gate}/{r.noise_above_gate} |"
        )

    # Ranking by composite score (P@2 * Recall * (1-NoiseRate))
    lines.append("")
    lines.append("## Composite Ranking")
    lines.append("Formula: `P@2 * Recall * (1 - NoiseRate)` (higher = better)")
    lines.append("")
    ranked = sorted(results, key=lambda r: r.precision_at_2 * r.recall * (1 - r.noise_rate), reverse=True)
    for i, r in enumerate(ranked, 1):
        composite = r.precision_at_2 * r.recall * (1 - r.noise_rate)
        lines.append(f"{i}. **{r.name}** ({composite:.4f}) — {r.description}")

    # Per-source breakdown for top 3
    lines.append("")
    lines.append("## Per-Source Breakdown (Top 3 Variations)")
    for r in ranked[:3]:
        lines.append(f"\n### {r.name}")
        lines.append("| Source | Useful | Noise | Mean U | Mean N | U>Gate | N>Gate | Precision |")
        lines.append("|--------|--------|-------|--------|--------|--------|--------|-----------|")
        for src, data in sorted(r.per_source.items()):
            lines.append(
                f"| {src} | {data['useful_count']} | {data['noise_count']} "
                f"| {data['mean_useful']:.3f} | {data['mean_noise']:.3f} "
                f"| {data['useful_above_gate']} | {data['noise_above_gate']} "
                f"| {data['precision']:.0%} |"
            )

    # Per-tool breakdown for winner
    winner = ranked[0]
    lines.append(f"\n## Per-Tool Breakdown (Winner: {winner.name})")
    lines.append("| Tool | Useful | Noise | Mean U | Mean N | U>Gate | N>Gate | Precision |")
    lines.append("|------|--------|-------|--------|--------|--------|--------|-----------|")
    for tool, data in sorted(winner.per_tool.items()):
        lines.append(
            f"| {tool} | {data['useful_count']} | {data['noise_count']} "
            f"| {data['mean_useful']:.3f} | {data['mean_noise']:.3f} "
            f"| {data['useful_above_gate']} | {data['noise_above_gate']} "
            f"| {data['precision']:.0%} |"
        )

    # Top-10 and bottom-10 for winner
    lines.append(f"\n## Score Distribution (Winner: {winner.name})")
    lines.append("\n### Top 10 Scored Items")
    lines.append("| Rank | Score | Useful | Source | Text |")
    lines.append("|------|-------|--------|--------|------|")
    for i, item in enumerate(winner.scored_items[:10], 1):
        label = "YES" if item["useful"] else "no"
        lines.append(f"| {i} | {item['score']:.4f} | {label} | {item['source']} | {item['text_preview']} |")

    lines.append("\n### Bottom 10 Scored Items")
    lines.append("| Rank | Score | Useful | Source | Text |")
    lines.append("|------|-------|--------|--------|------|")
    for i, item in enumerate(winner.scored_items[-10:], len(winner.scored_items) - 9):
        label = "YES" if item["useful"] else "no"
        lines.append(f"| {i} | {item['score']:.4f} | {label} | {item['source']} | {item['text_preview']} |")

    # Variation descriptions
    lines.append("\n## Variation Descriptions")
    for r in results:
        lines.append(f"- **{r.name}**: {r.description}")

    return "\n".join(lines)


# --------------- Main ---------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Advisory scoring benchmark")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "benchmarks" / "results"),
                        help="Output directory for results")
    parser.add_argument("--json", action="store_true", help="Also output raw JSON")
    args = parser.parse_args()

    # Load ground truth
    if not GROUND_TRUTH_FILE.exists():
        print(f"ERROR: Ground truth not found at {GROUND_TRUTH_FILE}")
        sys.exit(1)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases = [
        AdviceCase(**{k: v for k, v in c.items() if k != "case_id" and k in AdviceCase.__dataclass_fields__},
                   case_id=c["case_id"])
        for c in data["cases"]
    ]
    print(f"Loaded {len(cases)} cases ({sum(1 for c in cases if c.useful)} useful, {sum(1 for c in cases if not c.useful)} noise)")

    # Build variations
    variations = build_variations()
    print(f"Testing {len(variations)} scoring variations...\n")

    # Run benchmark
    results = []
    for var in variations:
        result = compute_metrics(cases, var)
        results.append(result)
        composite = result.precision_at_2 * result.recall * (1 - result.noise_rate)
        print(f"  {var.name:40s}  P@2={result.precision_at_2:.0%}  Recall={result.recall:.0%}  "
              f"Noise={result.noise_rate:.0%}  Gap={result.score_gap:+.3f}  Composite={composite:.4f}")

    # Generate output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Markdown report
    md_path = output_dir / f"scoring_benchmark_{timestamp}.md"
    report = generate_markdown_report(results, cases)
    md_path.write_text(report, encoding="utf-8")
    print(f"\nReport: {md_path}")

    # JSON results (optional)
    if args.json:
        json_path = output_dir / f"scoring_benchmark_{timestamp}.json"
        json_data = {
            "timestamp": timestamp,
            "case_count": len(cases),
            "useful_count": sum(1 for c in cases if c.useful),
            "noise_count": sum(1 for c in cases if not c.useful),
            "variations": [
                {
                    "name": r.name,
                    "description": r.description,
                    "precision_at_1": r.precision_at_1,
                    "precision_at_2": r.precision_at_2,
                    "precision_at_4": r.precision_at_4,
                    "precision_at_8": r.precision_at_8,
                    "recall": r.recall,
                    "noise_rate": r.noise_rate,
                    "score_gap": r.score_gap,
                    "mean_useful_score": r.mean_useful_score,
                    "mean_noise_score": r.mean_noise_score,
                    "useful_above_gate": r.useful_above_gate,
                    "noise_above_gate": r.noise_above_gate,
                    "per_source": r.per_source,
                    "per_tool": r.per_tool,
                    "composite": round(r.precision_at_2 * r.recall * (1 - r.noise_rate), 6),
                }
                for r in results
            ],
        }
        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON:   {json_path}")

    # Print winner
    ranked = sorted(results, key=lambda r: r.precision_at_2 * r.recall * (1 - r.noise_rate), reverse=True)
    print(f"\n{'='*60}")
    print(f"WINNER: {ranked[0].name}")
    print(f"  {ranked[0].description}")
    composite = ranked[0].precision_at_2 * ranked[0].recall * (1 - ranked[0].noise_rate)
    print(f"  Composite={composite:.4f}  P@2={ranked[0].precision_at_2:.0%}  "
          f"Recall={ranked[0].recall:.0%}  Noise={ranked[0].noise_rate:.0%}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
