#!/usr/bin/env python3
"""Run memory retrieval A/B benchmark across per-domain slices with gates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmarks import memory_retrieval_ab as mra
from lib.cognitive_learner import get_cognitive_learner
from lib.semantic_retriever import SemanticRetriever


DEFAULT_CASES = Path("benchmarks") / "data" / "memory_retrieval_eval_live_2026_02_12.json"
DEFAULT_OUT_PREFIX = "memory_retrieval_domain_matrix"
DEFAULT_GATE_TEMPLATE: Dict[str, float] = {
    "mrr_min": 0.35,
    "top1_hit_rate_min": 0.20,
    "non_empty_rate_min": 0.55,
    "error_rate_max": 0.10,
}
DEFAULT_DOMAIN_GATE_OVERRIDES: Dict[str, Dict[str, float]] = {
    "memory": {"mrr_min": 0.42, "top1_hit_rate_min": 0.25},
    "coding": {"mrr_min": 0.40, "top1_hit_rate_min": 0.24},
    "testing": {"mrr_min": 0.38, "top1_hit_rate_min": 0.22},
    "x_social": {"mrr_min": 0.30, "top1_hit_rate_min": 0.15},
    "general": {"mrr_min": 0.30, "top1_hit_rate_min": 0.15},
}
DOMAIN_MARKERS: Dict[str, Tuple[str, ...]] = {
    "x_social": (
        "x_social",
        "x-social",
        "twitter",
        "tweet",
        "retweet",
        "quote tweet",
        "timeline",
        "engagement",
        "multiplier granted",
        "cryptographic proof",
    ),
    "memory": (
        "memory",
        "retrieval",
        "distillation",
        "cross-session",
        "stale",
        "session",
        "insight",
        "index",
    ),
    "testing": (
        "pytest",
        "unit test",
        "integration test",
        "regression",
        "coverage",
        "assert",
    ),
    "coding": (
        "code",
        "coding",
        "debug",
        "refactor",
        "function",
        "module",
        "python",
        "typescript",
        "javascript",
        "traceback",
        "stack trace",
    ),
    "marketing": (
        "marketing",
        "campaign",
        "conversion",
        "audience",
        "brand",
        "growth",
        "positioning",
        "launch",
    ),
    "strategy": (
        "strategy",
        "roadmap",
        "tradeoff",
        "prioritize",
        "risk",
        "moat",
    ),
    "ui_design": (
        "ui",
        "ux",
        "layout",
        "visual",
        "design",
        "typography",
        "mobile",
        "desktop",
    ),
    "research": (
        "research",
        "analysis",
        "compare",
        "evaluate",
        "evidence",
        "paper",
        "benchmark",
    ),
    "conversation": (
        "coach",
        "coaching",
        "advice",
        "self-improvement",
        "mindset",
        "reflection",
        "feedback",
    ),
    "prompting": (
        "prompt",
        "system prompt",
        "few-shot",
        "instruction",
        "token budget",
    ),
}


@dataclass
class DomainCase:
    domain: str
    case: mra.EvalCase


@dataclass
class DomainGateResult:
    gate_values: Dict[str, float]
    checks: Dict[str, bool]
    all_pass: bool


def _norm_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "general"
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    aliases = {
        "x": "x_social",
        "social": "x_social",
        "social_media": "x_social",
        "ui": "ui_design",
        "ux": "ui_design",
    }
    if not text:
        return "general"
    return aliases.get(text, text)


def infer_domain(*, query: str, notes: str = "") -> str:
    text = f"{query} {notes}".strip().lower()
    if not text:
        return "general"
    for domain, markers in DOMAIN_MARKERS.items():
        if any(marker in text for marker in markers):
            return domain
    return "general"


def _load_raw_rows(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("cases") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("cases file must be a list or an object with a 'cases' list")
    return [row for row in rows if isinstance(row, dict)]


def load_cases_with_domains(path: Path) -> List[DomainCase]:
    rows = _load_raw_rows(path)
    out: List[DomainCase] = []
    for idx, row in enumerate(rows):
        case_id = str(row.get("id") or row.get("case_id") or f"case_{idx + 1}")
        query = str(row.get("query") or "").strip()
        if not query:
            continue
        keys = [str(v).strip() for v in (row.get("relevant_insight_keys") or []) if str(v).strip()]
        contains = [str(v).strip().lower() for v in (row.get("relevant_contains") or []) if str(v).strip()]
        notes = str(row.get("notes") or "")
        domain = _norm_domain(row.get("domain") or infer_domain(query=query, notes=notes))
        out.append(
            DomainCase(
                domain=domain,
                case=mra.EvalCase(
                    case_id=case_id,
                    query=query,
                    relevant_insight_keys=keys,
                    relevant_contains=contains,
                    notes=notes,
                ),
            )
        )
    return out


def group_cases(
    rows: Sequence[DomainCase],
    *,
    min_cases: int,
    allow_domains: Optional[set[str]],
) -> Dict[str, List[mra.EvalCase]]:
    grouped: Dict[str, List[mra.EvalCase]] = {}
    for row in rows:
        domain = _norm_domain(row.domain)
        if allow_domains is not None and domain not in allow_domains:
            continue
        grouped.setdefault(domain, []).append(row.case)
    return {k: v for k, v in grouped.items() if len(v) >= max(1, int(min_cases))}


def _summary_rank(row: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (
        float(row.get("mrr") if row.get("mrr") is not None else -1.0),
        float(row.get("precision_at_k") if row.get("precision_at_k") is not None else -1.0),
        1.0 - float(row.get("error_rate") or 0.0),
        -float(row.get("latency_ms_p95") or 0.0),
    )


def resolve_gates(domain: str, gate_file: str = "") -> Dict[str, float]:
    gate_values = dict(DEFAULT_GATE_TEMPLATE)
    gate_values.update(DEFAULT_DOMAIN_GATE_OVERRIDES.get(_norm_domain(domain), {}))
    if not gate_file:
        return gate_values
    loaded = json.loads(Path(gate_file).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return gate_values
    default_loaded = loaded.get("default")
    if isinstance(default_loaded, dict):
        gate_values.update({str(k): float(v) for k, v in default_loaded.items()})
    domain_loaded = loaded.get(_norm_domain(domain))
    if isinstance(domain_loaded, dict):
        gate_values.update({str(k): float(v) for k, v in domain_loaded.items()})
    return gate_values


def evaluate_domain_gates(summary: Dict[str, Any], gate_values: Dict[str, float]) -> DomainGateResult:
    mrr = summary.get("mrr")
    top1 = summary.get("top1_hit_rate")
    non_empty = float(summary.get("non_empty_rate") or 0.0)
    error_rate = float(summary.get("error_rate") or 0.0)

    checks = {
        "mrr_min": bool(mrr is not None and float(mrr) >= float(gate_values.get("mrr_min", 0.0))),
        "top1_hit_rate_min": bool(
            top1 is not None and float(top1) >= float(gate_values.get("top1_hit_rate_min", 0.0))
        ),
        "non_empty_rate_min": bool(non_empty >= float(gate_values.get("non_empty_rate_min", 0.0))),
        "error_rate_max": bool(error_rate <= float(gate_values.get("error_rate_max", 1.0))),
    }
    return DomainGateResult(gate_values=gate_values, checks=checks, all_pass=all(checks.values()))


def _weighted_avg(rows: Iterable[Dict[str, Any]], key: str) -> float:
    numer = 0.0
    denom = 0
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        weight = max(1, int(row.get("case_count") or 1))
        numer += float(value) * weight
        denom += weight
    if denom <= 0:
        return 0.0
    return round(numer / denom, 4)


def _report_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Memory Retrieval Domain Matrix")
    lines.append("")
    lines.append(f"- Timestamp (UTC): `{report.get('generated_at', '')}`")
    lines.append(f"- Cases file: `{report.get('cases_path', '')}`")
    lines.append(f"- Domains: `{report.get('domain_count', 0)}`")
    lines.append(f"- Cases: `{report.get('case_count', 0)}`")
    lines.append(f"- Systems: `{', '.join(report.get('systems') or [])}`")
    lines.append("")
    lines.append(
        "| Domain | Cases | Winner | MRR | Top1 | Non-empty | Error | Gate |"
    )
    lines.append("|---|---:|---|---:|---:|---:|---:|---|")
    for row in report.get("domains") or []:
        mrr = "-" if row.get("mrr") is None else f"{float(row.get('mrr')):.3f}"
        top1 = "-" if row.get("top1_hit_rate") is None else f"{float(row.get('top1_hit_rate')):.3f}"
        gate_state = "PASS" if bool(row.get("all_gates_pass")) else "FAIL"
        lines.append(
            f"| `{row.get('domain','')}` | {int(row.get('case_count', 0))} | "
            f"`{row.get('winner','')}` | {mrr} | {top1} | "
            f"{float(row.get('non_empty_rate', 0.0)):.3f} | {float(row.get('error_rate', 0.0)):.3f} | {gate_state} |"
        )
    lines.append("")
    weighted = report.get("weighted") or {}
    lines.append("## Weighted Summary")
    lines.append("")
    lines.append(f"- MRR: `{float(weighted.get('mrr', 0.0)):.4f}`")
    lines.append(f"- Top1 hit rate: `{float(weighted.get('top1_hit_rate', 0.0)):.4f}`")
    lines.append(f"- Non-empty rate: `{float(weighted.get('non_empty_rate', 0.0)):.4f}`")
    lines.append(f"- Error rate: `{float(weighted.get('error_rate', 0.0)):.4f}`")
    lines.append(f"- Domain gate pass rate: `{float(weighted.get('domain_gate_pass_rate', 0.0)):.2%}`")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_domains(raw: str) -> Optional[set[str]]:
    parts = {_norm_domain(p) for p in str(raw or "").split(",") if str(p).strip()}
    return parts or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Memory retrieval A/B matrix by domain with gates")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to benchmark cases JSON")
    parser.add_argument(
        "--systems",
        default="embeddings_only,hybrid,hybrid_agentic",
        help=f"Comma-separated systems ({', '.join(mra.SUPPORTED_SYSTEMS)})",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--lexical-weight", type=float, default=0.35)
    parser.add_argument("--intent-coverage-weight", type=float, default=0.0)
    parser.add_argument("--support-boost-weight", type=float, default=0.0)
    parser.add_argument("--reliability-weight", type=float, default=0.0)
    parser.add_argument("--semantic-intent-min", type=float, default=0.0)
    parser.add_argument("--disable-strict-filter", action="store_true")
    parser.add_argument("--min-similarity", type=float, default=None)
    parser.add_argument("--min-fusion-score", type=float, default=None)
    parser.add_argument("--min-cases-per-domain", type=int, default=2)
    parser.add_argument("--domains", default="", help="Optional comma-separated domain allow-list")
    parser.add_argument("--gate-file", default="", help="Optional gate override JSON (default/domain keys)")
    parser.add_argument("--strict-labels", action="store_true")
    parser.add_argument("--case-limit", type=int, default=0)
    parser.add_argument("--out-dir", default=str(Path("benchmarks") / "out"))
    parser.add_argument("--out-prefix", default=DEFAULT_OUT_PREFIX)
    args = parser.parse_args()

    systems = mra.parse_systems(args.systems)
    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"[matrix] missing cases file: {cases_path}")
        return 2
    rows = load_cases_with_domains(cases_path)
    if args.case_limit and args.case_limit > 0:
        rows = rows[: args.case_limit]
    allow_domains = parse_domains(args.domains)
    grouped = group_cases(rows, min_cases=max(1, int(args.min_cases_per_domain)), allow_domains=allow_domains)
    if not grouped:
        print("[matrix] no domains match selection/min-cases")
        return 2

    all_cases = [case for cases in grouped.values() for case in cases]
    unlabeled = [case.case_id for case in all_cases if not case.has_labels]
    if args.strict_labels and unlabeled:
        print(f"[matrix] strict labels enabled, unlabeled cases: {', '.join(unlabeled)}")
        return 2

    learner = get_cognitive_learner()
    insights = dict(getattr(learner, "insights", {}) or {})
    noise_filter = getattr(learner, "is_noise_insight", None)
    retriever = SemanticRetriever()
    retriever.config["triggers_enabled"] = False
    if args.min_similarity is not None:
        retriever.config["min_similarity"] = float(args.min_similarity)
    if args.min_fusion_score is not None:
        retriever.config["min_fusion_score"] = float(args.min_fusion_score)

    domain_reports: List[Dict[str, Any]] = []
    print("Memory Retrieval Domain Matrix")
    print(f"- cases: {cases_path}")
    for domain in sorted(grouped.keys()):
        print(f"  - {domain}: {len(grouped[domain])} cases")

    for domain in sorted(grouped.keys()):
        cases = grouped[domain]
        by_system: Dict[str, List[Dict[str, Any]]] = {system: [] for system in systems}
        for case in cases:
            for system in systems:
                by_system[system].append(
                    mra.run_system_for_case(
                        system=system,
                        case=case,
                        retriever=retriever,
                        insights=insights,
                        noise_filter=noise_filter,
                        top_k=max(1, int(args.top_k)),
                        candidate_k=max(1, int(args.candidate_k)),
                        lexical_weight=float(args.lexical_weight),
                        intent_coverage_weight=float(args.intent_coverage_weight),
                        support_boost_weight=float(args.support_boost_weight),
                        reliability_weight=float(args.reliability_weight),
                        semantic_intent_min=float(args.semantic_intent_min),
                        strict_filter=not bool(args.disable_strict_filter),
                    )
                )

        summaries = [mra.summarize_system(system, by_system[system]) for system in systems]
        winner = mra.pick_winner(summaries)
        ranked_summaries = sorted(summaries, key=_summary_rank, reverse=True)
        selected = ranked_summaries[0] if ranked_summaries else {}
        if winner not in {"tie", "none"}:
            explicit = next((row for row in summaries if row.get("system") == winner), None)
            if explicit is not None:
                selected = explicit

        gates = resolve_gates(domain, gate_file=str(args.gate_file or ""))
        gate_result = evaluate_domain_gates(selected, gates)
        domain_reports.append(
            {
                "domain": domain,
                "case_count": len(cases),
                "winner": winner,
                "winner_summary": selected,
                "mrr": selected.get("mrr"),
                "top1_hit_rate": selected.get("top1_hit_rate"),
                "non_empty_rate": float(selected.get("non_empty_rate") or 0.0),
                "error_rate": float(selected.get("error_rate") or 0.0),
                "gate_values": gate_result.gate_values,
                "gates": gate_result.checks,
                "all_gates_pass": gate_result.all_pass,
                "summaries": summaries,
            }
        )

    weighted = {
        "mrr": _weighted_avg(domain_reports, "mrr"),
        "top1_hit_rate": _weighted_avg(domain_reports, "top1_hit_rate"),
        "non_empty_rate": _weighted_avg(domain_reports, "non_empty_rate"),
        "error_rate": _weighted_avg(domain_reports, "error_rate"),
        "domain_gate_pass_rate": round(
            sum(1 for row in domain_reports if bool(row.get("all_gates_pass"))) / max(1, len(domain_reports)),
            4,
        ),
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases_path": str(cases_path),
        "systems": systems,
        "domain_count": len(domain_reports),
        "case_count": int(sum(int(row.get("case_count") or 0) for row in domain_reports)),
        "top_k": int(args.top_k),
        "candidate_k": int(args.candidate_k),
        "lexical_weight": float(args.lexical_weight),
        "intent_coverage_weight": float(args.intent_coverage_weight),
        "support_boost_weight": float(args.support_boost_weight),
        "reliability_weight": float(args.reliability_weight),
        "semantic_intent_min": float(args.semantic_intent_min),
        "strict_filter": not bool(args.disable_strict_filter),
        "min_similarity": retriever.config.get("min_similarity"),
        "min_fusion_score": retriever.config.get("min_fusion_score"),
        "weighted": weighted,
        "domains": domain_reports,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{args.out_prefix}_report.json"
    out_md = out_dir / f"{args.out_prefix}_report.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    out_md.write_text(_report_markdown(report), encoding="utf-8")

    print(f"[matrix] wrote {out_json}")
    print(f"[matrix] wrote {out_md}")
    print(
        "[matrix] weighted"
        f" mrr={weighted['mrr']:.3f}"
        f" top1={weighted['top1_hit_rate']:.3f}"
        f" non_empty={weighted['non_empty_rate']:.3f}"
        f" gate_pass={weighted['domain_gate_pass_rate']:.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
