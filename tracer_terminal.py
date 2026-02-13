#!/usr/bin/env python3
"""
Tracer Terminal - Intelligence Loop Dashboard
=============================================

Shows the real intelligence work: Intent → Action → Evidence → Outcome → Lesson

Usage:
    python tracer_terminal.py           # One-time snapshot
    python tracer_terminal.py --live    # Live updating view (Ctrl+C to exit)
    python tracer_terminal.py --web     # Open web dashboard

Filters OUT:
- Advisory planning noise
- Internal meta-events  
- Empty assistant acknowledgments

Shows ONLY:
- User intents (what we're trying to do)
- Tool executions (commands, edits, reads)
- Actual results (stdout, stderr, status codes)
- Distilled lessons (what was learned)
"""

import json
import time
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).parent))

from trace_hud import TraceCollector, TraceEvent, TraceSource, TraceStatus

# ANSI colors - disable if terminal doesn't support
import os
if os.environ.get('NO_COLOR') or os.name == 'nt':
    CYAN = GREEN = YELLOW = RED = MAGENTA = BLUE = WHITE = DIM = BOLD = RESET = CLEAR = ""
else:
    CYAN, GREEN, YELLOW, RED = "\033[36m", "\033[32m", "\033[33m", "\033[31m"
    MAGENTA, BLUE, WHITE = "\033[35m", "\033[34m", "\033[37m"
    DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
    CLEAR = "\033[2J\033[H"

# Filter configuration
SKIP_CATEGORIES = {'research_decision', 'build_delivery', 'unknown', 'advisory'}
SKIP_INTENT_PREFIXES = [
    'research_decision_support', 'emergent_other', 'knowledge_alignment',
    'team_coordination', 'deployment_ops', 'orchestration_execution',
]
SKIP_TRACE_PREFIXES = ['advisory-', 'bridge_', 'bridge-', 'pattern_']
SKIP_GENERIC_INTENTS = ['execute process', 'learning: learning']


def truncate(s: str, max_len: int = 60) -> str:
    return s[:max_len-3] + "..." if s and len(s) > max_len else (s or "")


def format_evidence(evidence: Any) -> str:
    """Format evidence into a readable summary."""
    if not evidence:
        return f"{DIM}no signal{RESET}"
    
    parts = []
    
    if hasattr(evidence, 'status_code') and evidence.status_code is not None:
        color = GREEN if evidence.status_code in (0, 200) else RED
        parts.append(f"{color}exit:{evidence.status_code}{RESET}")
    
    if hasattr(evidence, 'stdout') and evidence.stdout:
        stdout = evidence.stdout.strip()
        if stdout:
            lines = stdout.split('\n')
            if len(lines) == 1:
                parts.append(f"{GREEN}[OK]{RESET} {truncate(stdout, 50)}")
            else:
                first = lines[0].strip()
                parts.append(f"{GREEN}[OK]{RESET} {truncate(first, 40)} ({len(lines)} lines)")
    
    if hasattr(evidence, 'error_message') and evidence.error_message:
        parts.append(f"{RED}{truncate(evidence.error_message, 40)}{RESET}")
    
    return " | ".join(parts) if parts else f"{DIM}no details{RESET}"


def generate_lesson(trace_events: List[TraceEvent]) -> Optional[str]:
    """Generate a lesson from the trace events."""
    if not trace_events:
        return None
    
    latest = trace_events[-1]
    
    # Success after multiple attempts = persistence
    if latest.status == TraceStatus.SUCCESS and len(trace_events) > 2:
        return "Multiple attempts led to success"
    
    # HTTP errors = service availability
    for e in trace_events:
        if e.evidence and hasattr(e.evidence, 'stdout') and e.evidence.stdout:
            if '404' in e.evidence.stdout:
                return "Service endpoint returned 404 - may not be running"
            if 'Connection refused' in e.evidence.stdout:
                return "Connection refused - check if service is started"
    
    # File edits = validation
    file_actions = [e for e in trace_events if e.action_type in ('edit', 'write')]
    if file_actions and latest.status == TraceStatus.SUCCESS:
        return "File modifications applied successfully"
    
    return None


def filter_real_work(events: List[TraceEvent]) -> List[TraceEvent]:
    """Filter to only real intelligence work, not advisory noise."""
    filtered = []
    for e in events:
        if e.intent_category in SKIP_CATEGORIES:
            continue
        intent_lower = (e.intent or "").lower()
        if any(intent_lower.startswith(prefix) for prefix in SKIP_INTENT_PREFIXES):
            continue
        if any(e.trace_id.startswith(prefix) for prefix in SKIP_TRACE_PREFIXES):
            continue
        if not e.intent or e.intent == "(no intent captured)":
            continue
        if any(e.intent.lower() == gi for gi in SKIP_GENERIC_INTENTS):
            continue
        if e.source == TraceSource.PATTERN_DETECTED:
            continue
        if e.source == TraceSource.BRIDGE_HEARTBEAT:
            continue
        filtered.append(e)
    return filtered


def render_trace(trace_id: str, trace_events: List[TraceEvent]) -> str:
    """Render a single trace's intelligence loop."""
    lines = []
    trace_events.sort(key=lambda e: e.timestamp)
    latest = trace_events[-1]
    
    # Header
    lines.append(f"{CYAN}{trace_id[:16]}{RESET} {DIM}({len(trace_events)} events){RESET}")
    
    # INTENT
    intent_events = [e for e in trace_events if e.intent_category == 'user_intent']
    intent = intent_events[0].intent if intent_events else trace_events[0].intent
    lines.append(f"  {BOLD}INTENT:{RESET}  {WHITE}{truncate(intent, 80)}{RESET}")
    
    # ACTIONS (deduplicated)
    actions = [e for e in trace_events if e.action]
    seen = set()
    for e in actions:
        key = (e.action, round(e.timestamp, 1))
        if key not in seen:
            seen.add(key)
            action_type = e.action_type or "exec"
            color = BLUE if action_type == "read" else MAGENTA if action_type in ("edit", "write") else CYAN
            action_desc = truncate(e.action, 70)
            lines.append(f"  {BOLD}ACTION:{RESET} {color}[{action_type}]{RESET} {action_desc}")
            if e.evidence:
                ev_str = format_evidence(e.evidence)
                if ev_str != f"{DIM}no details{RESET}":
                    lines.append(f"  {BOLD}SIGNAL:{RESET} {ev_str}")
    
    # OUTCOME
    if latest.status == TraceStatus.SUCCESS:
        outcome = f"{GREEN}[OK] SUCCESS{RESET}"
    elif latest.status == TraceStatus.FAIL:
        outcome = f"{RED}[FAIL] FAILED{RESET}"
    else:
        outcome = f"{DIM}o {latest.status.value.upper()}{RESET}"
    lines.append(f"  {BOLD}RESULT:{RESET}  {outcome}")
    
    # LESSON
    lessons = [e for e in trace_events if e.lesson]
    if lessons:
        lines.append(f"  {BOLD}LESSON:{RESET} {YELLOW}{truncate(lessons[-1].lesson, 80)}{RESET}")
    else:
        lesson = generate_lesson(trace_events)
        if lesson:
            lines.append(f"  {BOLD}LESSON:{RESET} {DIM}{lesson}{RESET}")
    
    lines.append("")
    return "\n".join(lines)


def run_snapshot():
    """Run a one-time snapshot."""
    collector = TraceCollector()
    events = collector.poll_all_sources()
    real_events = filter_real_work(events)
    
    print(f"{BOLD}Spark Intelligence Snapshot{RESET}")
    print(f"{DIM}{'-' * 100}{RESET}")
    print("")
    
    # Group by trace
    traces = defaultdict(list)
    for e in real_events:
        traces[e.trace_id].append(e)
    
    # Show recent traces
    sorted_traces = sorted(traces.items(), key=lambda x: max(e.timestamp for e in x[1]), reverse=True)[:10]
    
    for trace_id, trace_events in sorted_traces:
        print(render_trace(trace_id, trace_events))
    
    # KPIs
    print(f"{DIM}{'-' * 100}{RESET}")
    
    recent = set(e.trace_id for e in real_events if time.time() - e.timestamp < 300)
    completed = [e for e in real_events if e.status in (TraceStatus.SUCCESS, TraceStatus.FAIL)]
    last_20 = sorted(completed, key=lambda e: e.timestamp, reverse=True)[:20]
    success_rate = (sum(1 for e in last_20 if e.status == TraceStatus.SUCCESS) / len(last_20) * 100) if last_20 else 0
    blocked = len(set(e.trace_id for e in real_events if e.status == TraceStatus.BLOCKED))
    lessons = len([e for e in real_events if e.lesson or generate_lesson([e])])
    
    kpis = [
        f"{CYAN}Active:{RESET} {BOLD}{len(recent)}{RESET}",
        f"{GREEN}Success:{RESET} {BOLD}{success_rate:.0f}%{RESET}",
        f"{RED}Blocked:{RESET} {BOLD}{blocked}{RESET}",
        f"{YELLOW}Lessons:{RESET} {BOLD}{lessons}{RESET}",
    ]
    print(" | ".join(kpis))
    print("")
    print(f"{DIM}Showing: Intent -> Action -> Evidence -> Outcome -> Lesson{RESET}")
    print(f"{DIM}Filtered: Advisory noise, meta-planning, empty events{RESET}")


def run_live():
    """Run live updating view."""
    collector = TraceCollector()
    
    print(f"{CLEAR}{BOLD}Spark Intelligence Tracer{RESET} {DIM}(Live){RESET}")
    print(f"{DIM}Press Ctrl+C to exit{RESET}")
    print("")
    
    try:
        while True:
            events = collector.poll_all_sources()
            real_events = filter_real_work(events)
            
            # Clear screen
            print(CLEAR, end="")
            print(f"{BOLD}Spark Intelligence Tracer{RESET} {DIM}(Live) {datetime.now().strftime('%H:%M:%S')}{RESET}")
            
            # Group by trace
            traces = defaultdict(list)
            for e in real_events:
                traces[e.trace_id].append(e)
            
            # Show top 5 recent
            sorted_traces = sorted(traces.items(), key=lambda x: max(e.timestamp for e in x[1]), reverse=True)[:5]
            
            for trace_id, trace_events in sorted_traces:
                print(render_trace(trace_id, trace_events))
            
            print(f"{DIM}{'-' * 100}{RESET}")
            print(f"{DIM}Active traces: {len(traces)} | Events: {len(real_events)} | Press Ctrl+C to exit{RESET}")
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print(f"\n{DIM}Tracer stopped.{RESET}")


def open_web_dashboard():
    """Open the web dashboard."""
    import subprocess
    import sys
    
    # Start the dashboard in background
    print("Starting web dashboard on http://localhost:8777/ ...")
    subprocess.Popen([sys.executable, "tracer_dashboard.py"], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    
    # Wait a moment and open browser
    time.sleep(2)
    webbrowser.open("http://localhost:8777/")
    print("Dashboard opened in browser!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Spark Intelligence Tracer")
    parser.add_argument("--live", action="store_true", help="Live updating view")
    parser.add_argument("--web", action="store_true", help="Open web dashboard")
    args = parser.parse_args()
    
    if args.web:
        open_web_dashboard()
    elif args.live:
        run_live()
    else:
        run_snapshot()
