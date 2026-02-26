"""Observatory page: Recovery Effectiveness Metrics (Phase D2).

Reads workflow_summary reports and visualizes failure->recovery chains
broken down by provider and tool.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict


def generate_recovery_metrics(data: Dict[int, Any] | None = None) -> str:
    """Generate the recovery effectiveness observatory page."""
    try:
        from ..workflow_evidence import compute_recovery_metrics, get_all_recent_summaries
    except ImportError:
        return _empty_page("Import failed — workflow_evidence module not available")

    try:
        summaries = get_all_recent_summaries(max_age_s=86400)
        metrics = compute_recovery_metrics(summaries)
    except Exception as exc:
        return _empty_page(f"Error computing metrics: {exc}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = metrics.get("total_sessions", 0)
    failures = metrics.get("sessions_with_failures", 0)
    recoveries = metrics.get("sessions_with_recovery", 0)
    rate = metrics.get("recovery_rate", 0.0)

    lines = [
        "---",
        "tags: [observatory, recovery, metrics, phase-d]",
        "---",
        "# Recovery Effectiveness",
        "",
        f"> Auto-generated {now_str} | [[flow|Dashboard]] | [[advisory_reverse_engineering|Advisory]]",
        "",
        "## Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total sessions (24h) | {total} |",
        f"| Sessions with failures | {failures} |",
        f"| Sessions with recovery | {recoveries} |",
        f"| **Recovery rate** | **{rate:.1%}** |",
        f"| Summaries scanned | {len(summaries)} |",
        "",
    ]

    # Per-provider breakdown
    per_provider = metrics.get("per_provider", {})
    if per_provider:
        lines.append("## By Provider")
        lines.append("")
        lines.append("| Provider | Sessions | Failures | Recoveries | Rate |")
        lines.append("|----------|----------|----------|------------|------|")
        for prov, stats in sorted(per_provider.items()):
            s = stats.get("sessions", 0)
            f = stats.get("failures", 0)
            r = stats.get("recoveries", 0)
            rt = stats.get("rate", 0.0)
            lines.append(f"| {prov} | {s} | {f} | {r} | {rt:.1%} |")
        lines.append("")

    # Per-tool breakdown
    per_tool = metrics.get("per_tool", {})
    if per_tool:
        lines.append("## By Tool (recovered)")
        lines.append("")
        lines.append("| Tool | Failures | Recoveries | Rate |")
        lines.append("|------|----------|------------|------|")
        for tool, stats in sorted(per_tool.items(), key=lambda x: x[1].get("recoveries_total", 0), reverse=True):
            f = stats.get("failures_total", 0)
            r = stats.get("recoveries_total", 0)
            rt = stats.get("rate", 0.0)
            lines.append(f"| `{tool}` | {f} | {r} | {rt:.1%} |")
        lines.append("")

    # Recent summaries sample
    if summaries:
        lines.append("## Recent Summaries (last 5)")
        lines.append("")
        lines.append("| Time | Provider | Tools | Successes | Failures | Recovery Tools |")
        lines.append("|------|----------|-------|-----------|----------|----------------|")
        for s in summaries[:5]:
            ts = float(s.get("ts") or 0)
            ts_str = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "?"
            prov = s.get("provider", "?")
            tools = int(s.get("tool_calls") or 0)
            succ = int(s.get("tool_successes") or 0)
            fail = int(s.get("tool_failures") or 0)
            rec = ", ".join(s.get("recovery_tools") or []) or "-"
            lines.append(f"| {ts_str} | {prov} | {tools} | {succ} | {fail} | {rec} |")
        lines.append("")

    if not summaries:
        lines.append("> No workflow summaries found in the last 24 hours.")
        lines.append("> Ensure workflow_summary is enabled in openclaw_tailer/codex_hook_bridge/observe.py.")
        lines.append("")

    return "\n".join(lines)


def _empty_page(reason: str) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        "---\ntags: [observatory, recovery, metrics]\n---\n"
        f"# Recovery Effectiveness\n\n"
        f"> Auto-generated {now_str}\n\n"
        f"No data available: {reason}\n"
    )
