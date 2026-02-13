#!/usr/bin/env python3
"""trace_state.py - In-memory state machine for tracking active traces.

Maintains state per task/thread:
- Current phase (intent → action → evidence → outcome → lesson)
- Status transitions
- Blockers and deferrals
- Success/failure history for KPIs
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Deque
from threading import Lock

from trace_hud.trace_collector import TraceEvent, TraceStatus, TraceSource


class TracePhase(Enum):
    """Phase in the decision trace lifecycle."""
    IDLE = "idle"
    INTENT = "intent"       # We know what we want to do
    ACTION = "action"       # We've decided on an action
    EXECUTING = "executing" # Action is running
    EVIDENCE = "evidence"   # We have results back
    OUTCOME = "outcome"     # We've evaluated success/fail
    LESSON = "lesson"       # We've distilled a lesson
    COMPLETE = "complete"   # Trace is finished


@dataclass
class TraceMetrics:
    """Metrics for a single trace."""
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[int] = None
    confidence_start: float = 0.0
    confidence_end: float = 0.0
    retry_count: int = 0
    blocker_count: int = 0
    
    def finish(self, confidence: float = 0.0):
        """Mark trace as finished."""
        self.end_time = time.time()
        self.duration_ms = int((self.end_time - self.start_time) * 1000)
        self.confidence_end = confidence


@dataclass
class ActiveTrace:
    """Represents one active decision trace/task."""
    # Identity
    trace_id: str
    session_id: Optional[str] = None
    
    # Current state
    phase: TracePhase = TracePhase.IDLE
    status: TraceStatus = TraceStatus.PENDING
    
    # Decision components
    intent: str = ""
    intent_category: Optional[str] = None
    action: Optional[str] = None
    action_type: Optional[str] = None
    evidence_summary: Optional[str] = None
    outcome: Optional[str] = None
    lesson: Optional[str] = None
    lesson_confidence: float = 0.0
    
    # Context
    project_path: Optional[str] = None
    file_paths: List[str] = field(default_factory=list)
    
    # History of events contributing to this trace
    events: List[TraceEvent] = field(default_factory=list)
    
    # Metrics
    metrics: TraceMetrics = field(default_factory=lambda: TraceMetrics(start_time=time.time()))
    
    # Blockers (if any)
    blockers: List[str] = field(default_factory=list)
    
    # Advisory tracking
    advisory_requested: bool = False
    advisory_received: bool = False
    advisory_actioned: bool = False
    advisory_id: Optional[str] = None
    
    # Last activity for timeout detection
    last_activity: float = field(default_factory=time.time)
    
    def update_from_event(self, event: TraceEvent) -> None:
        """Update trace state from a new event."""
        self.events.append(event)
        self.last_activity = time.time()
        
        # Update fields from event
        if event.intent:
            self.intent = event.intent
        if event.intent_category:
            self.intent_category = event.intent_category
        if event.action:
            self.action = event.action
        if event.action_type:
            self.action_type = event.action_type
        if event.lesson:
            self.lesson = event.lesson
            self.lesson_confidence = event.lesson_confidence
        if event.project_path:
            self.project_path = event.project_path
        if event.file_paths:
            self.file_paths = list(set(self.file_paths + event.file_paths))
        if event.advisory_id:
            self.advisory_id = event.advisory_id
        
        # Update status
        self.status = event.status
        
        # Phase transitions based on status and content
        self._update_phase(event)
    
    def _update_phase(self, event: TraceEvent) -> None:
        """Update phase based on event status and content."""
        if self.status == TraceStatus.PENDING:
            self.phase = TracePhase.INTENT
        elif self.status == TraceStatus.RUNNING:
            self.phase = TracePhase.EXECUTING
        elif self.status in (TraceStatus.SUCCESS, TraceStatus.FAIL):
            self.phase = TracePhase.OUTCOME
            if not self.metrics.end_time:
                self.metrics.finish(event.confidence_after)
        elif self.status == TraceStatus.DEFERRED:
            self.phase = TracePhase.EVIDENCE
        elif self.status == TraceStatus.BLOCKED:
            self.phase = TracePhase.ACTION
            self.blockers.append(event.outcome_summary or "Unknown blocker")
            self.metrics.blocker_count += 1
        
        # Move to LESSON phase if we have a lesson
        if self.lesson and self.phase.value in ('outcome', 'complete'):
            self.phase = TracePhase.LESSON
        
        # Complete if we have outcome and lesson
        if self.outcome and self.lesson and self.phase == TracePhase.LESSON:
            self.phase = TracePhase.COMPLETE
    
    def add_blocker(self, reason: str) -> None:
        """Add a blocker to this trace."""
        self.blockers.append(reason)
        self.status = TraceStatus.BLOCKED
        self.phase = TracePhase.ACTION
        self.metrics.blocker_count += 1
        self.last_activity = time.time()
    
    def mark_advisory_actioned(self) -> None:
        """Mark that advice was acted upon."""
        self.advisory_actioned = True
        self.last_activity = time.time()
    
    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to dict for display."""
        return {
            'trace_id': self.trace_id[:16] + '...' if len(self.trace_id) > 16 else self.trace_id,
            'phase': self.phase.value,
            'status': self.status.value,
            'intent': self.intent[:60] + '...' if len(self.intent) > 60 else self.intent,
            'action': (self.action[:40] + '...') if self.action and len(self.action) > 40 else self.action,
            'evidence': self.evidence_summary,
            'outcome': self.outcome,
            'lesson': (self.lesson[:60] + '...') if self.lesson and len(self.lesson) > 60 else self.lesson,
            'blockers': len(self.blockers),
            'duration_ms': self.metrics.duration_ms,
            'files': len(self.file_paths),
        }
    
    def is_stale(self, timeout_seconds: float = 300.0) -> bool:
        """Check if trace is stale (no activity)."""
        return (time.time() - self.last_activity) > timeout_seconds


class TraceState:
    """Manages all active traces and computes aggregate KPIs."""
    
    def __init__(self, max_history: int = 1000):
        self._traces: Dict[str, ActiveTrace] = {}
        self._lock = Lock()
        self._history: Deque[ActiveTrace] = deque(maxlen=max_history)
        
        # KPI tracking
        self._action_history: Deque[bool] = deque(maxlen=100)  # Success/fail
        self._advisory_history: Deque[bool] = deque(maxlen=100)  # Actioned or not
        
        # Window for recent stats
        self._recent_window_seconds: float = 300.0  # 5 minutes
    
    # -------------------------------------------------------------------------
    # Trace lifecycle
    # -------------------------------------------------------------------------
    
    def get_or_create_trace(self, trace_id: str, session_id: Optional[str] = None) -> ActiveTrace:
        """Get existing trace or create new one."""
        with self._lock:
            if trace_id not in self._traces:
                self._traces[trace_id] = ActiveTrace(
                    trace_id=trace_id,
                    session_id=session_id or trace_id,
                )
            return self._traces[trace_id]
    
    def update_from_event(self, event: TraceEvent) -> ActiveTrace:
        """Update or create trace from event."""
        trace = self.get_or_create_trace(event.trace_id, event.session_id)
        trace.update_from_event(event)
        
        # Track in history if completed
        if trace.status in (TraceStatus.SUCCESS, TraceStatus.FAIL, TraceStatus.CANCELLED):
            if trace not in self._history:
                self._history.append(trace)
            # Track success/fail
            self._action_history.append(trace.status == TraceStatus.SUCCESS)
        
        # Track advisory
        if event.source == TraceSource.SPARK_ADVISORY and trace.advisory_actioned:
            self._advisory_history.append(True)
        
        return trace
    
    def ingest_events(self, events: List[TraceEvent]) -> List[ActiveTrace]:
        """Ingest multiple events and return updated traces."""
        updated = []
        for event in events:
            trace = self.update_from_event(event)
            if trace not in updated:
                updated.append(trace)
        return updated
    
    def remove_trace(self, trace_id: str) -> Optional[ActiveTrace]:
        """Remove a trace from active set."""
        with self._lock:
            return self._traces.pop(trace_id, None)
    
    def cleanup_stale(self, timeout_seconds: float = 300.0) -> int:
        """Remove stale traces, return count removed."""
        removed = 0
        with self._lock:
            stale_ids = [
                tid for tid, trace in self._traces.items()
                if trace.is_stale(timeout_seconds)
            ]
            for tid in stale_ids:
                trace = self._traces.pop(tid)
                self._history.append(trace)
                removed += 1
        return removed
    
    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------
    
    def get_active_traces(self) -> List[ActiveTrace]:
        """Get all currently active traces."""
        with self._lock:
            # Sort by phase (earlier phases first) then by last activity
            return sorted(
                self._traces.values(),
                key=lambda t: (t.phase.value, -t.last_activity)
            )
    
    def get_traces_by_status(self, status: TraceStatus) -> List[ActiveTrace]:
        """Get traces filtered by status."""
        with self._lock:
            return [t for t in self._traces.values() if t.status == status]
    
    def get_blocked_traces(self) -> List[ActiveTrace]:
        """Get all blocked traces."""
        return self.get_traces_by_status(TraceStatus.BLOCKED)
    
    def get_recent_completed(self, count: int = 10) -> List[ActiveTrace]:
        """Get recently completed traces."""
        with self._lock:
            return list(self._history)[-count:]
    
    def get_trace(self, trace_id: str) -> Optional[ActiveTrace]:
        """Get specific trace by ID."""
        with self._lock:
            return self._traces.get(trace_id)
    
    # -------------------------------------------------------------------------
    # KPIs
    # -------------------------------------------------------------------------
    
    def get_kpis(self) -> Dict[str, Any]:
        """Compute current KPIs for the HUD top bar."""
        with self._lock:
            active_count = len(self._traces)
            blocked_count = len([t for t in self._traces.values() if t.status == TraceStatus.BLOCKED])
            
            # Success rate from history
            if self._action_history:
                success_rate = sum(self._action_history) / len(self._action_history)
            else:
                success_rate = 0.0
            
            # Advisory action rate
            if self._advisory_history:
                advisory_rate = sum(self._advisory_history) / len(self._advisory_history)
            else:
                advisory_rate = 0.0
            
            # Recent activity (last 5 min)
            now = time.time()
            recent_active = len([
                t for t in self._traces.values()
                if (now - t.last_activity) < self._recent_window_seconds
            ])
            
            # Phase distribution
            phases: Dict[str, int] = {}
            for t in self._traces.values():
                phase = t.phase.value
                phases[phase] = phases.get(phase, 0) + 1
            
            return {
                'active_tasks': active_count,
                'recent_active': recent_active,
                'blocked_tasks': blocked_count,
                'success_rate_100': int(success_rate * 100),
                'advisory_action_rate_100': int(advisory_rate * 100),
                'total_actions': len(self._action_history),
                'phase_distribution': phases,
                'lessons_learned': len([t for t in self._history if t.lesson]),
            }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        with self._lock:
            total_duration = sum(
                (t.metrics.duration_ms or 0) for t in self._history if t.metrics.duration_ms
            )
            avg_duration = total_duration / max(len(self._history), 1)
            
            # Category breakdown
            categories: Dict[str, int] = {}
            for t in list(self._traces.values()) + list(self._history):
                cat = t.intent_category or 'uncategorized'
                categories[cat] = categories.get(cat, 0) + 1
            
            return {
                'active_traces': len(self._traces),
                'historical_traces': len(self._history),
                'avg_duration_ms': int(avg_duration),
                'total_blockers': sum(t.metrics.blocker_count for t in self._traces.values()),
                'category_breakdown': categories,
            }
    
    # -------------------------------------------------------------------------
    # State export/import
    # -------------------------------------------------------------------------
    
    def to_snapshot(self) -> Dict[str, Any]:
        """Export current state as snapshot."""
        with self._lock:
            return {
                'timestamp': time.time(),
                'active_traces': [t.to_display_dict() for t in self._traces.values()],
                'kpis': self.get_kpis(),
                'stats': self.get_detailed_stats(),
            }
    
    def clear(self) -> None:
        """Clear all state."""
        with self._lock:
            self._traces.clear()
            self._history.clear()
            self._action_history.clear()
            self._advisory_history.clear()


def demo_state():
    """Demo the state manager."""
    from trace_hud.trace_collector import TraceEvent, TraceSource
    
    state = TraceState()
    
    # Create some fake events
    events = [
        TraceEvent(
            trace_id="test_1",
            event_id="evt_1",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Fix the login bug",
            status=TraceStatus.PENDING,
        ),
        TraceEvent(
            trace_id="test_1",
            event_id="evt_2",
            timestamp=time.time(),
            source=TraceSource.TOOL_CALL,
            intent="Fix the login bug",
            action="Read auth.py",
            action_type="read",
            status=TraceStatus.RUNNING,
        ),
        TraceEvent(
            trace_id="test_2",
            event_id="evt_3",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Add user profile page",
            status=TraceStatus.PENDING,
        ),
    ]
    
    state.ingest_events(events)
    
    print("Active traces:")
    for t in state.get_active_traces():
        print(f"  {t.trace_id}: {t.phase.value} - {t.intent[:40]}")
    
    print(f"\nKPIs: {state.get_kpis()}")


if __name__ == "__main__":
    demo_state()
