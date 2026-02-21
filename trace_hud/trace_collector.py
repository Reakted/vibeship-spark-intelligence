"""Lightweight trace event collector."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TraceSource(str, Enum):
    USER_PROMPT = "user_prompt"
    TOOL_CALL = "tool_call"
    ADVISORY = "advisory"
    PATTERN_DETECTED = "pattern_detected"
    BRIDGE_HEARTBEAT = "bridge_heartbeat"
    SYSTEM = "system"


class TraceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAIL = "fail"
    BLOCKED = "blocked"


@dataclass
class TraceEvidence:
    status_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TraceEvidence":
        if not isinstance(raw, dict):
            return cls()
        return cls(
            status_code=raw.get("status_code"),
            stdout=str(raw.get("stdout") or ""),
            stderr=str(raw.get("stderr") or ""),
            error_message=str(raw.get("error_message") or ""),
        )


@dataclass
class TraceEvent:
    trace_id: str
    event_id: str
    timestamp: float
    source: TraceSource
    intent: str
    status: TraceStatus
    session_id: str = ""
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    action: str = ""
    action_type: str = ""
    outcome: str = ""
    lesson: str = ""
    lesson_confidence: float = 0.0
    evidence: Optional[TraceEvidence] = None
    intent_category: str = ""
    file_paths: List[str] = field(default_factory=list)
    advisory_id: str = ""
    advisory_received: bool = False
    advisory_actioned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "event_id": self.event_id,
            "timestamp": float(self.timestamp),
            "source": self.source.value,
            "intent": self.intent,
            "status": self.status.value,
            "session_id": self.session_id,
            "confidence_before": float(self.confidence_before),
            "confidence_after": float(self.confidence_after),
            "action": self.action,
            "action_type": self.action_type,
            "outcome": self.outcome,
            "lesson": self.lesson,
            "lesson_confidence": float(self.lesson_confidence),
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "intent_category": self.intent_category,
            "file_paths": list(self.file_paths or []),
            "advisory_id": self.advisory_id,
            "advisory_received": bool(self.advisory_received),
            "advisory_actioned": bool(self.advisory_actioned),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TraceEvent":
        source_raw = str(raw.get("source") or TraceSource.SYSTEM.value).strip().lower()
        status_raw = str(raw.get("status") or TraceStatus.PENDING.value).strip().lower()
        try:
            source = TraceSource(source_raw)
        except Exception:
            source = TraceSource.SYSTEM
        try:
            status = TraceStatus(status_raw)
        except Exception:
            status = TraceStatus.PENDING

        evidence_raw = raw.get("evidence")
        evidence = TraceEvidence.from_dict(evidence_raw) if isinstance(evidence_raw, dict) else None
        file_paths_raw = raw.get("file_paths")
        file_paths = [str(x) for x in file_paths_raw] if isinstance(file_paths_raw, list) else []

        timestamp = raw.get("timestamp")
        try:
            ts = float(timestamp)
        except Exception:
            ts = time.time()

        return cls(
            trace_id=str(raw.get("trace_id") or ""),
            event_id=str(raw.get("event_id") or f"evt_{int(ts * 1000)}"),
            timestamp=ts,
            source=source,
            intent=str(raw.get("intent") or ""),
            status=status,
            session_id=str(raw.get("session_id") or ""),
            confidence_before=float(raw.get("confidence_before") or 0.0),
            confidence_after=float(raw.get("confidence_after") or 0.0),
            action=str(raw.get("action") or ""),
            action_type=str(raw.get("action_type") or ""),
            outcome=str(raw.get("outcome") or ""),
            lesson=str(raw.get("lesson") or ""),
            lesson_confidence=float(raw.get("lesson_confidence") or 0.0),
            evidence=evidence,
            intent_category=str(raw.get("intent_category") or ""),
            file_paths=file_paths,
            advisory_id=str(raw.get("advisory_id") or ""),
            advisory_received=bool(raw.get("advisory_received")),
            advisory_actioned=bool(raw.get("advisory_actioned")),
        )


class TraceCollector:
    """Poll trace events from local JSONL sources."""

    def __init__(self, spark_dir: Optional[Path] = None):
        self.spark_dir = Path(spark_dir or (Path.home() / ".spark"))
        self._offsets: Dict[str, int] = {}

    def _source_files(self) -> List[Path]:
        tracer_dir = self.spark_dir / "tracer"
        files = [
            tracer_dir / "events.jsonl",
            self.spark_dir / "trace_events.jsonl",
        ]
        return [f for f in files if f.exists()]

    def _read_new_rows(self, path: Path) -> List[TraceEvent]:
        out: List[TraceEvent] = []
        key = str(path.resolve())
        start = int(self._offsets.get(key, 0) or 0)
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(start)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(row, dict):
                        continue
                    evt = TraceEvent.from_dict(row)
                    if evt.trace_id and evt.event_id:
                        out.append(evt)
                self._offsets[key] = f.tell()
        except Exception:
            return []
        return out

    def poll_all_sources(self) -> List[TraceEvent]:
        events: List[TraceEvent] = []
        for path in self._source_files():
            events.extend(self._read_new_rows(path))
        events.sort(key=lambda e: float(e.timestamp or 0.0))
        return events
