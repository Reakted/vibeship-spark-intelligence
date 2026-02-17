#!/usr/bin/env python3
"""Benchmark gate for emotion-aware memory retrieval reranking."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmarks.memory_retrieval_ab import EvalCase, retrieve_hybrid


@dataclass
class _SyntheticInsight:
    insight: str
    reliability: float
    meta: Dict[str, Any]


class _SyntheticRetriever:
    def __init__(self, candidates_by_case: Dict[str, List[str]], insights: Dict[str, _SyntheticInsight]):
        self._candidates_by_case = candidates_by_case
        self._insights = insights

    def retrieve(self, query: str, _insights: Dict[str, Any], limit: int = 8):
        keys = self._candidates_by_case.get(query, [])
        rows = []
        for key in keys[:limit]:
            ins = self._insights.get(key)
            if not ins:
                continue
            rows.append(
                SimpleNamespace(
                    insight_key=key,
                    insight_text=ins.insight,
                    semantic_sim=0.72,
                    trigger_conf=0.0,
                    fusion_score=0.72,
                    source_type="semantic",
                    why="synthetic",
                )
            )
        return rows


def _build_synthetic_suite() -> tuple[Dict[str, _SyntheticInsight], List[EvalCase], Dict[str, List[str]]]:
    insights: Dict[str, _SyntheticInsight] = {
        "calm_plan": _SyntheticInsight(
            insight="Use a staged rollout checklist with fallback.",
            reliability=0.6,
            meta={"emotion": {"primary_emotion": "steady", "mode": "calm_focus", "strain": 0.18, "calm": 0.84}},
        ),
        "stress_fix": _SyntheticInsight(
            insight="Use rollback-first stabilization when deploy risk is high.",
            reliability=0.6,
            meta={"emotion": {"primary_emotion": "careful", "mode": "real_talk", "strain": 0.84, "calm": 0.58}},
        ),
        "neutral_scale": _SyntheticInsight(
            insight="Expand to adjacent domains in controlled batches.",
            reliability=0.6,
            meta={"emotion": {"primary_emotion": "steady", "mode": "real_talk", "strain": 0.24, "energy": 0.52}},
        ),
        "celebrate_expand": _SyntheticInsight(
            insight="When momentum is high, capture wins and scale follow-up actions.",
            reliability=0.6,
            meta={"emotion": {"primary_emotion": "encouraged", "mode": "spark_alive", "strain": 0.22, "energy": 0.81}},
        ),
        "supportive_focus": _SyntheticInsight(
            insight="When user frustration is high, switch to stepwise recovery guidance.",
            reliability=0.6,
            meta={"emotion": {"primary_emotion": "supportive_focus", "mode": "real_talk", "strain": 0.72, "calm": 0.76}},
        ),
    }

    cases = [
        EvalCase(
            case_id="high_strain_rollback",
            query="rollback deploy failure quickly",
            relevant_insight_keys=["stress_fix"],
            emotion_state={"primary_emotion": "careful", "mode": "real_talk", "strain": 0.82, "calm": 0.60},
        ),
        EvalCase(
            case_id="calm_planning",
            query="plan staged rollout with fallback",
            relevant_insight_keys=["calm_plan"],
            emotion_state={"primary_emotion": "steady", "mode": "calm_focus", "strain": 0.20, "calm": 0.86},
        ),
        EvalCase(
            case_id="positive_momentum_scale",
            query="scale after success and momentum",
            relevant_insight_keys=["celebrate_expand"],
            emotion_state={"primary_emotion": "encouraged", "mode": "spark_alive", "strain": 0.24, "energy": 0.82},
        ),
        EvalCase(
            case_id="user_frustration_recovery",
            query="user is frustrated during debugging support",
            relevant_insight_keys=["supportive_focus"],
            emotion_state={"primary_emotion": "supportive_focus", "mode": "real_talk", "strain": 0.75, "calm": 0.74},
        ),
    ]

    candidates_by_case = {
        "rollback deploy failure quickly": ["calm_plan", "stress_fix"],
        "plan staged rollout with fallback": ["calm_plan", "stress_fix"],
        "scale after success and momentum": ["neutral_scale", "celebrate_expand"],
        "user is frustrated during debugging support": ["calm_plan", "supportive_focus"],
    }
    return insights, cases, candidates_by_case


def _score_cases(
    *,
    cases: List[EvalCase],
    insights: Dict[str, _SyntheticInsight],
    retriever: _SyntheticRetriever,
    emotion_state_weight: float,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    hits = 0
    for case in cases:
        result = retrieve_hybrid(
            retriever=retriever,
            insights=insights,
            query=case.query,
            top_k=1,
            candidate_k=8,
            lexical_weight=0.0,
            intent_coverage_weight=0.0,
            support_boost_weight=0.0,
            reliability_weight=0.0,
            emotion_state_weight=emotion_state_weight,
            semantic_intent_min=0.0,
            strict_filter=False,
            agentic=False,
            emotion_state=case.emotion_state,
        )
        top_key = result[0].insight_key if result else None
        hit = bool(top_key and top_key in set(case.relevant_insight_keys))
        if hit:
            hits += 1
        rows.append(
            {
                "case_id": case.case_id,
                "query": case.query,
                "expected": list(case.relevant_insight_keys),
                "top_key": top_key,
                "top_score": float(result[0].score) if result else 0.0,
                "hit_top1": hit,
            }
        )
    top1 = hits / max(1, len(cases))
    return {"top1_hit_rate": round(float(top1), 4), "hits": hits, "total": len(cases), "rows": rows}


def run_benchmark(
    *,
    emotion_state_weight: float = 0.45,
    min_top1_hit_rate: float = 0.75,
    min_uplift: float = 0.25,
) -> Dict[str, Any]:
    insights, cases, candidates_by_case = _build_synthetic_suite()
    retriever = _SyntheticRetriever(candidates_by_case=candidates_by_case, insights=insights)

    baseline = _score_cases(cases=cases, insights=insights, retriever=retriever, emotion_state_weight=0.0)
    emotion_on = _score_cases(
        cases=cases,
        insights=insights,
        retriever=retriever,
        emotion_state_weight=max(0.0, float(emotion_state_weight)),
    )

    uplift = round(float(emotion_on["top1_hit_rate"] - baseline["top1_hit_rate"]), 4)
    passed = bool(
        emotion_on["top1_hit_rate"] >= float(min_top1_hit_rate)
        and uplift >= float(min_uplift)
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "emotion_state_weight": float(emotion_state_weight),
            "min_top1_hit_rate": float(min_top1_hit_rate),
            "min_uplift": float(min_uplift),
        },
        "baseline": baseline,
        "emotion_enabled": emotion_on,
        "gates": {
            "uplift": uplift,
            "passed": passed,
        },
    }


def _write_report(report: Dict[str, Any], *, out_dir: Path, out_prefix: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{out_prefix}.json"
    md_path = out_dir / f"{out_prefix}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines: List[str] = [
        "# Emotion Memory Alignment Benchmark",
        "",
        f"- Timestamp: `{report['timestamp_utc']}`",
        f"- Emotion Weight: `{report['config']['emotion_state_weight']}`",
        f"- Baseline Top1: `{report['baseline']['top1_hit_rate']}`",
        f"- Emotion Top1: `{report['emotion_enabled']['top1_hit_rate']}`",
        f"- Uplift: `{report['gates']['uplift']}`",
        f"- Gates Passed: `{report['gates']['passed']}`",
        "",
        "## Case Results",
    ]
    for row in report["emotion_enabled"]["rows"]:
        lines.append(
            f"- `{row['case_id']}` expected={row['expected']} top={row['top_key']} hit={row['hit_top1']}"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Emotion-memory retrieval alignment benchmark gate")
    parser.add_argument("--emotion-state-weight", type=float, default=0.45, help="Weight for emotion state reranking")
    parser.add_argument("--min-top1-hit-rate", type=float, default=0.75, help="Gate: minimum top1 hit rate")
    parser.add_argument("--min-uplift", type=float, default=0.25, help="Gate: minimum top1 uplift over baseline")
    parser.add_argument("--out-dir", default=str(Path("benchmarks") / "out"), help="Output directory")
    parser.add_argument("--out-prefix", default="emotion_memory_alignment_bench", help="Output file prefix")
    args = parser.parse_args()

    report = run_benchmark(
        emotion_state_weight=float(args.emotion_state_weight),
        min_top1_hit_rate=float(args.min_top1_hit_rate),
        min_uplift=float(args.min_uplift),
    )
    out_json, out_md = _write_report(report, out_dir=Path(args.out_dir), out_prefix=str(args.out_prefix))
    print(f"[emotion-bench] wrote {out_json}")
    print(f"[emotion-bench] wrote {out_md}")
    print(f"[emotion-bench] gates_passed={report['gates']['passed']}")
    return 0 if report["gates"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
