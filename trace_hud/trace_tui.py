#!/usr/bin/env python3
"""trace_tui.py - Rich terminal dashboard for the Decision Trace HUD.

Renders:
- Top bar KPIs (active tasks, success rate, blockers, advice acted %)
- Active traces table with Intent/Action/Evidence/Outcome/Lesson
- Recent history
- Real-time updates
"""

from __future__ import annotations

import time
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# Rich imports
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from rich import box

from trace_hud.trace_state import ActiveTrace, TracePhase, TraceState, TraceStatus


@dataclass
class TUIConfig:
    """Configuration for the TUI."""
    refresh_rate: float = 0.5  # seconds
    max_active_rows: int = 10
    max_history_rows: int = 5
    show_completed: bool = True
    color_scheme: str = "default"


class TraceTUI:
    """Rich terminal UI for the Decision Trace HUD."""
    
    # Color scheme
    COLORS = {
        'pending': 'yellow',
        'running': 'blue',
        'success': 'green',
        'fail': 'red',
        'deferred': 'magenta',
        'blocked': 'red3',
        'cancelled': 'dim',
        'intent': 'cyan',
        'action': 'blue',
        'evidence': 'yellow',
        'outcome': 'white',
        'lesson': 'green',
        'phase_idle': 'dim',
        'phase_intent': 'cyan',
        'phase_action': 'blue',
        'phase_executing': 'yellow',
        'phase_evidence': 'magenta',
        'phase_outcome': 'white',
        'phase_lesson': 'green',
        'phase_complete': 'dim',
    }
    
    def __init__(self, config: Optional[TUIConfig] = None):
        self.config = config or TUIConfig()
        self.console = Console()
        self.state: Optional[TraceState] = None
        self._live: Optional[Live] = None
        self._start_time = time.time()
    
    def _phase_color(self, phase: TracePhase) -> str:
        """Get color for phase."""
        return self.COLORS.get(f'phase_{phase.value}', 'white')
    
    def _status_color(self, status: TraceStatus) -> str:
        """Get color for status."""
        return self.COLORS.get(status.value, 'white')
    
    def _make_header(self, kpis: Dict[str, Any]) -> Panel:
        """Create the KPI header panel."""
        # Format KPIs
        active = kpis.get('active_tasks', 0)
        recent = kpis.get('recent_active', 0)
        blocked = kpis.get('blocked_tasks', 0)
        success_rate = kpis.get('success_rate_100', 0)
        advisory_rate = kpis.get('advisory_action_rate_100', 0)
        lessons = kpis.get('lessons_learned', 0)
        
        # Build KPI text
        kpi_text = Text()
        kpi_text.append("┌ ", style="dim")
        kpi_text.append(f"Active: {active}", style="cyan bold")
        if recent > 0:
            kpi_text.append(f" (recent: {recent})", style="cyan")
        kpi_text.append(" │ ", style="dim")
        
        # Success rate with color
        success_style = "green" if success_rate >= 80 else "yellow" if success_rate >= 50 else "red"
        kpi_text.append(f"Success: {success_rate}%", style=success_style + " bold")
        kpi_text.append(" │ ", style="dim")
        
        # Blockers
        blocker_style = "red bold" if blocked > 0 else "dim"
        kpi_text.append(f"Blocked: {blocked}", style=blocker_style)
        kpi_text.append(" │ ", style="dim")
        
        # Advisory rate
        advisory_style = "green" if advisory_rate >= 60 else "yellow"
        kpi_text.append(f"Advice Acted: {advisory_rate}%", style=advisory_style)
        kpi_text.append(" │ ", style="dim")
        
        # Lessons
        kpi_text.append(f"Lessons: {lessons}", style="green")
        kpi_text.append(" ┐", style="dim")
        
        # Phase distribution bar
        phases = kpis.get('phase_distribution', {})
        if phases:
            phase_text = Text("\n")
            phase_text.append("└─ Phases: ", style="dim")
            for phase, count in sorted(phases.items()):
                color = self._phase_color(TracePhase(phase))
                phase_text.append(f"{phase}:{count} ", style=color)
            phase_text.append("┘", style="dim")
            kpi_text.append(phase_text)
        
        return Panel(
            kpi_text,
            title="[bold cyan]⚡ Spark Decision Trace HUD",
            subtitle=f"[dim]Runtime: {int(time.time() - self._start_time)}s[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    
    def _make_active_traces_table(self, traces: List[ActiveTrace]) -> Table:
        """Create the active traces table."""
        table = Table(
            title="[bold]Active Decision Traces",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold magenta",
            expand=True,
        )
        
        # Columns
        table.add_column("Phase", width=10, justify="center")
        table.add_column("Status", width=8, justify="center")
        table.add_column("Intent", width=25, no_wrap=True)
        table.add_column("Action", width=20, no_wrap=True)
        table.add_column("Outcome", width=15, no_wrap=True)
        table.add_column("Lesson", width=20, no_wrap=True)
        
        # Rows
        for trace in traces[:self.config.max_active_rows]:
            phase_color = self._phase_color(trace.phase)
            status_color = self._status_color(trace.status)
            
            phase_text = f"[bold {phase_color}]{trace.phase.value[:8]}[/]"
            status_text = f"[{status_color}]{trace.status.value[:7]}[/]"
            
            # Intent with category if available
            intent = trace.intent[:23] + "…" if len(trace.intent) > 23 else trace.intent
            intent_text = f"[cyan]{intent}[/]"
            
            # Action
            action = trace.action or "—"
            action = action[:18] + "…" if len(action) > 18 else action
            action_text = f"[blue]{action}[/]"
            
            # Outcome
            outcome = trace.outcome or trace.evidence_summary or "—"
            outcome = outcome[:13] + "…" if len(outcome) > 13 else outcome
            outcome_color = "green" if trace.status == TraceStatus.SUCCESS else \
                           "red" if trace.status == TraceStatus.FAIL else "yellow"
            outcome_text = f"[{outcome_color}]{outcome}[/]"
            
            # Lesson
            lesson = trace.lesson or "—"
            lesson = lesson[:18] + "…" if len(lesson) > 18 else lesson
            lesson_text = f"[dim green]{lesson}[/]" if not trace.lesson else f"[green]{lesson}[/]"
            
            table.add_row(
                phase_text,
                status_text,
                intent_text,
                action_text,
                outcome_text,
                lesson_text,
            )
        
        if not traces:
            table.add_row(
                "[dim]—[/]", "[dim]—[/]", "[dim]No active traces[/]",
                "[dim]—[/]", "[dim]—[/]", "[dim]—[/]"
            )
        
        return table
    
    def _make_recent_history_table(self, traces: List[ActiveTrace]) -> Table:
        """Create recent completed traces table."""
        table = Table(
            title="[bold dim]Recent Completed Traces",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold dim",
            expand=True,
            padding=(0, 1),
        )
        
        table.add_column("Time", width=8, justify="right")
        table.add_column("Intent", width=30, no_wrap=True)
        table.add_column("Result", width=10)
        table.add_column("Duration", width=10, justify="right")
        
        for trace in traces[:self.config.max_history_rows]:
            # Time ago
            ago = int(time.time() - trace.last_activity)
            if ago < 60:
                time_str = f"{ago}s"
            else:
                time_str = f"{ago//60}m"
            
            # Intent
            intent = trace.intent[:28] + "…" if len(trace.intent) > 28 else trace.intent
            
            # Result
            if trace.status == TraceStatus.SUCCESS:
                result = "[green]✓ success[/]"
            elif trace.status == TraceStatus.FAIL:
                result = "[red]✗ fail[/]"
            else:
                result = f"[dim]{trace.status.value}[/]"
            
            # Duration
            duration = trace.metrics.duration_ms
            if duration:
                if duration < 1000:
                    duration_str = f"{duration}ms"
                else:
                    duration_str = f"{duration//1000}s"
            else:
                duration_str = "—"
            
            table.add_row(
                f"[dim]{time_str} ago[/]",
                intent,
                result,
                f"[dim]{duration_str}[/]"
            )
        
        return table
    
    def _make_blocked_panel(self, traces: List[ActiveTrace]) -> Optional[Panel]:
        """Create panel showing blocked traces."""
        blocked = [t for t in traces if t.status == TraceStatus.BLOCKED]
        if not blocked:
            return None
        
        content = Text()
        for trace in blocked[:5]:
            content.append(f"• ", style="red")
            content.append(f"{trace.intent[:40]}", style="white")
            if trace.blockers:
                content.append(f" → {trace.blockers[-1][:30]}", style="red dim")
            content.append("\n")
        
        return Panel(
            content,
            title="[bold red]⚠ Blocked Traces[/bold red]",
            border_style="red",
            box=box.ROUNDED,
        )
    
    def _make_layout(self, state: TraceState) -> Layout:
        """Create the full layout."""
        # Get data
        kpis = state.get_kpis()
        active_traces = state.get_active_traces()
        recent_traces = state.get_recent_completed(10)
        
        # Create layout
        layout = Layout()
        
        # Split into sections
        layout.split_column(
            Layout(name="header", size=6),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=8),
        )
        
        # Header with KPIs
        layout["header"].update(self._make_header(kpis))
        
        # Main section - active traces
        main_content = self._make_active_traces_table(active_traces)
        
        # Add blocked panel if any
        blocked_panel = self._make_blocked_panel(active_traces)
        if blocked_panel:
            layout["main"].split_row(
                Layout(main_content, ratio=3),
                Layout(blocked_panel, ratio=1),
            )
        else:
            layout["main"].update(main_content)
        
        # Footer - recent history
        layout["footer"].update(self._make_recent_history_table(recent_traces))
        
        return layout
    
    def _render_frame(self) -> Layout:
        """Render a single frame."""
        if self.state is None:
            # Loading state
            layout = Layout()
            layout.update(Panel(
                "[yellow]Initializing...[/]",
                title="Spark Trace HUD",
                border_style="cyan",
            ))
            return layout
        
        return self._make_layout(self.state)
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def set_state(self, state: TraceState) -> None:
        """Set the state manager."""
        self.state = state
    
    def start(self) -> None:
        """Start the live TUI."""
        self._live = Live(
            self._render_frame(),
            console=self.console,
            refresh_per_second=1.0 / self.config.refresh_rate,
            screen=True,  # Full-screen mode
        )
        self._live.start()
    
    def stop(self) -> None:
        """Stop the live TUI."""
        if self._live:
            self._live.stop()
            self._live = None
    
    def update(self) -> None:
        """Update the display (call periodically)."""
        if self._live:
            self._live.update(self._render_frame())
    
    def refresh(self) -> None:
        """Force refresh."""
        self.update()
    
    def __enter__(self) -> TraceTUI:
        self.start()
        return self
    
    def __exit__(self, *args) -> None:
        self.stop()
    
    # -------------------------------------------------------------------------
    # Static output (for non-interactive mode)
    # -------------------------------------------------------------------------
    
    def render_snapshot(self, state: TraceState) -> None:
        """Render a single snapshot (non-interactive)."""
        self.state = state
        layout = self._make_layout(state)
        self.console.print(layout)


def demo_tui():
    """Demo the TUI with mock data."""
    from trace_hud.trace_collector import TraceEvent, TraceSource, TraceStatus
    
    # Create mock state
    state = TraceState()
    
    # Add some mock traces
    events = [
        TraceEvent(
            trace_id="fix_auth_1",
            event_id="evt_1",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Fix authentication bug in login flow",
            status=TraceStatus.RUNNING,
        ),
        TraceEvent(
            trace_id="refactor_db_1",
            event_id="evt_2",
            timestamp=time.time(),
            source=TraceSource.TOOL_CALL,
            intent="Refactor database connection pool",
            action="Edit src/db.py",
            action_type="edit",
            status=TraceStatus.SUCCESS,
            lesson="Always close connections in finally blocks",
        ),
        TraceEvent(
            trace_id="add_tests_1",
            event_id="evt_3",
            timestamp=time.time(),
            source=TraceSource.USER_PROMPT,
            intent="Add unit tests for user service",
            status=TraceStatus.BLOCKED,
        ),
    ]
    
    state.ingest_events(events)
    
    # Add a blocker to the blocked trace
    blocked = state.get_trace("add_tests_1")
    if blocked:
        blocked.add_blocker("Missing test fixtures for auth mocks")
    
    # Mark one as completed in history
    completed = state.get_trace("refactor_db_1")
    if completed:
        completed.status = TraceStatus.SUCCESS
        completed.outcome = "Refactored successfully"
        completed.metrics.finish(confidence=0.9)
        state._history.append(completed)
    
    # Render snapshot
    tui = TraceTUI()
    tui.render_snapshot(state)


if __name__ == "__main__":
    demo_tui()
