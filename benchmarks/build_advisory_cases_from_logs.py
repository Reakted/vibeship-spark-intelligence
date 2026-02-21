#!/usr/bin/env python3
"""Utilities for building advisory benchmark cases from advisory engine logs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List


def _as_float_seconds(raw: object, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def build_cases(
    log_path: str | Path,
    *,
    lookback_hours: float = 24.0,
    limit: int = 100,
) -> List[Dict[str, object]]:
    """Build advisory benchmark cases from a JSONL advisory-engine log file.

    The helper is intentionally lightweight and only depends on fields that are
    currently available in local test fixtures.
    """
    path = Path(log_path)
    if not path.exists():
        return []

    now = time.time()
    cutoff = now - max(0.0, float(lookback_hours) * 3600.0)
    max_rows = max(0, int(limit))
    cases: List[Dict[str, object]] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = (line or "").strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue

        ts = _as_float_seconds(row.get("ts"), 0.0)
        if ts < cutoff:
            continue

        event = str(row.get("event", "")).strip().lower()
        tool = str(row.get("tool", "unknown")).strip()
        should_emit = event != "no_emit"

        cases.append(
            {
                "ts": ts,
                "tool": tool,
                "event": event,
                "should_emit": bool(should_emit),
                "route": str(row.get("route", "unknown")),
                "error_code": row.get("error_code"),
                "raw": row,
            }
        )

    if max_rows > 0:
        cases = cases[:max_rows]
    return cases


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
