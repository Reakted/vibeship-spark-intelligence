#!/usr/bin/env python3
"""
Moltbook Heartbeat Daemon

A background service that runs the Spark Moltbook agent on a schedule.
Performs periodic engagement to maintain an active presence on Moltbook.

Usage:
    # Run once
    python -m adapters.moltbook.heartbeat --once

    # Run as daemon (checks every 4 hours)
    python -m adapters.moltbook.heartbeat --daemon

    # Run with custom interval
    python -m adapters.moltbook.heartbeat --daemon --interval 6

Windows Task Scheduler:
    schtasks /create /tn "SparkMoltbookHeartbeat" /tr "python C:\\path\\to\\heartbeat.py --once" /sc hourly /mo 4

Linux/macOS cron:
    0 */4 * * * python /path/to/heartbeat.py --once >> ~/.spark/moltbook/heartbeat.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters.moltbook.agent import SparkMoltbookAgent
from adapters.moltbook.client import is_registered, MoltbookError
from lib.diagnostics import log_debug

# ============= Configuration =============
LOG_DIR = Path.home() / ".spark" / "moltbook" / "logs"
PID_FILE = Path.home() / ".spark" / "moltbook" / "heartbeat.pid"
DEFAULT_INTERVAL_HOURS = 4
MIN_INTERVAL_HOURS = 4  # Moltbook recommendation


class HeartbeatDaemon:
    """
    Background daemon for Moltbook heartbeat execution.

    Runs the agent's heartbeat cycle on a schedule, respecting
    Moltbook's recommended 4+ hour interval between check-ins.
    """

    def __init__(self, interval_hours: float = DEFAULT_INTERVAL_HOURS):
        """
        Initialize the heartbeat daemon.

        Args:
            interval_hours: Hours between heartbeats (minimum 4)
        """
        self.interval_hours = max(interval_hours, MIN_INTERVAL_HOURS)
        self.interval_seconds = self.interval_hours * 3600
        self.running = False
        self.agent: Optional[SparkMoltbookAgent] = None

        # Setup logging
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def start(self, daemon_mode: bool = False):
        """
        Start the heartbeat daemon.

        Args:
            daemon_mode: If True, run continuously. If False, run once.
        """
        if not is_registered():
            print("[SPARK] Not registered on Moltbook. Run 'spark moltbook register' first.")
            return

        self.agent = SparkMoltbookAgent()

        if daemon_mode:
            self._run_daemon()
        else:
            self._run_once()

    def _run_once(self):
        """Execute a single heartbeat."""
        print(f"[SPARK] Running Moltbook heartbeat at {datetime.now().isoformat()}")

        try:
            result = self.agent.heartbeat()
            self._log_result(result)
            print(f"[SPARK] Heartbeat complete. Actions: {len(result.get('actions', []))}")

        except MoltbookError as e:
            self._log_error(f"Moltbook API error: {e}")
            print(f"[SPARK] Heartbeat failed: {e}")

        except Exception as e:
            self._log_error(f"Unexpected error: {e}")
            log_debug("moltbook_heartbeat", "heartbeat failed", e)
            print(f"[SPARK] Heartbeat error: {e}")

    def _run_daemon(self):
        """Run continuously as a daemon."""
        print(f"[SPARK] Starting Moltbook heartbeat daemon (interval: {self.interval_hours}h)")

        # Write PID file
        self._write_pid()

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self.running = True

        try:
            while self.running:
                self._run_once()

                # Sleep until next heartbeat
                if self.running:
                    print(f"[SPARK] Next heartbeat in {self.interval_hours} hours")
                    self._sleep_interruptible(self.interval_seconds)

        finally:
            self._cleanup()

    def _sleep_interruptible(self, seconds: float):
        """Sleep that can be interrupted by shutdown signal."""
        end_time = time.time() + seconds

        while self.running and time.time() < end_time:
            time.sleep(min(60, end_time - time.time()))

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[SPARK] Received signal {signum}, shutting down...")
        self.running = False

    def _write_pid(self):
        """Write PID file for daemon management."""
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

    def _cleanup(self):
        """Clean up daemon resources."""
        if PID_FILE.exists():
            PID_FILE.unlink()
        print("[SPARK] Heartbeat daemon stopped")

    def _log_result(self, result: dict):
        """Log heartbeat result to file."""
        log_file = LOG_DIR / f"heartbeat_{datetime.now().strftime('%Y%m%d')}.jsonl"

        with open(log_file, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "result": result,
            }) + "\n")

    def _log_error(self, error: str):
        """Log error to file."""
        log_file = LOG_DIR / "errors.log"

        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {error}\n")

    @staticmethod
    def is_running() -> bool:
        """Check if a daemon instance is already running."""
        if not PID_FILE.exists():
            return False

        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError):
            # Process doesn't exist or invalid PID
            if PID_FILE.exists():
                PID_FILE.unlink()
            return False

    @staticmethod
    def stop():
        """Stop a running daemon instance."""
        if not PID_FILE.exists():
            print("[SPARK] No daemon running")
            return

        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"[SPARK] Sent stop signal to daemon (PID: {pid})")

            # Wait for process to stop
            for _ in range(10):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    print("[SPARK] Daemon stopped")
                    return

            print("[SPARK] Daemon didn't stop gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)

        except ProcessLookupError:
            print("[SPARK] Daemon was not running")
            if PID_FILE.exists():
                PID_FILE.unlink()

        except Exception as e:
            print(f"[SPARK] Error stopping daemon: {e}")


# ============= CLI Interface =============

def main():
    """CLI entry point for the heartbeat daemon."""
    parser = argparse.ArgumentParser(
        description="Spark Moltbook Heartbeat Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --once          Run a single heartbeat
  %(prog)s --daemon        Start as background daemon
  %(prog)s --stop          Stop running daemon
  %(prog)s --status        Check daemon status
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="Run a single heartbeat")
    group.add_argument("--daemon", action="store_true", help="Run as background daemon")
    group.add_argument("--stop", action="store_true", help="Stop running daemon")
    group.add_argument("--status", action="store_true", help="Check daemon status")

    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_HOURS,
        help=f"Hours between heartbeats (default: {DEFAULT_INTERVAL_HOURS}, min: {MIN_INTERVAL_HOURS})"
    )

    args = parser.parse_args()

    if args.status:
        if HeartbeatDaemon.is_running():
            pid = PID_FILE.read_text().strip()
            print(f"[SPARK] Moltbook heartbeat daemon is running (PID: {pid})")
        else:
            print("[SPARK] Moltbook heartbeat daemon is not running")
        return

    if args.stop:
        HeartbeatDaemon.stop()
        return

    if HeartbeatDaemon.is_running():
        print("[SPARK] Heartbeat daemon is already running. Use --stop to stop it first.")
        return

    daemon = HeartbeatDaemon(interval_hours=args.interval)
    daemon.start(daemon_mode=args.daemon)


if __name__ == "__main__":
    main()
