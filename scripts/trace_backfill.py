#!/usr/bin/env python3
"""Backfill missing trace_id bindings for evidence/outcomes (best-effort).

Usage:
  python scripts/trace_backfill.py --dry-run
  python scripts/trace_backfill.py --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.exposure_tracker import EXPOSURES_FILE  # noqa: E402
from lib.outcome_log import OUTCOMES_FILE  # noqa: E402
from lib.eidos import get_store, get_evidence_store  # noqa: E402


def _load_exposure_trace_map(limit: int = 2000) -> Dict[str, str]:
    """Return latest trace_id per session_id from exposures.jsonl."""
    if not EXPOSURES_FILE.exists():
        return {}
    mapping: Dict[str, str] = {}
    try:
        lines = EXPOSURES_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    for line in reversed(lines[-limit:]):
        try:
            row = json.loads(line)
        except Exception:
            continue
        sid = row.get("session_id")
        tid = row.get("trace_id")
        if not sid or not tid:
            continue
        if sid not in mapping:
            mapping[sid] = str(tid)
    return mapping


def _backfill_outcomes(*, apply: bool) -> Tuple[int, int]:
    if not OUTCOMES_FILE.exists():
        return 0, 0
    mapping = _load_exposure_trace_map()
    updated = 0
    total_missing = 0
    rows: List[str] = []
    try:
        with OUTCOMES_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    rows.append(raw)
                    continue
                if not row.get("trace_id"):
                    total_missing += 1
                    sid = row.get("session_id")
                    if sid and sid in mapping:
                        row["trace_id"] = mapping[sid]
                        updated += 1
                rows.append(json.dumps(row, ensure_ascii=False))
    except Exception:
        return 0, 0

    if apply and rows:
        tmp_path = OUTCOMES_FILE.with_suffix(".jsonl.tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
        if OUTCOMES_FILE.exists():
            OUTCOMES_FILE.unlink()
        tmp_path.rename(OUTCOMES_FILE)

    return total_missing, updated


def _fetch_trace_ids(store, step_ids: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not step_ids:
        return mapping
    with sqlite3.connect(store.db_path) as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT step_id, trace_id FROM steps WHERE step_id IN ({})".format(
            ",".join("?" for _ in step_ids)
        )
        rows = conn.execute(q, step_ids).fetchall()
        for row in rows:
            sid = row["step_id"]
            tid = row["trace_id"]
            if sid and tid:
                mapping[str(sid)] = str(tid)
    return mapping


def _backfill_evidence(*, apply: bool) -> Tuple[int, int]:
    ev_store = get_evidence_store()
    if not Path(ev_store.db_path).exists():
        return 0, 0

    total_missing = 0
    updated = 0
    step_ids: List[str] = []
    try:
        with sqlite3.connect(ev_store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cols = conn.execute("PRAGMA table_info(evidence)").fetchall()
            has_trace = any(c[1] == "trace_id" for c in cols)
            if not has_trace:
                return 0, 0
            rows = conn.execute(
                "SELECT evidence_id, step_id FROM evidence WHERE trace_id IS NULL OR trace_id = ''"
            ).fetchall()
            for row in rows:
                total_missing += 1
                sid = row["step_id"]
                if sid:
                    step_ids.append(str(sid))
    except Exception:
        return 0, 0

    store = get_store()
    mapping = _fetch_trace_ids(store, list(dict.fromkeys(step_ids)))
    if not mapping:
        return total_missing, 0

    if apply:
        with sqlite3.connect(ev_store.db_path) as conn:
            for sid, tid in mapping.items():
                res = conn.execute(
                    "UPDATE evidence SET trace_id = ? WHERE (trace_id IS NULL OR trace_id = '') AND step_id = ?",
                    (tid, sid),
                )
                updated += int(res.rowcount or 0)
            conn.commit()
    else:
        updated = len(mapping)

    return total_missing, updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes")
    ap.add_argument("--dry-run", action="store_true", help="compute changes only")
    args = ap.parse_args()

    apply = args.apply and not args.dry_run
    mode = "APPLY" if apply else "DRY-RUN"
    start = time.time()

    out_missing, out_updated = _backfill_outcomes(apply=apply)
    ev_missing, ev_updated = _backfill_evidence(apply=apply)

    print(f"[{mode}] outcomes missing trace_id: {out_missing}")
    print(f"[{mode}] outcomes updated: {out_updated}")
    print(f"[{mode}] evidence missing trace_id: {ev_missing}")
    print(f"[{mode}] evidence updated: {ev_updated}")
    print(f"[{mode}] elapsed: {time.time() - start:.2f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
