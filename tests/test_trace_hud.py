#!/usr/bin/env python3
"""Tests for the Decision Trace HUD."""

import json
import time
import tempfile
from pathlib import Path

import pytest

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from trace_hud.trace_collector import (
    TraceCollector,
    TraceEvent,
    TraceStatus,
    TraceSource,
    TraceEvidence,
)
from trace_hud.trace_state import TraceState, ActiveTrace, TracePhase, TraceMetrics
from trace_hud.trace_store import TraceStore


class TestTraceEvent:
    """Test TraceEvent dataclass."""
    
    def test_basic_creation(self):
        evt = TraceEvent(
            trace_id="test_1",
            event_id="evt_1",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Test intent",
            status=TraceStatus.PENDING,
        )
        assert evt.trace_id == "test_1"
        assert evt.status == TraceStatus.PENDING
        assert evt.source == TraceSource.USER_PROMPT
    
    def test_to_dict(self):
        evt = TraceEvent(
            trace_id="test_1",
            event_id="evt_1",
            timestamp=1234567890.0,
            source=TraceSource.USER_PROMPT,
            intent="Test",
            status=TraceStatus.SUCCESS,
            evidence=TraceEvidence(status_code=200, stdout="output"),
        )
        d = evt.to_dict()
        assert d['trace_id'] == "test_1"
        assert d['source'] == "user_prompt"
        assert d['status'] == "success"
        assert d['evidence']['status_code'] == 200
    
    def test_from_dict(self):
        d = {
            'trace_id': 'test_1',
            'event_id': 'evt_1',
            'timestamp': 1234567890.0,
            'source': 'user_prompt',
            'intent': 'Test',
            'status': 'success',
            'confidence_before': 0.7,
        }
        evt = TraceEvent.from_dict(d)
        assert evt.trace_id == "test_1"
        assert evt.source == TraceSource.USER_PROMPT
        assert evt.status == TraceStatus.SUCCESS


class TestTraceState:
    """Test TraceState manager."""
    
    def test_create_trace(self):
        state = TraceState()
        trace = state.get_or_create_trace("test_1", "session_1")
        assert trace.trace_id == "test_1"
        assert trace.session_id == "session_1"
        assert trace.phase == TracePhase.IDLE
    
    def test_update_from_event(self):
        state = TraceState()
        evt = TraceEvent(
            trace_id="test_1",
            event_id="evt_1",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Fix bug",
            status=TraceStatus.PENDING,
        )
        trace = state.update_from_event(evt)
        assert trace.intent == "Fix bug"
        assert trace.phase == TracePhase.INTENT
    
    def test_ingest_multiple_events(self):
        state = TraceState()
        events = [
            TraceEvent(
                trace_id="test_1",
                event_id=f"evt_{i}",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent="Task",
                status=TraceStatus.PENDING if i == 0 else TraceStatus.RUNNING,
            )
            for i in range(3)
        ]
        traces = state.ingest_events(events)
        assert len(traces) == 1  # Same trace_id
        assert len(traces[0].events) == 3
    
    def test_get_active_traces(self):
        state = TraceState()
        events = [
            TraceEvent(
                trace_id=f"test_{i}",
                event_id=f"evt_{i}",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent=f"Task {i}",
                status=TraceStatus.PENDING,
            )
            for i in range(5)
        ]
        state.ingest_events(events)
        active = state.get_active_traces()
        assert len(active) == 5
    
    def test_get_blocked_traces(self):
        state = TraceState()
        events = [
            TraceEvent(
                trace_id="blocked_1",
                event_id="evt_1",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent="Blocked task",
                status=TraceStatus.BLOCKED,
            ),
            TraceEvent(
                trace_id="active_1",
                event_id="evt_2",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent="Active task",
                status=TraceStatus.PENDING,
            ),
        ]
        state.ingest_events(events)
        blocked = state.get_blocked_traces()
        assert len(blocked) == 1
        assert blocked[0].trace_id == "blocked_1"
    
    def test_kpis(self):
        state = TraceState()
        # Add some successful events
        for i in range(5):
            evt = TraceEvent(
                trace_id=f"test_{i}",
                event_id=f"evt_{i}",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent="Task",
                status=TraceStatus.SUCCESS,
            )
            state.update_from_event(evt)
            # Mark as completed and move to history
            trace = state.get_trace(f"test_{i}")
            trace.status = TraceStatus.SUCCESS
            trace.metrics.finish(confidence=0.8)
            state._history.append(trace)
            state._action_history.append(True)
            # Remove from active
            state.remove_trace(f"test_{i}")
        
        kpis = state.get_kpis()
        assert kpis['active_tasks'] == 0  # All moved to history
        assert kpis['success_rate_100'] == 100
    
    def test_cleanup_stale(self):
        state = TraceState()
        trace = state.get_or_create_trace("old_trace")
        trace.last_activity = time.time() - 1000  # Very old
        
        removed = state.cleanup_stale(timeout_seconds=300)
        assert removed == 1
        assert "old_trace" not in state._traces


class TestTraceStore:
    """Test TraceStore persistence."""
    
    def test_append_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=Path(tmp))
            
            evt = TraceEvent(
                trace_id="test_1",
                event_id="evt_1",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent="Test",
                status=TraceStatus.SUCCESS,
            )
            
            store.append(evt)
            store.flush()
            
            # Read back
            events = store.read_last(10)
            assert len(events) == 1
            assert events[0].trace_id == "test_1"
    
    def test_append_many(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=Path(tmp))
            
            events = [
                TraceEvent(
                    trace_id=f"test_{i}",
                    event_id=f"evt_{i}",
                    timestamp=time.time(),
                    source=TraceSource.USER_PROMPT,
                    intent=f"Task {i}",
                    status=TraceStatus.SUCCESS,
                )
                for i in range(10)
            ]
            
            store.append_many(events)
            store.flush()
            
            read_events = store.read_last(5)
            assert len(read_events) == 5
    
    def test_read_since(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=Path(tmp))
            
            now = time.time()
            events = [
                TraceEvent(
                    trace_id=f"test_{i}",
                    event_id=f"evt_{i}",
                    timestamp=now - i,  # Decreasing timestamps
                    source=TraceSource.USER_PROMPT,
                    intent=f"Task {i}",
                    status=TraceStatus.SUCCESS,
                )
                for i in range(10)
            ]
            
            store.append_many(events)
            store.flush()
            
            # Read only recent
            recent = list(store.read_since(now - 5))
            assert len(recent) == 6  # 0, 1, 2, 3, 4, 5
    
    def test_filter_by_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=Path(tmp))
            
            events = [
                TraceEvent(
                    trace_id="user_1",
                    event_id="evt_1",
                    timestamp=time.time(),
                    source=TraceSource.USER_PROMPT,
                    intent="User task",
                    status=TraceStatus.PENDING,
                ),
                TraceEvent(
                    trace_id="tool_1",
                    event_id="evt_2",
                    timestamp=time.time(),
                    source=TraceSource.TOOL_CALL,
                    intent="Tool task",
                    status=TraceStatus.SUCCESS,
                ),
            ]
            
            store.append_many(events)
            store.flush()
            
            # Filter
            user_events = list(store.read_since(
                0,
                source_filter=[TraceSource.USER_PROMPT]
            ))
            assert len(user_events) == 1
            assert user_events[0].source == TraceSource.USER_PROMPT
    
    def test_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=Path(tmp))
            
            events = [
                TraceEvent(
                    trace_id=f"test_{i}",
                    event_id=f"evt_{i}",
                    timestamp=time.time(),
                    source=TraceSource.USER_PROMPT,
                    intent=f"Task {i}",
                    status=TraceStatus.FAIL if i % 2 == 0 else TraceStatus.SUCCESS,
                )
                for i in range(10)
            ]
            
            store.append_many(events)
            store.flush()
            
            # Query for failures
            failures = store.query(lambda e: e.status == TraceStatus.FAIL, limit=10)
            assert len(failures) == 5
    
    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=Path(tmp))
            
            evt = TraceEvent(
                trace_id="test_1",
                event_id="evt_1",
                timestamp=time.time(),
                source=TraceSource.USER_PROMPT,
                intent="Test",
                status=TraceStatus.SUCCESS,
            )
            store.append(evt)
            store.flush()
            
            stats = store.get_stats()
            assert 'current_file' in stats
            assert stats['buffered_events'] == 0  # Flushed


class TestActiveTrace:
    """Test ActiveTrace state machine."""
    
    def test_phase_transitions(self):
        trace = ActiveTrace(trace_id="test_1")
        
        # Initial state
        assert trace.phase == TracePhase.IDLE
        
        # PENDING event
        evt = TraceEvent(
            trace_id="test_1",
            event_id="evt_1",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Do something",
            status=TraceStatus.PENDING,
        )
        trace.update_from_event(evt)
        assert trace.phase == TracePhase.INTENT
        
        # RUNNING event
        evt2 = TraceEvent(
            trace_id="test_1",
            event_id="evt_2",
            timestamp=time.time(),
            source=TraceSource.TOOL_CALL,
            intent="Do something",
            action="Read file",
            status=TraceStatus.RUNNING,
        )
        trace.update_from_event(evt2)
        assert trace.phase == TracePhase.EXECUTING
        
        # SUCCESS event
        evt3 = TraceEvent(
            trace_id="test_1",
            event_id="evt_3",
            timestamp=time.time(),
            source=TraceSource.TOOL_CALL,
            intent="Do something",
            action="Read file",
            status=TraceStatus.SUCCESS,
            lesson="Always check file exists first",
        )
        trace.update_from_event(evt3)
        assert trace.phase == TracePhase.LESSON
        assert trace.lesson is not None
    
    def test_blocker_tracking(self):
        trace = ActiveTrace(trace_id="test_1")
        trace.add_blocker("Missing dependency")
        
        assert trace.status == TraceStatus.BLOCKED
        assert len(trace.blockers) == 1
        assert trace.metrics.blocker_count == 1
    
    def test_advisory_tracking(self):
        trace = ActiveTrace(trace_id="test_1")
        trace.advisory_id = "adv_123"
        trace.advisory_received = True
        trace.mark_advisory_actioned()
        
        assert trace.advisory_actioned is True
    
    def test_stale_detection(self):
        trace = ActiveTrace(trace_id="test_1")
        trace.last_activity = time.time() - 1000
        
        assert trace.is_stale(timeout_seconds=300) is True
        assert trace.is_stale(timeout_seconds=2000) is False


class TestTraceCollector:
    """Test TraceCollector (lightweight)."""
    
    def test_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = TraceCollector(spark_dir=Path(tmp))
            assert collector.spark_dir == Path(tmp)
    
    def test_empty_poll(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = TraceCollector(spark_dir=Path(tmp))
            events = collector.poll_all_sources()
            assert isinstance(events, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
