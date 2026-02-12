#!/usr/bin/env python3
"""Print aligned Carmack KPI scorecard for recent Spark windows."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from lib.carmack_kpi import build_scorecard


def _fmt_ratio(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def _fmt_delta(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:+.1f}pp"


def _render_text(score: Dict[str, Any]) -> str:
    generated = datetime.fromtimestamp(float(score["generated_at"]), tz=timezone.utc).isoformat()
    rows = []
    rows.append(f"Carmack KPI Scorecard (generated {generated})")
    rows.append(f"Window: {score.get('window_hours')}h current vs previous")
    rows.append("")
    rows.append("KPI | Current | Previous | Delta | Trend")
    rows.append("--- | --- | --- | --- | ---")

    metrics = score.get("metrics") or {}
    gaur = metrics.get("gaur") or {}
    rows.append(
        "GAUR | "
        f"{_fmt_ratio(gaur.get('current'))} | {_fmt_ratio(gaur.get('previous'))} | "
        f"{_fmt_delta(gaur.get('delta'))} | {gaur.get('trend', 'unknown')}"
    )

    fb = metrics.get("fallback_burden") or {}
    rows.append(
        "Fallback Burden | "
        f"{_fmt_ratio(fb.get('current'))} | {_fmt_ratio(fb.get('previous'))} | "
        f"{_fmt_delta(fb.get('delta'))} | {fb.get('trend', 'unknown')}"
    )

    nb = metrics.get("noise_burden") or {}
    rows.append(
        "Noise Burden | "
        f"{_fmt_ratio(nb.get('current'))} | {_fmt_ratio(nb.get('previous'))} | "
        f"{_fmt_delta(nb.get('delta'))} | {nb.get('trend', 'unknown')}"
    )

    cr = metrics.get("core_reliability") or {}
    rows.append(
        "Core Reliability | "
        f"{_fmt_ratio(cr.get('current'))} | {_fmt_ratio(cr.get('previous'))} | "
        f"{_fmt_delta(cr.get('delta'))} | {cr.get('trend', 'unknown')}"
    )

    current = score.get("current") or {}
    rows.append("")
    rows.append(
        "Current window raw: "
        f"events={current.get('total_events', 0)}, delivered_calls={current.get('delivered', 0)}, "
        f"emitted_items={current.get('emitted_advice_items', 0)}, good_used={current.get('good_advice_used', 0)}"
    )
    core = score.get("core") or {}
    rows.append(
        f"Core services running: {core.get('core_running', 0)}/{core.get('core_total', 0)}"
    )
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute aligned Carmack KPI scorecard.")
    ap.add_argument("--window-hours", type=float, default=4.0, help="Window size in hours.")
    ap.add_argument("--json", action="store_true", help="Print JSON only.")
    args = ap.parse_args()

    score = build_scorecard(window_hours=args.window_hours)
    if args.json:
        print(json.dumps(score, indent=2))
        return 0

    print(_render_text(score))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
