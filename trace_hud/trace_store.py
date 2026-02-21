"""JSONL-backed trace event store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable, Iterator, List, Optional

from .trace_collector import TraceEvent, TraceSource


class TraceStore:
    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = Path(store_dir or (Path.home() / ".spark" / "tracer"))
        self.events_file = self.store_dir / "events.jsonl"
        self._buffer: List[TraceEvent] = []

    def append(self, event: TraceEvent) -> None:
        self._buffer.append(event)

    def append_many(self, events: Iterable[TraceEvent]) -> None:
        for event in events or []:
            self._buffer.append(event)

    def flush(self) -> None:
        if not self._buffer:
            return
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self.events_file.open("a", encoding="utf-8") as f:
            for event in self._buffer:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self._buffer.clear()

    def _read_all(self) -> List[TraceEvent]:
        out: List[TraceEvent] = []
        if not self.events_file.exists():
            return out
        try:
            with self.events_file.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(row, dict):
                        continue
                    evt = TraceEvent.from_dict(row)
                    if evt.trace_id:
                        out.append(evt)
        except Exception:
            return []
        return out

    def read_last(self, limit: int = 100) -> List[TraceEvent]:
        rows = self._read_all()
        lim = max(0, int(limit or 0))
        return rows[-lim:] if lim else []

    def read_since(
        self,
        min_timestamp: float,
        source_filter: Optional[List[TraceSource]] = None,
    ) -> Iterator[TraceEvent]:
        allow = None
        if source_filter:
            allow = {src.value if isinstance(src, TraceSource) else str(src) for src in source_filter}
        for event in self._read_all():
            if float(event.timestamp or 0.0) < float(min_timestamp or 0.0):
                continue
            if allow is not None and event.source.value not in allow:
                continue
            yield event

    def query(self, predicate: Callable[[TraceEvent], bool], limit: int = 100) -> List[TraceEvent]:
        out: List[TraceEvent] = []
        for event in reversed(self._read_all()):
            try:
                if predicate(event):
                    out.append(event)
            except Exception:
                continue
            if len(out) >= max(0, int(limit or 0)):
                break
        out.reverse()
        return out

    def get_stats(self) -> dict:
        total = len(self._read_all())
        return {
            "current_file": str(self.events_file),
            "buffered_events": len(self._buffer),
            "stored_events": total,
        }
