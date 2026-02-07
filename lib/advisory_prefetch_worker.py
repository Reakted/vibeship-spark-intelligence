"""Background-style worker helpers for advisory prefetch queue processing."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from . import advisory_packet_store as packet_store
from .advisory_prefetch_planner import plan_prefetch_jobs


WORKER_ENABLED = os.getenv("SPARK_ADVISORY_PREFETCH_WORKER", "1") != "0"
PROCESSED_MAX = 4000


def _worker_state_file():
    return packet_store.PACKET_DIR / "prefetch_worker_state.json"


def _state_defaults() -> Dict[str, Any]:
    return {
        "paused": False,
        "pause_reason": "",
        "last_run_at": None,
        "processed_count": 0,
        "processed_job_ids": [],
        "last_result": {},
    }


def _load_state() -> Dict[str, Any]:
    state_file = _worker_state_file()
    if not state_file.exists():
        return _state_defaults()
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = _state_defaults()
            merged.update(data)
            if not isinstance(merged.get("processed_job_ids"), list):
                merged["processed_job_ids"] = []
            return merged
    except Exception:
        pass
    return _state_defaults()


def _save_state(state: Dict[str, Any]) -> None:
    state_file = _worker_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    safe = dict(_state_defaults())
    safe.update(state or {})
    processed_ids = [str(x) for x in (safe.get("processed_job_ids") or []) if str(x).strip()]
    safe["processed_job_ids"] = processed_ids[-PROCESSED_MAX:]
    state_file.write_text(json.dumps(safe, indent=2), encoding="utf-8")


def set_worker_paused(paused: bool, reason: str = "") -> Dict[str, Any]:
    state = _load_state()
    state["paused"] = bool(paused)
    state["pause_reason"] = str(reason or "")[:200]
    _save_state(state)
    return get_worker_status()


def _baseline_text(intent_family: str, tool_name: str) -> str:
    family = (intent_family or "emergent_other").strip()
    tool = (tool_name or "").strip()
    if family == "auth_security":
        return f"Before {tool}, validate auth assumptions and avoid exposing secrets in logs."
    if family == "deployment_ops":
        return f"Use reversible steps for {tool} and verify rollback conditions first."
    if family == "testing_validation":
        return f"For {tool}, prioritize reproducible checks and preserve failing-case evidence."
    if family == "schema_contracts":
        return f"Before {tool}, verify schema and contract compatibility to avoid breaking interfaces."
    if family == "orchestration_execution":
        return f"Use {tool} on critical-path tasks first; unblock dependencies before parallel work."
    if family == "knowledge_alignment":
        return f"Use {tool} to align with existing project patterns before broad edits."
    if family == "tool_reliability":
        return f"Keep {tool} steps minimal and validate assumptions before irreversible changes."
    return f"Use {tool} conservatively with fast validation and explicit rollback safety."


def _read_queue_rows() -> List[Dict[str, Any]]:
    queue_file = packet_store.PREFETCH_QUEUE_FILE
    if not queue_file.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for line in queue_file.read_text(encoding="utf-8").splitlines():
            row = line.strip()
            if not row:
                continue
            try:
                parsed = json.loads(row)
            except Exception:
                continue
            if isinstance(parsed, dict):
                out.append(parsed)
    except Exception:
        return []
    return out


def _pending_jobs(rows: List[Dict[str, Any]], processed_ids: List[str]) -> List[Dict[str, Any]]:
    done = {str(x) for x in (processed_ids or []) if str(x).strip()}
    out: List[Dict[str, Any]] = []
    for row in rows:
        job_id = str(row.get("job_id") or "").strip()
        if not job_id:
            continue
        if job_id in done:
            continue
        out.append(row)
    return out


def process_prefetch_queue(
    *,
    max_jobs: int = 3,
    max_tools_per_job: int = 3,
) -> Dict[str, Any]:
    """Consume queued prefetch intents and create predictive packets."""
    state = _load_state()
    if not WORKER_ENABLED:
        state["last_result"] = {"ok": False, "reason": "worker_disabled"}
        _save_state(state)
        return {"ok": False, "reason": "worker_disabled"}
    if state.get("paused"):
        state["last_result"] = {"ok": False, "reason": "paused", "pause_reason": state.get("pause_reason", "")}
        _save_state(state)
        return {"ok": False, "reason": "paused", "pause_reason": state.get("pause_reason", "")}

    rows = _read_queue_rows()
    pending = _pending_jobs(rows, state.get("processed_job_ids") or [])
    jobs = pending[: max(0, int(max_jobs or 0))]
    if not jobs:
        state["last_run_at"] = time.time()
        state["last_result"] = {"ok": True, "jobs_processed": 0, "packets_created": 0}
        _save_state(state)
        return state["last_result"]

    created_packets: List[str] = []
    processed_job_ids: List[str] = list(state.get("processed_job_ids") or [])
    per_job: List[Dict[str, Any]] = []

    for job in jobs:
        job_id = str(job.get("job_id") or "").strip()
        if not job_id:
            continue
        plans = plan_prefetch_jobs(job, max_jobs=max_tools_per_job, min_probability=0.25)
        local_packets: List[str] = []
        for planned in plans:
            tool_name = str(planned.get("tool_name") or "").strip() or "*"
            intent_family = str(planned.get("intent_family") or "emergent_other")
            packet = packet_store.build_packet(
                project_key=str(planned.get("project_key") or "unknown_project"),
                session_context_key=str(planned.get("session_context_key") or "default"),
                tool_name=tool_name,
                intent_family=intent_family,
                task_plane=str(planned.get("task_plane") or "build_delivery"),
                advisory_text=_baseline_text(intent_family, tool_name),
                source_mode="prefetch_deterministic",
                advice_items=[
                    {
                        "advice_id": f"prefetch_{intent_family}_{tool_name.lower()}",
                        "insight_key": f"prefetch:{intent_family}:{tool_name}",
                        "text": _baseline_text(intent_family, tool_name),
                        "confidence": float(planned.get("probability") or 0.5),
                        "source": "prefetch",
                        "context_match": 0.7,
                        "reason": "prefetch_plan",
                    }
                ],
                lineage={
                    "sources": ["prefetch"],
                    "memory_absent_declared": False,
                    "prefetch_job_id": job_id,
                },
            )
            packet_id = packet_store.save_packet(packet)
            local_packets.append(packet_id)
            created_packets.append(packet_id)
        processed_job_ids.append(job_id)
        per_job.append(
            {
                "job_id": job_id,
                "planned_tools": [str(p.get("tool_name") or "") for p in plans],
                "packets_created": local_packets,
            }
        )

    state["processed_job_ids"] = processed_job_ids[-PROCESSED_MAX:]
    state["processed_count"] = int(state.get("processed_count", 0) or 0) + len(per_job)
    state["last_run_at"] = time.time()
    state["last_result"] = {
        "ok": True,
        "jobs_processed": len(per_job),
        "packets_created": len(created_packets),
        "jobs": per_job,
    }
    _save_state(state)
    return state["last_result"]


def get_worker_status() -> Dict[str, Any]:
    state = _load_state()
    rows = _read_queue_rows()
    pending = _pending_jobs(rows, state.get("processed_job_ids") or [])
    store = packet_store.get_store_status()
    return {
        "enabled": bool(WORKER_ENABLED),
        "paused": bool(state.get("paused", False)),
        "pause_reason": str(state.get("pause_reason") or ""),
        "last_run_at": state.get("last_run_at"),
        "processed_count": int(state.get("processed_count", 0) or 0),
        "pending_jobs": len(pending),
        "last_result": state.get("last_result") or {},
        "packets_total": int(store.get("total_packets", 0) or 0),
    }
