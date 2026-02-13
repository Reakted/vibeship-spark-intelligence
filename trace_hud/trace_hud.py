#!/usr/bin/env python3
"""trace_hud.py - Decision Trace HUD (CLI) main entry point.

Real-time observability for Spark intelligence loops.

Usage:
    python trace_hud/trace_hud.py              # Start interactive HUD
    python trace_hud/trace_hud.py --snapshot   # Single snapshot and exit
    python trace_hud/trace_hud.py --replay     # Replay from store
    python trace_hud/trace_hud.py --export     # Export to JSON
    
    # Keyboard shortcuts (interactive mode)
    q / Ctrl+C    Quit
    r             Force refresh
    p             Pause/unpause updates
    s             Save snapshot
    h             Show help
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from trace_hud.trace_collector import TraceCollector
from trace_hud.trace_state import TraceState
from trace_hud.trace_store import TraceStore
from trace_hud.trace_tui import TraceTUI, TUIConfig


class DecisionTraceHUD:
    """Main orchestrator for the Decision Trace HUD."""
    
    def __init__(
        self,
        spark_dir: Optional[Path] = None,
        store_dir: Optional[Path] = None,
        refresh_rate: float = 1.0,
    ):
        self.spark_dir = spark_dir
        self.refresh_rate = refresh_rate
        
        # Components
        self.collector = TraceCollector(spark_dir=spark_dir)
        self.state = TraceState()
        self.store = TraceStore(store_dir=store_dir)
        
        # TUI
        config = TUIConfig(refresh_rate=refresh_rate)
        self.tui = TraceTUI(config=config)
        self.tui.set_state(self.state)
        
        # Control
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        
        # Stats
        self._poll_count = 0
        self._last_poll = 0.0
        self._events_processed = 0
    
    def _poll_loop(self) -> None:
        """Background polling loop."""
        while not self._stop_event.is_set():
            if not self._paused:
                try:
                    self._poll_once()
                except Exception as e:
                    # Log error but keep running
                    print(f"[HUD Error] Poll failed: {e}", file=sys.stderr)
            
            # Wait for next poll
            self._stop_event.wait(timeout=self.refresh_rate)
    
    def _poll_once(self) -> None:
        """Single poll cycle."""
        # Poll for new events
        events = self.collector.poll_all_sources()
        
        if events:
            # Update state
            self.state.ingest_events(events)
            
            # Persist to store
            self.store.append_many(events)
            
            self._events_processed += len(events)
        
        # Cleanup stale traces
        self.state.cleanup_stale(timeout_seconds=300)
        
        self._poll_count += 1
        self._last_poll = time.time()
    
    def _handle_signal(self, signum, frame) -> None:
        """Handle shutdown signals."""
        self.stop()
    
    def start(self) -> None:
        """Start the HUD."""
        self._running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Initial poll
        self._poll_once()
        
        # Start background polling
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        
        # Start TUI
        try:
            with self.tui:
                while self._running and not self._stop_event.is_set():
                    self.tui.update()
                    time.sleep(self.refresh_rate)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the HUD."""
        self._running = False
        self._stop_event.set()
        
        # Stop TUI
        self.tui.stop()
        
        # Flush store
        self.store.flush()
        
        # Wait for poll thread
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)
    
    def snapshot(self) -> dict:
        """Get current snapshot."""
        self._poll_once()
        return {
            'timestamp': time.time(),
            'kpis': self.state.get_kpis(),
            'stats': self.state.get_detailed_stats(),
            'active_traces': [t.to_display_dict() for t in self.state.get_active_traces()],
            'collector_stats': self.collector.get_stats(),
            'store_stats': self.store.get_stats(),
        }
    
    def render_snapshot(self) -> None:
        """Render single snapshot to console."""
        self._poll_once()
        self.tui.render_snapshot(self.state)
    
    def export_json(self, output_path: Path) -> None:
        """Export current state to JSON file."""
        snapshot = self.snapshot()
        output_path.write_text(json.dumps(snapshot, indent=2, default=str))
        print(f"Exported to {output_path}")
    
    def replay(self, since: Optional[float] = None) -> None:
        """Replay events from store."""
        since = since or (time.time() - 3600)  # Default: last hour
        
        print(f"Replaying events since {datetime.fromtimestamp(since)}")
        print("=" * 60)
        
        count = 0
        for event in self.store.read_since(since):
            print(f"\n[{event.source.value}] {event.status.value}")
            print(f"  Intent: {event.intent[:60]}...")
            if event.action:
                print(f"  Action: {event.action[:60]}...")
            if event.lesson:
                print(f"  Lesson: {event.lesson[:60]}...")
            print(f"  Time: {datetime.fromtimestamp(event.timestamp)}")
            count += 1
        
        print(f"\nReplayed {count} events")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Decision Trace HUD - Real-time Spark observability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Keyboard shortcuts (interactive mode):
  q / Ctrl+C    Quit
  r             Force refresh
  p             Pause/unpause updates
  s             Save snapshot
  h             Show help
        """
    )
    
    parser.add_argument(
        "--spark-dir",
        type=Path,
        help="Spark directory (default: ~/.spark)",
    )
    parser.add_argument(
        "--store-dir",
        type=Path,
        help="Trace store directory (default: ~/.spark/trace_hud)",
    )
    parser.add_argument(
        "--refresh-rate",
        type=float,
        default=1.0,
        help="Refresh rate in seconds (default: 1.0)",
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--snapshot",
        action="store_true",
        help="Single snapshot and exit",
    )
    mode_group.add_argument(
        "--replay",
        action="store_true",
        help="Replay events from store",
    )
    mode_group.add_argument(
        "--export",
        type=Path,
        metavar="PATH",
        help="Export to JSON file",
    )
    mode_group.add_argument(
        "--compact",
        action="store_true",
        help="Compact old store data",
    )
    
    # Replay options
    parser.add_argument(
        "--since",
        type=float,
        help="Replay since timestamp (Unix)",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        help="Replay since N hours ago",
    )
    
    args = parser.parse_args()
    
    # Create HUD
    hud = DecisionTraceHUD(
        spark_dir=args.spark_dir,
        store_dir=args.store_dir,
        refresh_rate=args.refresh_rate,
    )
    
    # Execute mode
    if args.snapshot:
        hud.render_snapshot()
    
    elif args.replay:
        since = args.since
        if args.since_hours:
            since = time.time() - (args.since_hours * 3600)
        hud.replay(since=since)
    
    elif args.export:
        hud.export_json(args.export)
    
    elif args.compact:
        stats = hud.store.compact()
        print(f"Compacted: {stats}")
    
    else:
        # Interactive mode
        print("Starting Decision Trace HUD...")
        print("Press 'q' or Ctrl+C to quit\n")
        hud.start()


if __name__ == "__main__":
    main()
