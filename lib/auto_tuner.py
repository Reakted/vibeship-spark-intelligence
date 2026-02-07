"""
Spark Auto-Tuner: Data-Driven Source Boost Optimization

Reads advisor effectiveness data and adjusts source boosts in tuneables.json
so that high-performing sources get amplified and low-performing ones get demoted.

The auto-tuner runs periodically (default: every 24 hours) and makes bounded
adjustments (max 15% per run) to prevent wild swings.

Usage:
    from lib.auto_tuner import AutoTuner
    tuner = AutoTuner()
    report = tuner.run()
    print(report.summary)

CLI:
    python -m lib.auto_tuner [--dry-run] [--force]
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SPARK_DIR = Path.home() / ".spark"
TUNEABLES_PATH = SPARK_DIR / "tuneables.json"
EFFECTIVENESS_PATH = SPARK_DIR / "advisor" / "effectiveness.json"


@dataclass
class BoostChange:
    """A single source boost adjustment."""
    source: str
    old_boost: float
    new_boost: float
    effectiveness: float
    sample_count: int
    reason: str

    @property
    def delta(self) -> float:
        return self.new_boost - self.old_boost


@dataclass
class TuningReport:
    """Result of an auto-tuner run."""
    timestamp: str
    changes: List[BoostChange]
    skipped: List[str]
    data_basis: str
    dry_run: bool = False

    @property
    def summary(self) -> str:
        lines = [f"Auto-Tuner Report ({self.timestamp})"]
        lines.append(f"Data: {self.data_basis}")
        if self.dry_run:
            lines.append("Mode: DRY RUN (no changes applied)")
        if not self.changes:
            lines.append("No changes needed — all boosts are within tolerance.")
        for c in self.changes:
            direction = "+" if c.delta > 0 else ""
            lines.append(
                f"  {c.source}: {c.old_boost:.2f} -> {c.new_boost:.2f} "
                f"({direction}{c.delta:.2f}) | {c.effectiveness:.1%} effective "
                f"({c.sample_count} samples) | {c.reason}"
            )
        if self.skipped:
            lines.append(f"Skipped (insufficient data): {', '.join(self.skipped)}")
        return "\n".join(lines)


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning empty dict on error."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _write_json_atomic(path: Path, data: dict):
    """Write JSON atomically via temp file + replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=4))
    tmp.replace(path)


class AutoTuner:
    """Data-driven source boost optimizer for the Spark advisor."""

    # Minimum samples before a source's boost can be adjusted
    MIN_SAMPLES = 20

    # How far from the "ideal" boost a source must be before we adjust
    TOLERANCE = 0.05

    # Boost floor and ceiling
    BOOST_MIN = 0.2
    BOOST_MAX = 2.0

    def __init__(self, tuneables_path: Path = TUNEABLES_PATH):
        self.tuneables_path = tuneables_path
        self._tuneables = _read_json(tuneables_path)
        self._config = self._tuneables.get("auto_tuner", {})

    @property
    def enabled(self) -> bool:
        return self._config.get("enabled", False)

    @property
    def max_change(self) -> float:
        return self._config.get("max_change_per_run", 0.15)

    @property
    def run_interval(self) -> int:
        return self._config.get("run_interval_s", 86400)

    def should_run(self) -> bool:
        """Check if enough time has passed since last run."""
        if not self.enabled:
            return False
        last_run = self._config.get("last_run")
        if not last_run:
            return True
        try:
            last_ts = datetime.fromisoformat(last_run).timestamp()
            return (time.time() - last_ts) >= self.run_interval
        except (ValueError, TypeError):
            return True

    def get_effectiveness_data(self) -> Dict[str, Dict[str, int]]:
        """Read per-source effectiveness from the advisor."""
        data = _read_json(EFFECTIVENESS_PATH)
        return data.get("by_source", {})

    def compute_ideal_boost(self, effectiveness: float, global_avg: float) -> float:
        """Compute the ideal boost for a source based on its effectiveness.

        Sources above the global average get boosted, below get demoted.
        The boost scales linearly between BOOST_MIN and BOOST_MAX,
        centered at 1.0 for global-average effectiveness.
        """
        if global_avg <= 0:
            return 1.0

        # Ratio of source effectiveness to global average
        ratio = effectiveness / global_avg

        # Map ratio to boost: ratio=0 -> 0.3, ratio=1 -> 1.0, ratio=2 -> 1.7
        ideal = 0.3 + ratio * 0.7

        return max(self.BOOST_MIN, min(self.BOOST_MAX, round(ideal, 3)))

    def run(self, dry_run: bool = False, force: bool = False) -> TuningReport:
        """Execute an auto-tuning cycle.

        Args:
            dry_run: If True, compute changes but don't apply them.
            force: If True, ignore the run interval check.
        """
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if not force and not self.should_run():
            return TuningReport(
                timestamp=now, changes=[], skipped=[],
                data_basis="Skipped: interval not reached", dry_run=dry_run
            )

        # Read effectiveness data
        by_source = self.get_effectiveness_data()
        current_boosts = self._config.get("source_boosts", {})

        # Compute global average effectiveness (weighted by sample count)
        total_helpful = sum(s.get("helpful", 0) for s in by_source.values())
        total_samples = sum(s.get("total", 0) for s in by_source.values())
        global_avg = total_helpful / max(total_samples, 1)

        changes: List[BoostChange] = []
        skipped: List[str] = []
        new_effectiveness: Dict[str, float] = {}

        # All known sources (union of effectiveness data and current boosts)
        all_sources = set(by_source.keys()) | set(current_boosts.keys())

        for source in sorted(all_sources):
            stats = by_source.get(source, {})
            total = stats.get("total", 0)
            helpful = stats.get("helpful", 0)

            # Skip sources with insufficient data
            if total < self.MIN_SAMPLES:
                skipped.append(f"{source} ({total} samples)")
                continue

            effectiveness = helpful / total
            new_effectiveness[source] = effectiveness

            ideal = self.compute_ideal_boost(effectiveness, global_avg)
            current = current_boosts.get(source, 1.0)

            # Check if change is needed (beyond tolerance)
            delta = ideal - current
            if abs(delta) < self.TOLERANCE:
                continue

            # Cap the change per run
            capped_delta = max(-self.max_change, min(self.max_change, delta))
            new_boost = round(current + capped_delta, 3)
            new_boost = max(self.BOOST_MIN, min(self.BOOST_MAX, new_boost))

            # Determine reason
            if effectiveness > global_avg:
                reason = f"Above avg ({global_avg:.1%}), boosting"
            elif effectiveness < global_avg * 0.5:
                reason = f"Well below avg ({global_avg:.1%}), demoting"
            else:
                reason = f"Below avg ({global_avg:.1%}), slight demotion"

            changes.append(BoostChange(
                source=source,
                old_boost=current,
                new_boost=new_boost,
                effectiveness=effectiveness,
                sample_count=total,
                reason=reason,
            ))

        data_basis = f"{total_samples:,} advisor outcomes across {len(by_source)} sources"

        # Apply changes if not dry run
        if not dry_run and changes:
            self._apply_changes(changes, new_effectiveness, now, data_basis)

        return TuningReport(
            timestamp=now,
            changes=changes,
            skipped=skipped,
            data_basis=data_basis,
            dry_run=dry_run,
        )

    def _apply_changes(
        self,
        changes: List[BoostChange],
        new_effectiveness: Dict[str, float],
        timestamp: str,
        data_basis: str,
    ):
        """Write boost changes to tuneables.json atomically."""
        tuneables = _read_json(self.tuneables_path)
        auto_tuner = tuneables.setdefault("auto_tuner", {})

        # Update boosts
        boosts = auto_tuner.setdefault("source_boosts", {})
        for c in changes:
            boosts[c.source] = c.new_boost

        # Update effectiveness snapshot
        auto_tuner["source_effectiveness"] = {
            k: round(v, 4) for k, v in new_effectiveness.items()
        }

        # Update metadata
        auto_tuner["last_run"] = timestamp

        # Append to tuning log (keep last 50 entries)
        log = auto_tuner.setdefault("tuning_log", [])
        log.append({
            "timestamp": timestamp,
            "action": "auto_tune",
            "changes": {
                c.source: f"{c.old_boost} -> {c.new_boost} ({c.effectiveness:.1%} effective, {c.sample_count} samples)"
                for c in changes
            },
            "data_basis": data_basis,
        })
        if len(log) > 50:
            auto_tuner["tuning_log"] = log[-50:]

        tuneables["updated_at"] = timestamp
        _write_json_atomic(self.tuneables_path, tuneables)

    def get_status(self) -> Dict[str, Any]:
        """Get current auto-tuner status for dashboards."""
        by_source = self.get_effectiveness_data()
        current_boosts = self._config.get("source_boosts", {})

        status = {
            "enabled": self.enabled,
            "last_run": self._config.get("last_run"),
            "run_interval_s": self.run_interval,
            "max_change_per_run": self.max_change,
            "sources": {},
        }

        for source in sorted(set(by_source.keys()) | set(current_boosts.keys())):
            stats = by_source.get(source, {})
            total = stats.get("total", 0)
            helpful = stats.get("helpful", 0)
            status["sources"][source] = {
                "boost": current_boosts.get(source, 1.0),
                "effectiveness": round(helpful / max(total, 1), 4),
                "samples": total,
                "sufficient_data": total >= self.MIN_SAMPLES,
            }

        return status


# CLI entry point
if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    tuner = AutoTuner()

    if "--status" in sys.argv:
        status = tuner.get_status()
        print(json.dumps(status, indent=2))
        sys.exit(0)

    report = tuner.run(dry_run=dry_run, force=force)
    print(report.summary)

    if not dry_run and report.changes:
        print(f"\nApplied {len(report.changes)} changes to {TUNEABLES_PATH}")
    elif dry_run and report.changes:
        print(f"\nDry run: {len(report.changes)} changes would be applied")
