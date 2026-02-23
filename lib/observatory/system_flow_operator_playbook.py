"""Generate an operator playbook for Spark intelligence flow diagnostics."""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import spark_dir

_SPARK_DIR = spark_dir()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return data if isinstance(data, dict) else {}


def _read_jsonl(path: Path, max_rows: int = 6000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except Exception:
        return []
    if max_rows > 0 and len(rows) > max_rows:
        rows = rows[-max_rows:]
    return rows


def _parse_ts(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except Exception:
            pass
        try:
            return float(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
        except Exception:
            return 0.0
    return 0.0


def _fmt_ts(ts: float) -> str:
    if ts <= 0:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _pct(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return 100.0 * float(part) / float(whole)


def _suppression_24h() -> Dict[str, Any]:
    rows = _read_jsonl(_SPARK_DIR / "advisory_decision_ledger.jsonl", max_rows=12000)
    cutoff = time.time() - 86400.0
    outcomes = Counter()
    buckets = Counter()
    reasons = Counter()
    latest_ts = 0.0

    for row in rows:
        ts = _parse_ts(row.get("ts"))
        if ts and ts < cutoff:
            continue
        latest_ts = max(latest_ts, ts)
        outcome = str(row.get("outcome") or "unknown").strip().lower() or "unknown"
        outcomes[outcome] += 1

        for item in row.get("suppressed_reasons") or []:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason") or "").strip()
            try:
                count = max(1, int(item.get("count") or 1))
            except Exception:
                count = 1
            if not reason:
                continue
            reasons[reason] += count
            low = reason.lower()
            if "shown " in low and "ttl" in low:
                buckets["shown_ttl"] += count
            elif "global_dedupe" in low:
                buckets["global_dedupe"] += count
            elif "budget exhausted" in low:
                buckets["budget_exhausted"] += count
            elif "on cooldown" in low:
                buckets["tool_cooldown"] += count
            elif "phase=" in low or "exploration phase" in low:
                buckets["context_phase_guard"] += count
            else:
                buckets["other"] += count

        for item in row.get("suppressed") or []:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason") or "").strip().lower()
            if reason in {"text_sig", "advice_id"}:
                buckets["global_dedupe"] += 1
                reasons[f"global_dedupe:{reason}"] += 1

    total = sum(int(v or 0) for v in buckets.values())
    emitted = int(outcomes.get("emitted", 0))
    blocked = int(outcomes.get("blocked", 0))
    return {
        "outcomes": dict(outcomes),
        "buckets": dict(buckets),
        "suppressed_total": total,
        "emit_rate": round(_pct(emitted, max(emitted + blocked, 1)), 1),
        "latest_ts": latest_ts,
        "top_reasons": reasons.most_common(8),
    }


def _feedback_24h() -> Dict[str, Any]:
    rows = _read_jsonl(_SPARK_DIR / "advisor" / "implicit_feedback.jsonl", max_rows=12000)
    cutoff = time.time() - 86400.0
    signals = Counter()
    latest_ts = 0.0
    latest_row: Dict[str, Any] = {}
    for row in rows:
        ts = _parse_ts(row.get("timestamp"))
        if ts and ts < cutoff:
            continue
        latest_ts = max(latest_ts, ts)
        if ts == latest_ts:
            latest_row = row
        signal = str(row.get("signal") or "unknown").strip().lower() or "unknown"
        signals[signal] += 1
    followed = int(signals.get("followed", 0) + signals.get("helpful", 0))
    not_followed = int(
        signals.get("ignored", 0)
        + signals.get("unhelpful", 0)
        + signals.get("not_followed", 0)
    )
    return {
        "rows": int(sum(signals.values())),
        "signals": dict(signals),
        "follow_rate": round(_pct(followed, max(followed + not_followed, 1)), 1),
        "latest_ts": latest_ts,
        "latest_row": latest_row,
    }


def _mind_status() -> Dict[str, Any]:
    hb = _read_json(_SPARK_DIR / "bridge_worker_heartbeat.json")
    ms = _read_json(_SPARK_DIR / "mind_sync_state.json")
    out: Dict[str, Any] = {}
    out["heartbeat_ts"] = _parse_ts(hb.get("ts")) if hb else 0.0
    if hb:
        stats = hb.get("stats")
        if isinstance(stats, dict):
            mind_sync = stats.get("mind_sync")
            if isinstance(mind_sync, dict):
                out["mind_sync"] = mind_sync
    hashes = ms.get("synced_hashes") if isinstance(ms.get("synced_hashes"), list) else []
    out["synced_hashes_count"] = len(hashes)
    out["mind_state_last_sync"] = _parse_ts(ms.get("last_sync")) if ms else 0.0
    return out


def _status_badge(ok: bool, warn: bool) -> str:
    if ok:
        return "OK"
    if warn:
        return "WARN"
    return "ALERT"


def generate_system_flow_operator_playbook(data: Dict[int, Dict[str, Any]]) -> str:
    """Generate operator playbook with checks, commands, and remediation."""
    suppression = _suppression_24h()
    feedback = _feedback_24h()
    mind = _mind_status()

    queue_pending = int((data.get(2) or {}).get("estimated_pending", 0) or 0)
    pipeline_ts = _parse_ts((data.get(3) or {}).get("last_cycle_ts"))
    pipeline_age_s = max(0.0, time.time() - pipeline_ts) if pipeline_ts > 0 else 10**9
    meta_pass = float((data.get(5) or {}).get("pass_rate", 0.0) or 0.0)
    emit_rate = float(suppression.get("emit_rate", 0.0) or 0.0)
    follow_rate = float(feedback.get("follow_rate", 0.0) or 0.0)
    shown_ttl_share = _pct(
        (suppression.get("buckets") or {}).get("shown_ttl", 0),
        max(int(suppression.get("suppressed_total", 0) or 0), 1),
    )

    checks = [
        {
            "name": "Queue backlog",
            "value": f"{queue_pending}",
            "threshold": "< 5000 healthy; >= 20000 critical",
            "status": _status_badge(queue_pending < 5000, queue_pending < 20000),
            "cmd": "python -c \"import lib.queue as q; print(q.get_queue_stats())\"",
            "immediate": "If critical, reduce producer noise and run bridge worker immediately.",
            "fix": "Tune capture filtering and queue overflow handling; confirm pipeline consumption pace.",
        },
        {
            "name": "Pipeline freshness",
            "value": f"{int(pipeline_age_s)}s since last cycle",
            "threshold": "<= 300s healthy; > 600s critical",
            "status": _status_badge(pipeline_age_s <= 300, pipeline_age_s <= 600),
            "cmd": "python -c \"import json, pathlib; p=pathlib.Path.home()/'.spark'/'pipeline_state.json'; print(json.loads(p.read_text()))\"",
            "immediate": "Restart/schedule bridge cycle and confirm no crash loop.",
            "fix": "Stabilize worker loop and add heartbeat alerting for stale cycles.",
        },
        {
            "name": "Meta-Ralph pass rate",
            "value": f"{meta_pass:.1f}%",
            "threshold": ">= 20% preferred",
            "status": _status_badge(meta_pass >= 30.0, meta_pass >= 15.0),
            "cmd": "python -c \"import json, pathlib; p=pathlib.Path.home()/'.spark'/'meta_ralph'/'roast_history.json'; d=json.loads(p.read_text()); print(d.get('quality_passed'), d.get('total_roasted'))\"",
            "immediate": "Sample recent rejects and verify if thresholding is too strict.",
            "fix": "Tune scoring thresholds or improve pre-gate signal extraction quality.",
        },
        {
            "name": "Advisory emit rate (24h)",
            "value": f"{emit_rate:.1f}%",
            "threshold": ">= 25% target band",
            "status": _status_badge(emit_rate >= 35.0, emit_rate >= 25.0),
            "cmd": "python -c \"import json, pathlib; p=pathlib.Path.home()/'.spark'/'advisory_decision_ledger.jsonl'; print('tail', len(p.read_text().splitlines()))\"",
            "immediate": "If low while follow-rate is high, relax suppression controls incrementally.",
            "fix": "Implement source/authority TTL policy and dynamic per-call budget.",
        },
        {
            "name": "Implicit follow rate (24h)",
            "value": f"{follow_rate:.1f}%",
            "threshold": ">= 40% minimum",
            "status": _status_badge(follow_rate >= 60.0, follow_rate >= 40.0),
            "cmd": "python -c \"import pathlib, json; p=pathlib.Path.home()/'.spark'/'advisor'/'implicit_feedback.jsonl'; rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]; print(len(rows))\"",
            "immediate": "If low, inspect last emitted advisories for relevance mismatch.",
            "fix": "Reweight sources, improve context matching, and tighten low-value emissions.",
        },
        {
            "name": "Shown TTL suppression share (24h)",
            "value": f"{shown_ttl_share:.1f}%",
            "threshold": "<= 50% preferred",
            "status": _status_badge(shown_ttl_share <= 40.0, shown_ttl_share <= 50.0),
            "cmd": "python scripts/generate_observatory.py --force",
            "immediate": "Lower category/source TTL where repeat suppression is over-aggressive.",
            "fix": "Ship source/authority-aware TTL tuneables and monitor before/after deltas.",
        },
        {
            "name": "Mind sync heartbeat",
            "value": _fmt_ts(float(mind.get("heartbeat_ts", 0.0) or 0.0)),
            "threshold": "Recent heartbeat (< 10m)",
            "status": _status_badge((time.time() - float(mind.get("heartbeat_ts", 0.0) or 0.0)) <= 600.0, (time.time() - float(mind.get("heartbeat_ts", 0.0) or 0.0)) <= 1200.0),
            "cmd": "python -c \"import json, pathlib; p=pathlib.Path.home()/'.spark'/'bridge_worker_heartbeat.json'; print(json.loads(p.read_text()).get('stats',{}).get('mind_sync'))\"",
            "immediate": "If stale, verify mind service and bridge worker are both running.",
            "fix": "Harden mind auth/service checks and queue drain behavior.",
        },
    ]

    lines: List[str] = []
    lines.append("---")
    lines.append("title: System Flow Operator Playbook")
    lines.append("tags:")
    lines.append("  - observatory")
    lines.append("  - operations")
    lines.append("  - runbook")
    lines.append("  - diagnostics")
    lines.append("---")
    lines.append("")
    lines.append("# Spark Flow Operator Playbook")
    lines.append("")
    lines.append(f"> Generated: {_fmt_ts(time.time())}")
    lines.append("> Use this page during active operations when advisory quality or flow health drifts.")
    lines.append("")

    lines.append("## Fast Triage Matrix")
    lines.append("")
    lines.append("| Signal | Current | Threshold | Status |")
    lines.append("|---|---:|---|---|")
    for check in checks:
        lines.append(
            f"| {check['name']} | {check['value']} | {check['threshold']} | **{check['status']}** |"
        )
    lines.append("")

    lines.append("## Runbook Checks")
    lines.append("")
    for idx, check in enumerate(checks, start=1):
        lines.append(f"### {idx}) {check['name']}")
        lines.append(f"- Current: `{check['value']}`")
        lines.append(f"- Threshold: `{check['threshold']}`")
        lines.append(f"- Status: **{check['status']}**")
        lines.append(f"- Command: `{check['cmd']}`")
        lines.append(f"- Immediate action: {check['immediate']}")
        lines.append(f"- Durable fix: {check['fix']}")
        lines.append("")

    lines.append("## Example Fault Patterns (From Recent Runtime)")
    lines.append("")
    lines.append("- Emitted then fast-suppressed sequence (expected anti-spam behavior):")
    lines.append("  - `emitted -> gate_no_emit(shown TTL) -> global_dedupe_suppressed` for same baseline advice within seconds.")
    lines.append("- Typical suppression reasons currently dominant:")
    top_reasons = suppression.get("top_reasons") or []
    if top_reasons:
        for reason, count in top_reasons[:6]:
            lines.append(f"  - `{reason}`: {count}")
    else:
        lines.append("  - No suppression reasons found.")
    lines.append("")

    lines.append("## Gaps To Prioritize")
    lines.append("")
    lines.append("1. Source/authority-aware TTL policy (reduce over-suppression from shown TTL).")
    lines.append("2. Dynamic per-call emission budget (reduce `budget exhausted` drops).")
    lines.append("3. Tool-family cooldown profiles (reduce blanket cooldown loss).")
    lines.append("4. Emit-floor alerts when follow-rate remains high but emissions fall.")
    lines.append("")

    lines.append("## Useful Links")
    lines.append("")
    lines.append("- [[system_flow_comprehensive|System Flow Comprehensive]]")
    lines.append("- [[advisory_reverse_engineering|Advisory Reverse Engineering]]")
    lines.append("- [[stages/08-advisory|Stage 8 - Advisory]]")
    lines.append("- [[../Advisory Implementation Tasks|Advisory Implementation Tasks]]")
    lines.append("")

    return "\n".join(lines)
