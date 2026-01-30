"""Outcome log helpers for prediction validation."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

OUTCOMES_FILE = Path.home() / ".spark" / "outcomes.jsonl"


def _hash_id(*parts: str) -> str:
    raw = "|".join(p or "" for p in parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def make_outcome_id(*parts: str) -> str:
    return _hash_id(*parts)


def append_outcomes(rows: Iterable[Dict[str, Any]]) -> int:
    """Append outcome rows to the shared outcomes log. Returns count written."""
    if not rows:
        return 0
    OUTCOMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUTCOMES_FILE.open("a", encoding="utf-8") as f:
        for row in rows:
            if not row:
                continue
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def append_outcome(row: Dict[str, Any]) -> int:
    return append_outcomes([row] if row else [])


def build_explicit_outcome(
    result: str,
    text: str = "",
    *,
    tool: Optional[str] = None,
    created_at: Optional[float] = None,
) -> Tuple[Dict[str, Any], str]:
    """Build an explicit outcome row from a user check-in."""
    res = (result or "").strip().lower()
    if res in {"yes", "y", "success", "ok", "good", "worked"}:
        polarity = "pos"
    elif res in {"partial", "mixed", "some", "meh", "unclear"}:
        polarity = "neutral"
    else:
        polarity = "neg"
    now = float(created_at or time.time())
    clean_text = (text or "").strip()
    if not clean_text:
        clean_text = f"explicit check-in: {res or 'unknown'}"
    row = {
        "outcome_id": make_outcome_id(str(now), res, clean_text[:120]),
        "event_type": "explicit_checkin",
        "tool": tool,
        "text": clean_text,
        "polarity": polarity,
        "result": res or "unknown",
        "created_at": now,
    }
    return row, polarity
