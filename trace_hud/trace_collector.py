#!/usr/bin/env python3
"""trace_collector.py - Normalize events from Spark sources into common trace schema.

Ingests:
- OpenClaw/session events (user prompts, tool calls, results)
- Spark advisory events
- Agent feedback reports (spark_reports/*.json)
- Bridge heartbeat/status snapshots

Outputs normalized TraceEvent objects for the HUD.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator
import threading


class TraceStatus(Enum):
    """Status of a trace decision/action."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAIL = "fail"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TraceSource(Enum):
    """Source of the trace event."""
    OPENCLAW = "openclaw"
    SPARK_ADVISORY = "spark_advisory"
    AGENT_FEEDBACK = "agent_feedback"
    BRIDGE_HEARTBEAT = "bridge_heartbeat"
    USER_PROMPT = "user_prompt"
    TOOL_CALL = "tool_call"
    PATTERN_DETECTED = "pattern_detected"
    INSIGHT_LEARNED = "insight_learned"


@dataclass
class TraceEvidence:
    """Evidence from a tool/action execution."""
    status_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    diff: Optional[str] = None
    test_results: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TraceEvidence:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TraceEvent:
    """Normalized trace event - the core schema for the HUD."""
    # Identity
    trace_id: str
    event_id: str
    timestamp: float
    source: TraceSource
    
    # What we intended to do
    intent: str
    intent_category: Optional[str] = None  # e.g., "fix_bug", "add_feature", "refactor"
    
    # What we actually did
    action: Optional[str] = None  # tool/command executed
    action_type: Optional[str] = None  # "edit", "bash", "read", "test", etc.
    
    # Evidence/signal that came back
    evidence: Optional[TraceEvidence] = None
    
    # Outcome
    status: TraceStatus = TraceStatus.PENDING
    outcome_summary: Optional[str] = None
    
    # Lesson learned (filled in later by distillation)
    lesson: Optional[str] = None
    lesson_confidence: float = 0.0
    
    # Context
    session_id: Optional[str] = None
    project_path: Optional[str] = None
    file_paths: List[str] = field(default_factory=list)
    
    # Spark-specific
    advisory_id: Optional[str] = None
    pattern_type: Optional[str] = None
    insight_id: Optional[str] = None
    
    # Parent/child relationships
    parent_trace_id: Optional[str] = None
    child_trace_ids: List[str] = field(default_factory=list)
    
    # Metrics
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['source'] = self.source.value
        d['status'] = self.status.value
        d['timestamp_iso'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TraceEvent:
        # Convert enum strings back to enums
        d = dict(d)
        d['source'] = TraceSource(d.get('source', 'openclaw'))
        d['status'] = TraceStatus(d.get('status', 'pending'))
        if 'evidence' in d and d['evidence']:
            d['evidence'] = TraceEvidence.from_dict(d['evidence'])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class TraceCollector:
    """Collects and normalizes events from multiple Spark sources."""
    
    def __init__(self, spark_dir: Optional[Path] = None):
        self.spark_dir = spark_dir or Path.home() / ".spark"
        self._lock = threading.RLock()
        self._last_poll_time: float = 0.0
        self._processed_ids: set = set()
        
    def _generate_event_id(self, prefix: str = "evt") -> str:
        """Generate unique event ID."""
        return f"{prefix}_{int(time.time()*1000)}_{threading.current_thread().ident}"
    
    def _read_jsonl_tail(self, path: Path, max_lines: int = 100) -> List[Dict]:
        """Read last N lines from a JSONL file."""
        if not path.exists():
            return []
        try:
            lines = []
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return lines[-max_lines:] if len(lines) > max_lines else lines
        except Exception:
            return []
    
    def _read_json_safe(self, path: Path) -> Optional[Dict]:
        """Safely read a JSON file."""
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
        return None
    
    # ---------------------------------------------------------------------
    # Source-specific parsers
    # ---------------------------------------------------------------------
    
    def _extract_user_intent(self, text: str) -> str:
        """Extract clean user intent from message text, removing metadata."""
        if not text:
            return "User input"
        
        # Remove timestamp prefix like "[Fri 2026-02-13 04:02 GMT+4]"
        import re
        text = re.sub(r'\[[A-Za-z]{3}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+[^\]]+\]\s*', '', text)
        
        # Remove message_id line
        text = re.sub(r'\[message_id:[^\]]+\]\s*', '', text)
        
        # Remove pulse mood prefix
        text = re.sub(r'\[Pulse Mood:[^\]]+\]\s*', '', text)
        
        # Remove "Reply in X mood:" prefix
        text = re.sub(r'Reply in \w+ mood:[^\n]*\n?', '', text)
        
        # Clean up whitespace
        text = text.strip()
        
        # Truncate if too long
        if len(text) > 120:
            text = text[:117] + "..."
        
        return text if text else "User input"
    
    def _extract_tool_intent(self, tool_name: str, tool_input: Dict, event_type: str = '') -> tuple:
        """Extract intent description and category from tool execution."""
        if not tool_name:
            return "Execute tool", "tool"
        
        # Normalize tool name
        tool_lower = tool_name.lower()
        
        # Check if this is a shell/exec command even if tool_input is empty
        if tool_lower in ('bash', 'exec', 'shell', 'cmd', 'powershell'):
            if isinstance(tool_input, dict) and tool_input.get('command'):
                cmd = tool_input['command']
                return f"$ {cmd[:100]}", "bash"
            else:
                # Shell exec without visible command (data was in request)
                return f"Run {tool_name} command", "bash"
        
        intent = f"Execute {tool_name}"
        category = "tool"
        
        if isinstance(tool_input, dict):
            # File edits
            if tool_lower in ('edit', 'strreplacefile', 'str_replace_file') or 'old_string' in tool_input:
                path = tool_input.get('file_path') or tool_input.get('path', 'file')
                intent = f"Edit {path}"
                category = "edit"
            
            # File reads
            elif tool_lower in ('read', 'readfile', 'view', 'cat') or tool_input.get('view_range'):
                path = tool_input.get('file_path') or tool_input.get('path', 'file')
                intent = f"Read {path}"
                category = "read"
            
            # File creation/writing
            elif tool_lower in ('write', 'create', 'writefile') or tool_input.get('content') or tool_input.get('new_string'):
                path = tool_input.get('file_path') or tool_input.get('path', 'file')
                intent = f"Write {path}"
                category = "write"
            
            # Search
            elif tool_lower in ('grep', 'search', 'glob', 'find'):
                if tool_input.get('pattern'):
                    intent = f"Search for '{tool_input['pattern'][:50]}'"
                elif tool_input.get('query'):
                    intent = f"Search: {tool_input['query'][:50]}"
                else:
                    intent = f"Search with {tool_name}"
                category = "search"
            
            # Generic file operation
            elif tool_input.get('file_path') or tool_input.get('path'):
                path = tool_input.get('file_path') or tool_input.get('path')
                intent = f"{tool_name} {path}"
                category = "file"
        
        return intent, category
    
    def _parse_queue_event(self, event: Dict, user_intent_cache: Dict[str, str] = None) -> Optional[TraceEvent]:
        """Parse event from Spark queue (events.jsonl)."""
        event_type = event.get('event_type', event.get('type', ''))
        session_id = event.get('session_id', 'unknown')
        
        # Get data and payload
        data = event.get('data', {})
        payload = data.get('payload', {})
        
        # Extract trace_id from multiple possible locations
        trace_id = (
            event.get('trace_id') 
            or data.get('trace_id')
            or payload.get('trace_id')
            or session_id
        )
        
        # Skip if already processed
        event_hash = f"{trace_id}:{event.get('timestamp', event.get('ts', 0))}:{event_type}"
        if event_hash in self._processed_ids:
            return None
        self._processed_ids.add(event_hash)
        
        # Determine intent based on event type
        intent = "Unknown"
        intent_category = None
        role = payload.get('role', '')
        
        if event_type == 'user_prompt':
            text = payload.get('text', '')
            
            # Keep: role=user (explicit user) OR role=None with text (implicit user)
            # Skip: role=assistant (AI responses)
            if role == 'assistant':
                return None  # Skip assistant acknowledgments
            
            if role == 'user' or (role is None and text and len(text.strip()) > 5):
                # This is a user message - extract their intent
                intent = self._extract_user_intent(text)
                intent_category = "user_intent"
            elif not text or len(text.strip()) < 5:
                # Too short to be meaningful
                return None
            else:
                # Fallback - treat as user intent
                intent = self._extract_user_intent(text)
                intent_category = "user_intent"
        
        elif event_type in ('pre_tool', 'post_tool', 'post_tool_failure'):
            # This is a tool execution - use cached user intent if available
            if user_intent_cache and trace_id in user_intent_cache:
                intent = user_intent_cache[trace_id]
                intent_category = "user_intent"
            else:
                tool_name = payload.get('tool_name') or event.get('tool_name')
                tool_input = payload.get('tool_input', {}) or event.get('tool_input', {})
                intent, intent_category = self._extract_tool_intent(tool_name, tool_input, event_type)
        
        elif payload.get('tool_name') or event.get('tool_name'):
            # Fallback for any tool-related event
            if user_intent_cache and trace_id in user_intent_cache:
                intent = user_intent_cache[trace_id]
                intent_category = "user_intent"
            else:
                tool_name = payload.get('tool_name') or event.get('tool_name')
                tool_input = payload.get('tool_input', {}) or event.get('tool_input', {})
                intent, intent_category = self._extract_tool_intent(tool_name, tool_input, event_type)
        
        elif event_type == 'learning':
            # Learning/session events
            cmd = payload.get('command', 'learning')
            if cmd == 'session_start':
                intent = "Session started"
                intent_category = "session"
            elif cmd == 'session_end':
                intent = "Session ended"
                intent_category = "session"
            else:
                intent = f"Learning: {cmd}"
                intent_category = "learning"
        
        elif event_type == 'session_start':
            intent = "Session started"
            intent_category = "session"
        
        elif event_type == 'session_end':
            intent = "Session ended"
            intent_category = "session"
        
        # Determine status from event type and error
        error = event.get('error') or data.get('error') or payload.get('error') or payload.get('is_error')
        status = TraceStatus.SUCCESS
        if error:
            status = TraceStatus.FAIL
        elif event_type == 'pre_tool':
            status = TraceStatus.RUNNING
        elif event_type == 'user_prompt':
            status = TraceStatus.PENDING
        elif event_type == 'post_tool_failure':
            status = TraceStatus.FAIL
        
        # Build evidence from tool result
        evidence = None
        if error:
            evidence = TraceEvidence(
                error_message=str(error)[:500],
            )
        elif payload.get('tool_result'):
            result = str(payload['tool_result'])[:300]
            evidence = TraceEvidence(stdout=result)
        elif payload.get('text'):
            # Use the text field as evidence (description of what happened)
            evidence = TraceEvidence(stdout=payload['text'][:500])
        
        # Get tool name from either payload or top level
        tool_name = payload.get('tool_name') or event.get('tool_name')
        
        # Extract file paths from tool input
        file_paths = []
        tool_input = payload.get('tool_input', {}) or event.get('tool_input', {}) or {}
        if isinstance(tool_input, dict):
            for key in ['file_path', 'path']:
                if key in tool_input and tool_input[key]:
                    file_paths.append(str(tool_input[key]))
        
        # Build richer action description
        action = tool_name
        if tool_input and isinstance(tool_input, dict):
            # For bash/exec, show the command
            if tool_input.get('command'):
                action = f"{tool_name}: {tool_input['command'][:80]}"
            # For edit/write, show the file
            elif tool_input.get('file_path') or tool_input.get('path'):
                path = tool_input.get('file_path') or tool_input.get('path')
                action = f"{tool_name} {path}"
            # For read/view, show what was read
            elif tool_input.get('view_range'):
                action = f"{tool_name} (lines {tool_input['view_range']})"
        
        # FILTER: Skip low-value/generic intents
        if intent and len(intent.strip()) < 10 and intent_category == 'user_intent':
            return None  # Skip short responses like "Yes", "Ok"
        
        if intent == 'Learning: learning':
            return None  # Skip generic learning events
        
        if intent == 'Run exec command' and not tool_input.get('command'):
            return None  # Skip generic exec without actual command
        
        # FILTER: Skip reads of internal Spark files
        if intent_category == 'read' and intent:
            skip_patterns = ['SPARK_', '.openclaw/workspace/SPARK_', 'spark_reports/']
            if any(p in intent for p in skip_patterns):
                return None
        
        return TraceEvent(
            trace_id=trace_id,
            event_id=self._generate_event_id("queue"),
            timestamp=event.get('timestamp', event.get('ts', time.time())),
            source=TraceSource.OPENCLAW,
            intent=intent,
            intent_category=intent_category,
            action=tool_name,
            action_type=intent_category or tool_name,
            evidence=evidence,
            status=status,
            outcome_summary="Success" if not error else f"Error: {str(error)[:100]}",
            session_id=session_id,
            project_path=payload.get('cwd') or event.get('cwd') or data.get('cwd'),
            file_paths=file_paths,
            confidence_before=0.7 if not error else 0.3,
        )
    
    def _parse_advisory_event(self, event: Dict) -> Optional[TraceEvent]:
        """Parse advisory engine event."""
        # FILTER: Skip most advisory events - they're telemetry, not real work
        # Only keep actual advice that was emitted to the user
        if not event.get('emitted'):
            return None
        
        # Skip meta-planning task planes (telemetry, not real work)
        task_plane = event.get('task_plane', '')
        if task_plane in ('research_decision', 'build_delivery', 'orchestration_execution'):
            return None
        
        advisory_id = event.get('advisory_id') or event.get('id') or event.get('packet_id')
        trace_id = event.get('trace_id') or f"adv_{advisory_id or 'unknown'}"
        
        # Build intent from available fields
        intent_parts = []
        if event.get('intent_family'):
            intent_parts.append(event['intent_family'])
        elif event.get('event'):
            intent_parts.append(event['event'])
        if event.get('tool'):
            intent_parts.append(f"tool: {event['tool']}")
        intent = ' | '.join(intent_parts) if intent_parts else 'Advisory check'
        
        # Build action description
        action_parts = []
        if event.get('route'):
            action_parts.append(f"Route: {event['route']}")
        if event.get('advice'):
            action_parts.append(str(event['advice'])[:100])
        action = ' | '.join(action_parts) if action_parts else 'Advice retrieval'
        
        # Determine status
        emitted = event.get('emitted', False)
        error = event.get('error_kind') or event.get('error_code')
        if error:
            status = TraceStatus.FAIL
        elif emitted:
            status = TraceStatus.SUCCESS
        else:
            status = TraceStatus.DEFERRED
        
        return TraceEvent(
            trace_id=trace_id,
            event_id=self._generate_event_id("adv"),
            timestamp=event.get('timestamp', event.get('ts', time.time())),
            source=TraceSource.SPARK_ADVISORY,
            intent=intent,
            intent_category=event.get('task_plane'),
            action=action,
            action_type="advisory",
            status=status,
            outcome_summary=event.get('delivery_mode', 'unknown'),
            advisory_id=advisory_id,
            confidence_before=0.7 if emitted else 0.3,
            session_id=event.get('session_id'),
        )
    
    def _parse_feedback_report(self, report: Dict) -> Optional[TraceEvent]:
        """Parse agent feedback report."""
        report_id = report.get('report_id', 'unknown')
        trace_id = report.get('trace_id', f"rpt_{report_id}")
        
        return TraceEvent(
            trace_id=trace_id,
            event_id=self._generate_event_id("fb"),
            timestamp=report.get('submitted_at', time.time()),
            source=TraceSource.AGENT_FEEDBACK,
            intent=report.get('task', 'Agent task'),
            intent_category=report.get('category'),
            action=report.get('action_taken', ''),
            action_type=report.get('tool_used'),
            status=TraceStatus.SUCCESS if report.get('success') else TraceStatus.FAIL,
            outcome_summary=report.get('outcome', 'unknown'),
            lesson=report.get('lesson_learned'),
            lesson_confidence=report.get('confidence', 0.0),
            confidence_before=report.get('confidence_before', 0.5),
            confidence_after=report.get('confidence_after', 0.5),
        )
    
    def _parse_bridge_heartbeat(self, heartbeat: Dict) -> Optional[TraceEvent]:
        """Parse bridge worker heartbeat as meta-trace."""
        stats = heartbeat.get('stats', {})
        
        # Build outcome summary with key stats
        errors = stats.get('errors', [])
        outcome = f"Learnings: {stats.get('content_learned', 0)}, Patterns: {stats.get('pattern_processed', 0)}"
        if errors:
            outcome += f", Errors: {len(errors)}"
        if stats.get('memory', {}).get('auto_saved'):
            outcome += f", Memories: {stats['memory']['auto_saved']}"
        
        return TraceEvent(
            trace_id="bridge_meta",
            event_id=self._generate_event_id("hb"),
            timestamp=heartbeat.get('ts', time.time()),
            source=TraceSource.BRIDGE_HEARTBEAT,
            intent="Bridge cycle processing",
            action=f"Processed {stats.get('pattern_processed', 0)} patterns",
            status=TraceStatus.SUCCESS if not errors else TraceStatus.FAIL,
            outcome_summary=outcome,
        )
    
    def _parse_pattern_event(self, pattern: Dict) -> Optional[TraceEvent]:
        """Parse detected pattern."""
        pattern_id = pattern.get('pattern_id', 'unknown')
        pattern_type = pattern.get('type', 'unknown')
        
        # FILTER: Skip unknown patterns - they're noise
        if pattern_type == 'unknown':
            return None
        
        return TraceEvent(
            trace_id=f"pat_{pattern_id}",
            event_id=self._generate_event_id("pat"),
            timestamp=pattern.get('detected_at', time.time()),
            source=TraceSource.PATTERN_DETECTED,
            intent=f"Detected {pattern_type} pattern",
            intent_category=pattern_type,
            pattern_type=pattern_type,
            status=TraceStatus.SUCCESS,
            outcome_summary=pattern.get('description', '')[:200],
            confidence_before=pattern.get('confidence', 0.5),
            session_id=pattern.get('session_id'),
        )
    
    def _parse_insight_event(self, insight: Dict) -> Optional[TraceEvent]:
        """Parse cognitive insight."""
        insight_id = insight.get('id', 'unknown')
        
        return TraceEvent(
            trace_id=f"ins_{insight_id}",
            event_id=self._generate_event_id("ins"),
            timestamp=insight.get('timestamp', time.time()),
            source=TraceSource.INSIGHT_LEARNED,
            intent=f"Learned: {insight.get('category', 'insight')}",
            lesson=insight.get('signal', insight.get('text', '')),
            lesson_confidence=insight.get('confidence', 0.0),
            status=TraceStatus.SUCCESS,
            outcome_summary=f"Validated {insight.get('times_validated', 0)} times",
            insight_id=insight_id,
            confidence_before=insight.get('confidence_before', 0.6),
            confidence_after=insight.get('confidence', 0.6),
        )
    
    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    
    def poll_all_sources(self) -> List[TraceEvent]:
        """Poll all Spark sources and return normalized trace events."""
        events: List[TraceEvent] = []
        
        # Cache for user intents by trace_id - maps trace_id -> intent string
        user_intent_cache: Dict[str, str] = {}
        
        with self._lock:
            # 1. Queue events (main source) - read more to capture user prompts
            queue_file = self.spark_dir / "queue" / "events.jsonl"
            raw_events = self._read_jsonl_tail(queue_file, max_lines=200)
            
            # First pass: collect user intents by trace_id
            for raw_event in raw_events:
                event_type = raw_event.get('event_type', raw_event.get('type', ''))
                if event_type == 'user_prompt':
                    data = raw_event.get('data', {})
                    payload = data.get('payload', {})
                    if payload.get('role') == 'user':
                        trace_id = (
                            raw_event.get('trace_id') 
                            or data.get('trace_id')
                            or payload.get('trace_id')
                            or raw_event.get('session_id', 'unknown')
                        )
                        text = payload.get('text', '')
                        if text:
                            user_intent_cache[trace_id] = self._extract_user_intent(text)
            
            # Second pass: parse all events and enrich with user intent
            for raw_event in raw_events:
                evt = self._parse_queue_event(raw_event, user_intent_cache)
                if evt:
                    events.append(evt)
            
            # 2. Advisory events
            advisory_file = self.spark_dir / "advisory_engine.jsonl"
            for raw_event in self._read_jsonl_tail(advisory_file, max_lines=20):
                evt = self._parse_advisory_event(raw_event)
                if evt:
                    events.append(evt)
            
            # 3. Agent feedback reports
            reports_dir = Path("spark_reports")
            if reports_dir.exists():
                for report_file in sorted(reports_dir.glob("*.json"))[-10:]:
                    report = self._read_json_safe(report_file)
                    if report:
                        evt = self._parse_feedback_report(report)
                        if evt:
                            events.append(evt)
            
            # 4. Bridge heartbeat
            heartbeat_file = self.spark_dir / "bridge_worker_heartbeat.json"
            heartbeat = self._read_json_safe(heartbeat_file)
            if heartbeat:
                evt = self._parse_bridge_heartbeat(heartbeat)
                if evt:
                    events.append(evt)
            
            # 5. Detected patterns
            patterns_file = self.spark_dir / "detected_patterns.jsonl"
            for raw_pattern in self._read_jsonl_tail(patterns_file, max_lines=20):
                evt = self._parse_pattern_event(raw_pattern)
                if evt:
                    events.append(evt)
            
            # 6. Cognitive insights
            insights_file = self.spark_dir / "cognitive_insights.json"
            insights_data = self._read_json_safe(insights_file)
            if insights_data and 'insights' in insights_data:
                for raw_insight in insights_data['insights'][-20:]:
                    evt = self._parse_insight_event(raw_insight)
                    if evt:
                        events.append(evt)
        
        self._last_poll_time = time.time()
        return sorted(events, key=lambda e: e.timestamp, reverse=True)
    
    def poll_recent(self, since: float) -> List[TraceEvent]:
        """Poll only events since timestamp."""
        all_events = self.poll_all_sources()
        return [e for e in all_events if e.timestamp > since]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            "last_poll": self._last_poll_time,
            "processed_ids_count": len(self._processed_ids),
            "spark_dir": str(self.spark_dir),
        }


def demo_collector():
    """Demo the collector - run standalone to see what events are found."""
    collector = TraceCollector()
    events = collector.poll_all_sources()
    
    print(f"Found {len(events)} trace events\n")
    print("=" * 80)
    
    for evt in events[:10]:
        print(f"\n[{evt.source.value}] {evt.status.value.upper()}")
        print(f"  Intent: {evt.intent[:80]}...")
        print(f"  Action: {evt.action or 'N/A'}")
        print(f"  Outcome: {evt.outcome_summary or 'N/A'}")
        if evt.lesson:
            print(f"  Lesson: {evt.lesson[:80]}...")
        print(f"  Time: {datetime.fromtimestamp(evt.timestamp).strftime('%H:%M:%S')}")


if __name__ == "__main__":
    demo_collector()
