"""In-memory trace state manager."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .trace_collector import TraceEvent, TraceStatus


class TracePhase(str, Enum):
    IDLE = "idle"
    INTENT = "intent"
    EXECUTING = "executing"
    OUTCOME = "outcome"
    LESSON = "lesson"


@dataclass
class TraceMetrics:
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None
    duration_ms: int = 0
    blocker_count: int = 0
    confidence_final: float = 0.0

    def finish(self, confidence: float = 0.0) -> None:
        now = time.time()
        self.end_ts = now
        self.duration_ms = int(max(0.0, (now - float(self.start_ts or now)) * 1000.0))
        self.confidence_final = float(confidence or 0.0)


@dataclass
class ActiveTrace:
    trace_id: str
    session_id: str = ""
    phase: TracePhase = TracePhase.IDLE
    status: TraceStatus = TraceStatus.PENDING
    intent: str = ""
    intent_category: str = ""
    action: str = ""
    outcome: str = ""
    lesson: str = ""
    lesson_confidence: float = 0.0
    advisory_id: str = ""
    advisory_received: bool = False
    advisory_actioned: bool = False
    blockers: List[str] = field(default_factory=list)
    file_paths: List[str] = field(default_factory=list)
    events: List[TraceEvent] = field(default_factory=list)
    metrics: TraceMetrics = field(default_factory=TraceMetrics)
    last_activity: float = field(default_factory=time.time)

    def update_from_event(self, event: TraceEvent) -> None:
        self.events.append(event)
        self.last_activity = float(event.timestamp or time.time())
        if event.session_id and not self.session_id:
            self.session_id = event.session_id
        if event.intent:
            self.intent = event.intent
        if event.intent_category:
            self.intent_category = event.intent_category
        if event.action:
            self.action = event.action
        if event.outcome:
            self.outcome = event.outcome
        if event.lesson:
            self.lesson = event.lesson
            self.lesson_confidence = float(event.lesson_confidence or self.lesson_confidence or 0.0)
        if event.file_paths:
            for path in event.file_paths:
                p = str(path or "").strip()
                if p and p not in self.file_paths:
                    self.file_paths.append(p)
        if event.advisory_id:
            self.advisory_id = event.advisory_id
        self.advisory_received = bool(self.advisory_received or event.advisory_received)
        self.advisory_actioned = bool(self.advisory_actioned or event.advisory_actioned)
        self.status = event.status

        if event.status == TraceStatus.PENDING:
            self.phase = TracePhase.INTENT
        elif event.status in {TraceStatus.RUNNING, TraceStatus.BLOCKED}:
            self.phase = TracePhase.EXECUTING
        elif event.status in {TraceStatus.SUCCESS, TraceStatus.FAIL}:
            self.phase = TracePhase.OUTCOME
            if self.metrics.end_ts is None:
                self.metrics.finish(confidence=float(event.confidence_after or 0.0))
        if self.lesson:
            self.phase = TracePhase.LESSON

    def add_blocker(self, blocker: str) -> None:
        text = str(blocker or "").strip()
        if not text:
            return
        self.blockers.append(text)
        self.metrics.blocker_count += 1
        self.status = TraceStatus.BLOCKED
        self.phase = TracePhase.EXECUTING
        self.last_activity = time.time()

    def mark_advisory_actioned(self) -> None:
        self.advisory_actioned = True
        self.last_activity = time.time()

    def is_stale(self, timeout_seconds: float = 300.0) -> bool:
        return (time.time() - float(self.last_activity or 0.0)) > float(timeout_seconds)


class TraceState:
    """Tracks active and historical traces."""

    def __init__(self):
        self._traces: Dict[str, ActiveTrace] = {}
        self._history: List[ActiveTrace] = []
        self._action_history: List[bool] = []

    def get_or_create_trace(self, trace_id: str, session_id: str = "") -> ActiveTrace:
        trace = self._traces.get(trace_id)
        if trace is None:
            trace = ActiveTrace(trace_id=trace_id, session_id=session_id or "")
            self._traces[trace_id] = trace
        elif session_id and not trace.session_id:
            trace.session_id = session_id
        return trace

    def get_trace(self, trace_id: str) -> Optional[ActiveTrace]:
        return self._traces.get(trace_id)

    def remove_trace(self, trace_id: str) -> None:
        self._traces.pop(trace_id, None)

    def update_from_event(self, event: TraceEvent) -> ActiveTrace:
        trace = self.get_or_create_trace(event.trace_id, event.session_id)
        trace.update_from_event(event)
        if event.status in {TraceStatus.SUCCESS, TraceStatus.FAIL}:
            self._action_history.append(event.status == TraceStatus.SUCCESS)
        return trace

    def ingest_events(self, events: List[TraceEvent]) -> List[ActiveTrace]:
        updated: Dict[str, ActiveTrace] = {}
        for event in events or []:
            if not event.trace_id:
                continue
            updated[event.trace_id] = self.update_from_event(event)
        return list(updated.values())

    def get_active_traces(self) -> List[ActiveTrace]:
        return sorted(self._traces.values(), key=lambda t: float(t.last_activity or 0.0), reverse=True)

    def get_blocked_traces(self) -> List[ActiveTrace]:
        return [t for t in self.get_active_traces() if t.status == TraceStatus.BLOCKED]

    def get_recent_completed(self, limit: int = 10) -> List[ActiveTrace]:
        rows = sorted(self._history, key=lambda t: float(t.last_activity or 0.0), reverse=True)
        return rows[: max(0, int(limit or 0))]

    def cleanup_stale(self, timeout_seconds: float = 300.0) -> int:
        stale_ids = [tid for tid, trace in self._traces.items() if trace.is_stale(timeout_seconds)]
        for tid in stale_ids:
            trace = self._traces.pop(tid, None)
            if trace is not None:
                self._history.append(trace)
        return len(stale_ids)

    def get_kpis(self) -> Dict[str, Any]:
        active = self.get_active_traces()
        active_count = len(active)
        blocked_count = len([t for t in active if t.status == TraceStatus.BLOCKED])
        recent_active = len([t for t in active if (time.time() - float(t.last_activity or 0.0)) <= 300.0])
        lessons = len([t for t in active if t.lesson]) + len([t for t in self._history if t.lesson])
        advisory_actioned_total = len([t for t in active if t.advisory_actioned]) + len(
            [t for t in self._history if t.advisory_actioned]
        )
        traces_total = max(1, active_count + len(self._history))
        advisory_rate = int(round(100.0 * advisory_actioned_total / traces_total))

        window = self._history[-100:] if self._history else []
        success = len([t for t in window if t.status == TraceStatus.SUCCESS])
        fail = len([t for t in window if t.status == TraceStatus.FAIL])
        denom = max(1, success + fail)
        success_rate = int(round(100.0 * success / denom)) if (success + fail) > 0 else 0

        phase_distribution: Dict[str, int] = {}
        for trace in active:
            key = trace.phase.value
            phase_distribution[key] = phase_distribution.get(key, 0) + 1

        return {
            "active_tasks": active_count,
            "recent_active": recent_active,
            "blocked_tasks": blocked_count,
            "success_rate_100": success_rate,
            "advisory_action_rate_100": advisory_rate,
            "lessons_learned": lessons,
            "total_actions": len(self._action_history),
            "phase_distribution": phase_distribution,
        }

    def get_detailed_stats(self) -> Dict[str, Any]:
        durations = [int(t.metrics.duration_ms or 0) for t in self._history if int(t.metrics.duration_ms or 0) > 0]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0
        total_blockers = sum(int(t.metrics.blocker_count or 0) for t in self._traces.values()) + sum(
            int(t.metrics.blocker_count or 0) for t in self._history
        )
        return {
            "active_traces": len(self._traces),
            "historical_traces": len(self._history),
            "avg_duration_ms": avg_duration,
            "total_blockers": total_blockers,
        }
