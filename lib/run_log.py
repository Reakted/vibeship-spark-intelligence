"""SparkRunLog: facade for run/episode timelines (no new storage)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.eidos import get_store, get_evidence_store


OUTCOMES_FILE = Path.home() / ".spark" / "outcomes.jsonl"


def _read_jsonl(path: Path, limit: int = 800) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    rows = []
    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _count_evidence_for_steps(step_ids: List[str]) -> int:
    if not step_ids:
        return 0
    ev_store = get_evidence_store()
    try:
        with sqlite3.connect(ev_store.db_path) as conn:
            q = "SELECT COUNT(*) FROM evidence WHERE step_id IN ({})".format(
                ",".join("?" for _ in step_ids)
            )
            row = conn.execute(q, step_ids).fetchone()
            return int(row[0] or 0)
    except Exception:
        return 0


def get_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent run records (facade over episodes/steps/outcomes)."""
    store = get_store()
    episodes = store.get_recent_episodes(limit=limit)
    outcomes = _read_jsonl(OUTCOMES_FILE, limit=1200)
    runs: List[Dict[str, Any]] = []

    for ep in episodes:
        steps = store.get_episode_steps(ep.episode_id)
        trace_ids = [s.trace_id for s in steps if getattr(s, "trace_id", None)]
        trace_ids = list(dict.fromkeys(trace_ids))
        outcomes_count = 0
        if trace_ids:
            outcomes_count = sum(1 for o in outcomes if o.get("trace_id") in trace_ids)
        evidence_count = _count_evidence_for_steps([s.step_id for s in steps])
        last_step_ts = steps[-1].created_at if steps else None
        runs.append({
            "episode_id": ep.episode_id,
            "goal": ep.goal,
            "phase": ep.phase.value,
            "outcome": ep.outcome.value,
            "final_evaluation": ep.final_evaluation,
            "start_ts": ep.start_ts,
            "end_ts": ep.end_ts,
            "last_step_ts": last_step_ts,
            "step_count": len(steps),
            "trace_count": len(trace_ids),
            "evidence_count": evidence_count,
            "outcomes_count": outcomes_count,
            "escape_protocol_triggered": ep.escape_protocol_triggered,
            "error_counts": ep.error_counts,
        })
    return runs


def get_run_detail(episode_id: str) -> Dict[str, Any]:
    """Return a detailed run record for one episode."""
    store = get_store()
    ep = store.get_episode(episode_id)
    if not ep:
        return {"episode_id": episode_id, "found": False}

    steps = store.get_episode_steps(episode_id)
    step_ids = [s.step_id for s in steps]
    trace_ids = [s.trace_id for s in steps if getattr(s, "trace_id", None)]
    trace_ids = list(dict.fromkeys(trace_ids))

    evidence = []
    try:
        ev_store = get_evidence_store()
        for step in steps:
            for ev in ev_store.get_for_step(step.step_id):
                evidence.append({
                    "evidence_id": ev.evidence_id,
                    "step_id": ev.step_id,
                    "trace_id": ev.trace_id,
                    "type": ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                    "tool": ev.tool_name,
                    "created_at": ev.created_at,
                    "expires_at": ev.expires_at,
                    "bytes": ev.byte_size,
                })
    except Exception:
        pass

    outcomes = []
    if trace_ids:
        for row in _read_jsonl(OUTCOMES_FILE, limit=1200):
            if row.get("trace_id") in trace_ids:
                outcomes.append(row)

    return {
        "episode": {
            "episode_id": ep.episode_id,
            "goal": ep.goal,
            "phase": ep.phase.value,
            "outcome": ep.outcome.value,
            "final_evaluation": ep.final_evaluation,
            "start_ts": ep.start_ts,
            "end_ts": ep.end_ts,
            "step_count": ep.step_count,
            "escape_protocol_triggered": ep.escape_protocol_triggered,
            "error_counts": ep.error_counts,
        },
        "steps": [
            {
                "step_id": s.step_id,
                "trace_id": s.trace_id,
                "intent": (s.intent or "")[:120],
                "decision": (s.decision or "")[:120],
                "evaluation": s.evaluation.value if hasattr(s.evaluation, "value") else str(s.evaluation),
                "validated": bool(s.validated),
                "created_at": s.created_at,
                "result": (s.result or "")[:200],
            }
            for s in steps
        ],
        "evidence": evidence,
        "outcomes": outcomes,
        "trace_ids": trace_ids,
        "found": True,
        "step_ids": step_ids,
    }


def get_run_kpis(limit: int = 50) -> Dict[str, Any]:
    """Compute run KPIs from recent episodes."""
    runs = get_recent_runs(limit=limit)
    if not runs:
        return {"avg_steps": 0, "escape_rate": 0.0, "evidence_ratio": 0.0, "runs": 0}

    total_steps = sum(r.get("step_count", 0) for r in runs)
    total_evidence = sum(r.get("evidence_count", 0) for r in runs)
    escape_count = sum(1 for r in runs if r.get("escape_protocol_triggered"))
    runs_count = len(runs)

    avg_steps = total_steps / max(1, runs_count)
    escape_rate = escape_count / max(1, runs_count)
    evidence_ratio = total_evidence / max(1, total_steps)

    return {
        "avg_steps": round(avg_steps, 2),
        "escape_rate": round(escape_rate, 3),
        "evidence_ratio": round(evidence_ratio, 3),
        "runs": runs_count,
    }
