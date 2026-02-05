"""
Chip Insight Merger - Bridge chip insights into the cognitive learning pipeline.

Chips capture domain-specific insights that are stored separately.
This module merges high-value chip insights into the main cognitive system
so they can be validated, promoted, and injected into context.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory
from lib.exposure_tracker import record_exposures
from lib.queue import _tail_lines


CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
MERGE_STATE_FILE = Path.home() / ".spark" / "chip_merge_state.json"


# Map chip domains to cognitive categories
CHIP_TO_CATEGORY = {
    "market-intel": CognitiveCategory.CONTEXT,
    "game_dev": CognitiveCategory.REASONING,
    "marketing": CognitiveCategory.CONTEXT,
    "vibecoding": CognitiveCategory.WISDOM,
    "moltbook": CognitiveCategory.REASONING,
    "biz-ops": CognitiveCategory.CONTEXT,
    "bench-core": CognitiveCategory.SELF_AWARENESS,
    "spark-core": CognitiveCategory.META_LEARNING,
}


def _load_merge_state() -> Dict[str, Any]:
    """Load the merge state tracking which insights have been merged."""
    if not MERGE_STATE_FILE.exists():
        return {"merged_hashes": [], "last_merge": None}
    try:
        return json.loads(MERGE_STATE_FILE.read_text())
    except Exception:
        return {"merged_hashes": [], "last_merge": None}


def _save_merge_state(state: Dict[str, Any]):
    """Save the merge state."""
    MERGE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MERGE_STATE_FILE.write_text(json.dumps(state, indent=2))


def _hash_insight(chip_id: str, content: str, timestamp: str) -> str:
    """Create a hash for deduplication."""
    import hashlib
    raw = f"{chip_id}|{content[:100]}|{timestamp}".encode()
    return hashlib.sha1(raw).hexdigest()[:12]


def _tail_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    """Read the last N JSONL rows without loading the whole file."""
    if limit <= 0 or not path.exists():
        return []

    out: List[Dict[str, Any]] = []
    for raw in _tail_lines(path, limit):
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def _count_jsonl_lines(path: Path) -> int:
    """Count non-empty JSONL rows with streaming IO."""
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def load_chip_insights(chip_id: str = None, limit: int = 100) -> List[Dict]:
    """Load chip insights from disk."""
    insights = []

    if chip_id:
        files = [CHIP_INSIGHTS_DIR / f"{chip_id}.jsonl"]
    else:
        files = list(CHIP_INSIGHTS_DIR.glob("*.jsonl")) if CHIP_INSIGHTS_DIR.exists() else []

    for file_path in files:
        if not file_path.exists():
            continue
        try:
            # Tail-read avoids loading very large chip files into memory each cycle.
            insights.extend(_tail_jsonl(file_path, limit=limit))
        except Exception:
            continue

    # Sort by timestamp descending
    insights.sort(key=lambda i: i.get("timestamp", ""), reverse=True)
    return insights[:limit]


def merge_chip_insights(
    min_confidence: float = 0.7,
    limit: int = 50,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Merge high-confidence chip insights into the cognitive learning system.

    This is the key function that bridges domain-specific chip observations
    into the main learning pipeline where they can be validated and promoted.

    Args:
        min_confidence: Minimum confidence to consider for merging
        limit: Max insights to process per run
        dry_run: If True, don't actually merge, just report what would happen

    Returns:
        Stats about the merge operation
    """
    state = _load_merge_state()
    merged_hashes = set(state.get("merged_hashes", []))

    stats = {
        "processed": 0,
        "merged": 0,
        "skipped_low_confidence": 0,
        "skipped_duplicate": 0,
        "by_chip": {},
    }

    cog = get_cognitive_learner()
    chip_insights = load_chip_insights(limit=limit)
    exposures_to_record = []

    for chip_insight in chip_insights:
        stats["processed"] += 1

        chip_id = chip_insight.get("chip_id", "unknown")
        content = chip_insight.get("content", "")
        confidence = chip_insight.get("confidence", 0.5)
        timestamp = chip_insight.get("timestamp", "")
        captured_data = chip_insight.get("captured_data", {})

        # Skip low confidence
        if confidence < min_confidence:
            stats["skipped_low_confidence"] += 1
            continue

        # Skip already merged
        insight_hash = _hash_insight(chip_id, content, timestamp)
        if insight_hash in merged_hashes:
            stats["skipped_duplicate"] += 1
            continue

        # Determine category
        category = CHIP_TO_CATEGORY.get(chip_id, CognitiveCategory.CONTEXT)

        # Build context from captured data
        context_parts = []
        if captured_data.get("file_path"):
            context_parts.append(f"File: {captured_data['file_path']}")
        if captured_data.get("tool"):
            context_parts.append(f"Tool: {captured_data['tool']}")
        if captured_data.get("change_summary"):
            context_parts.append(captured_data["change_summary"])
        context = " | ".join(context_parts) if context_parts else f"From {chip_id} chip"

        if not dry_run:
            # Add to cognitive system (but don't double-record exposure)
            cog.add_insight(
                category=category,
                insight=content,
                context=context,
                confidence=confidence,
                record_exposure=False  # We'll batch record below
            )

            # Track for exposure recording
            key = cog._generate_key(category, content[:40].replace(" ", "_").lower())
            exposures_to_record.append({
                "insight_key": key,
                "category": category.value,
                "text": content,
            })

            merged_hashes.add(insight_hash)

        stats["merged"] += 1
        stats["by_chip"][chip_id] = stats["by_chip"].get(chip_id, 0) + 1

    # Batch record exposures
    if exposures_to_record and not dry_run:
        try:
            from lib.exposure_tracker import infer_latest_trace_id, infer_latest_session_id
            session_id = infer_latest_session_id()
            trace_id = infer_latest_trace_id(session_id)
        except Exception:
            session_id = None
            trace_id = None
        record_exposures(source="chip_merge", items=exposures_to_record, session_id=session_id, trace_id=trace_id)

    # Save state
    if not dry_run:
        state["merged_hashes"] = list(merged_hashes)[-1000:]  # Keep last 1000
        state["last_merge"] = datetime.now().isoformat()
        state["last_stats"] = stats
        _save_merge_state(state)

    return stats


def get_merge_stats() -> Dict[str, Any]:
    """Get statistics about chip merging."""
    state = _load_merge_state()

    # Count insights per chip
    chip_counts = {}
    if CHIP_INSIGHTS_DIR.exists():
        for f in CHIP_INSIGHTS_DIR.glob("*.jsonl"):
            try:
                chip_counts[f.stem] = _count_jsonl_lines(f)
            except Exception:
                continue

    return {
        "total_merged": len(state.get("merged_hashes", [])),
        "last_merge": state.get("last_merge"),
        "last_stats": state.get("last_stats"),
        "chip_insight_counts": chip_counts,
    }
