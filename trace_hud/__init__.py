#!/usr/bin/env python3
"""Decision Trace HUD - Real-time observability for Spark intelligence loops.

A terminal dashboard that proves Spark is doing real intelligence work:
Intent → Action → Evidence → Outcome → Lesson in one visible stream.

Components:
- trace_collector: Normalizes events from multiple Spark sources
- trace_state: Manages in-memory state per trace
- trace_store: Persistent append-only storage with replay
- trace_tui: Rich terminal dashboard
- trace_hud: Main orchestrator
"""

__version__ = "1.0.0"

from trace_hud.trace_collector import TraceCollector, TraceEvent, TraceStatus, TraceSource, TraceEvidence
from trace_hud.trace_state import TraceState, ActiveTrace, TracePhase, TraceMetrics
from trace_hud.trace_store import TraceStore
from trace_hud.trace_tui import TraceTUI, TUIConfig
from trace_hud.trace_hud import DecisionTraceHUD

__all__ = [
    'TraceCollector',
    'TraceEvent',
    'TraceStatus',
    'TraceSource',
    'TraceEvidence',
    'TraceState',
    'ActiveTrace',
    'TracePhase',
    'TraceMetrics',
    'TraceStore',
    'TraceTUI',
    'TUIConfig',
    'DecisionTraceHUD',
]
