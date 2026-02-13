#!/usr/bin/env python3
"""trace_store.py - Append-only JSONL log for trace events with replay capability.

Provides:
- Persistent append-only storage
- Replay from any point in time
- Compaction for old data
- Query/filter capabilities
"""

from __future__ import annotations

import json
import gzip
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Callable
from dataclasses import asdict
import threading

from trace_hud.trace_collector import TraceEvent, TraceSource, TraceStatus


class TraceStore:
    """Append-only store for trace events with replay support."""
    
    def __init__(
        self,
        store_dir: Optional[Path] = None,
        max_file_size_bytes: int = 10 * 1024 * 1024,  # 10MB
        max_age_days: int = 30,
    ):
        self.store_dir = store_dir or Path.home() / ".spark" / "trace_hud"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_file = self.store_dir / "trace_store.jsonl"
        self.archive_dir = self.store_dir / "archive"
        self.archive_dir.mkdir(exist_ok=True)
        
        self.max_file_size = max_file_size_bytes
        self.max_age_days = max_age_days
        
        self._lock = threading.RLock()
        self._write_buffer: List[Dict] = []
        self._buffer_size = 10
        self._last_flush = time.time()
        self._flush_interval = 5.0  # seconds
    
    # -------------------------------------------------------------------------
    # Writing
    # -------------------------------------------------------------------------
    
    def append(self, event: TraceEvent) -> None:
        """Append single event to store."""
        with self._lock:
            self._write_buffer.append(event.to_dict())
            
            if len(self._write_buffer) >= self._buffer_size:
                self._flush()
            elif time.time() - self._last_flush > self._flush_interval:
                self._flush()
    
    def append_many(self, events: List[TraceEvent]) -> None:
        """Append multiple events."""
        with self._lock:
            for event in events:
                self._write_buffer.append(event.to_dict())
            
            if len(self._write_buffer) >= self._buffer_size:
                self._flush()
    
    def _flush(self) -> None:
        """Flush buffer to disk."""
        if not self._write_buffer:
            return
        
        # Check if we need to rotate
        if self.current_file.exists():
            size = self.current_file.stat().st_size
            if size > self.max_file_size:
                self._rotate_file()
        
        # Write events
        # Note: some upstream sources can contain invalid Unicode surrogate codepoints.
        # Use errors='replace' to avoid crashing the tracer/dashboard on write.
        with open(self.current_file, 'a', encoding='utf-8', errors='replace') as f:
            for event_dict in self._write_buffer:
                f.write(json.dumps(event_dict, ensure_ascii=False) + '\n')
        
        self._write_buffer.clear()
        self._last_flush = time.time()
    
    def _rotate_file(self) -> None:
        """Rotate current file to archive."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f"trace_store_{timestamp}.jsonl.gz"
        archive_path = self.archive_dir / archive_name
        
        # Compress and move
        if self.current_file.exists():
            with open(self.current_file, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            self.current_file.unlink()
    
    def flush(self) -> None:
        """Public flush method."""
        with self._lock:
            self._flush()
    
    # -------------------------------------------------------------------------
    # Reading / Replay
    # -------------------------------------------------------------------------
    
    def read_since(
        self,
        since: float,
        source_filter: Optional[List[TraceSource]] = None,
        status_filter: Optional[List[TraceStatus]] = None,
    ) -> Iterator[TraceEvent]:
        """Read events since timestamp with optional filtering."""
        self.flush()  # Ensure all data is on disk
        
        sources = {s.value for s in source_filter} if source_filter else None
        statuses = {s.value for s in status_filter} if status_filter else None
        
        for event_dict in self._iter_all_events():
            # Time filter
            if event_dict.get('timestamp', 0) < since:
                continue
            
            # Source filter
            if sources and event_dict.get('source') not in sources:
                continue
            
            # Status filter
            if statuses and event_dict.get('status') not in statuses:
                continue
            
            try:
                yield TraceEvent.from_dict(event_dict)
            except Exception:
                continue
    
    def read_range(
        self,
        start: float,
        end: float,
    ) -> Iterator[TraceEvent]:
        """Read events in time range."""
        self.flush()
        
        for event_dict in self._iter_all_events():
            ts = event_dict.get('timestamp', 0)
            if start <= ts <= end:
                try:
                    yield TraceEvent.from_dict(event_dict)
                except Exception:
                    continue
    
    def read_last(self, count: int = 100) -> List[TraceEvent]:
        """Read last N events."""
        self.flush()
        
        events = []
        for event_dict in self._iter_all_events(reverse=True):
            try:
                events.append(TraceEvent.from_dict(event_dict))
                if len(events) >= count:
                    break
            except Exception:
                continue
        
        return list(reversed(events))
    
    def _iter_all_events(
        self,
        reverse: bool = False,
    ) -> Iterator[Dict]:
        """Iterate all events from current file and archives."""
        files = []
        
        # Current file
        if self.current_file.exists():
            files.append(self.current_file)
        
        # Archive files
        if self.archive_dir.exists():
            archives = sorted(self.archive_dir.glob("trace_store_*.jsonl.gz"))
            files.extend(archives)
        
        if reverse:
            files = list(reversed(files))
        
        for file_path in files:
            if file_path.suffix == '.gz':
                yield from self._iter_gz_file(file_path, reverse)
            else:
                yield from self._iter_jsonl_file(file_path, reverse)
    
    def _iter_jsonl_file(
        self,
        path: Path,
        reverse: bool = False,
    ) -> Iterator[Dict]:
        """Iterate events from a JSONL file."""
        if not path.exists():
            return
        
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            if reverse:
                lines = reversed(lines)
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
        except Exception:
            return
    
    def _iter_gz_file(
        self,
        path: Path,
        reverse: bool = False,
    ) -> Iterator[Dict]:
        """Iterate events from a gzipped JSONL file."""
        if not path.exists():
            return
        
        try:
            with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            if reverse:
                lines = reversed(lines)
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
        except Exception:
            return
    
    # -------------------------------------------------------------------------
    # Query / Analysis
    # -------------------------------------------------------------------------
    
    def query(
        self,
        predicate: Callable[[TraceEvent], bool],
        limit: int = 100,
    ) -> List[TraceEvent]:
        """Query events with custom predicate."""
        results = []
        for event in self.read_last(count=1000):
            if predicate(event):
                results.append(event)
                if len(results) >= limit:
                    break
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        self.flush()
        
        total_events = 0
        total_bytes = 0
        
        # Current file
        if self.current_file.exists():
            stat = self.current_file.stat()
            total_bytes += stat.st_size
            with open(self.current_file, 'r', encoding='utf-8', errors='replace') as f:
                total_events += sum(1 for _ in f)
        
        # Archives
        archive_count = 0
        if self.archive_dir.exists():
            for archive in self.archive_dir.glob("*.gz"):
                archive_count += 1
                total_bytes += archive.stat().st_size
        
        return {
            'current_file': str(self.current_file),
            'current_file_size': self.current_file.stat().st_size if self.current_file.exists() else 0,
            'archive_count': archive_count,
            'total_bytes': total_bytes,
            'buffered_events': len(self._write_buffer),
        }
    
    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------
    
    def compact(self, keep_days: Optional[int] = None) -> Dict[str, int]:
        """Remove old data, return stats."""
        keep_days = keep_days or self.max_age_days
        cutoff = time.time() - (keep_days * 24 * 60 * 60)
        
        removed = 0
        bytes_freed = 0
        
        # Remove old archive files
        if self.archive_dir.exists():
            for archive in list(self.archive_dir.glob("*.gz")):
                # Parse date from filename: trace_store_YYYYMMDD_HHMMSS.jsonl.gz
                try:
                    date_str = archive.stem.split('_')[2]
                    file_time = datetime.strptime(date_str, '%Y%m%d').timestamp()
                    if file_time < cutoff:
                        size = archive.stat().st_size
                        archive.unlink()
                        removed += 1
                        bytes_freed += size
                except Exception:
                    continue
        
        return {
            'files_removed': removed,
            'bytes_freed': bytes_freed,
        }
    
    def clear_all(self) -> None:
        """Clear all stored data (dangerous!)."""
        with self._lock:
            self._flush()
            if self.current_file.exists():
                self.current_file.unlink()
            for archive in self.archive_dir.glob("*.gz"):
                archive.unlink()


def demo_store():
    """Demo the store."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp:
        store = TraceStore(store_dir=Path(tmp))
        
        # Create some test events
        events = [
            TraceEvent(
                trace_id=f"test_{i}",
                event_id=f"evt_{i}",
                timestamp=time.time() - i,
                source=TraceSource.USER_PROMPT,
                intent=f"Test intent {i}",
                status=TraceStatus.SUCCESS if i % 2 == 0 else TraceStatus.FAIL,
            )
            for i in range(20)
        ]
        
        # Store them
        store.append_many(events)
        store.flush()
        
        # Read back
        print(f"Store stats: {store.get_stats()}")
        
        print("\nLast 5 events:")
        for evt in store.read_last(5):
            print(f"  [{evt.source.value}] {evt.intent[:40]} - {evt.status.value}")
        
        # Query
        print("\nFailed events:")
        failed = store.query(lambda e: e.status == TraceStatus.FAIL, limit=5)
        for evt in failed:
            print(f"  {evt.intent[:40]}")


if __name__ == "__main__":
    demo_store()
