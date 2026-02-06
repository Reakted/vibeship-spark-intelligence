"""
Chip Router - Match events to chip triggers.

This was the third missing piece: when an event comes in,
which chips should process it?
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

from .loader import Chip, ChipObserver

log = logging.getLogger("spark.chips")


@dataclass
class TriggerMatch:
    """A matched trigger with context."""
    chip: Chip
    observer: Optional[ChipObserver]
    trigger: str
    confidence: float
    content_snippet: str  # What content matched


class ChipRouter:
    """
    Routes events to appropriate chips based on trigger matching.

    When we see an Edit to "lobster-royale/src/main.js" containing
    "health", "damage", "physics", this routes to the game_dev chip.
    """

    def route_event(self, event: Dict[str, Any], chips: List[Chip]) -> List[TriggerMatch]:
        """
        Route an event to matching chips.

        Returns all matches sorted by confidence.
        """
        matches = []

        # Extract searchable content from event
        content = self._extract_content(event)
        if not content:
            return matches

        content_lower = content.lower()
        raw_event_type = event.get('event_type') or event.get('hook_event') or event.get('type') or event.get('kind')
        raw_tool_name = event.get('tool_name') or event.get('tool')
        self._current_event_type = self._normalize_event_type(raw_event_type)
        self._current_tool_name = str(raw_tool_name or "").strip().lower()

        for chip in chips:
            chip_matches = self._match_chip(chip, content_lower, content)
            matches.extend(chip_matches)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def _normalize_event_type(self, event_type: Any) -> str:
        """Normalize event names across hook naming variants."""
        normalized = str(event_type or "").strip()
        if not normalized:
            return ""
        lowered = normalized.lower()
        aliases = {
            "posttooluse": "post_tool",
            "posttoolusefailure": "post_tool_failure",
            "userpromptsubmit": "user_prompt",
            "pretooluse": "pre_tool",
            "post_tool_use": "post_tool",
            "post_tool_use_failure": "post_tool_failure",
        }
        compact = lowered.replace("_", "").replace("-", "")
        if compact in aliases:
            return aliases[compact]
        return lowered.replace("-", "_")

    def _extract_content(self, event: Dict[str, Any]) -> str:
        """
        Extract searchable content from an event.

        Combines: tool name, file path, input, output snippet
        """
        parts = []

        # Event type
        event_type = self._normalize_event_type(
            event.get('event_type') or event.get('hook_event') or event.get('type') or event.get('kind')
        )
        if event_type:
            parts.append(event_type)

        # Tool name
        tool = event.get('tool_name') or event.get('tool')
        if tool:
            parts.append(str(tool))

        # File path (very important for domain detection)
        file_path = event.get('file_path')
        if not file_path:
            inp = event.get('input') or event.get('tool_input') or {}
            if isinstance(inp, dict):
                file_path = inp.get('file_path') or inp.get('path')
        if file_path:
            parts.append(str(file_path))

        # Input content
        inp = event.get('input') or event.get('tool_input')
        if inp:
            if isinstance(inp, dict):
                for v in inp.values():
                    if v and isinstance(v, str) and len(v) < 5000:
                        parts.append(v)
            elif isinstance(inp, str):
                parts.append(inp[:2000])

        payload = event.get('payload')
        if isinstance(payload, dict):
            for v in payload.values():
                if isinstance(v, str):
                    parts.append(v[:2000])
        elif isinstance(payload, str):
            parts.append(payload[:2000])

        # Output/result (limited)
        output = event.get('output') or event.get('result')
        if output and isinstance(output, str):
            parts.append(output[:1000])

        # CWD (project context)
        cwd = event.get('cwd') or event.get('data', {}).get('cwd')
        if cwd:
            parts.append(str(cwd))

        return ' '.join(parts)

    def _match_chip(self, chip: Chip, content_lower: str, content_raw: str) -> List[TriggerMatch]:
        """Match content against a chip's triggers."""
        matches = []
        seen_triggers = set()

        # Event-type triggers (high confidence)
        event_type = self._current_event_type or ""
        for event_trigger in getattr(chip, "trigger_events", []) or []:
            trigger_event = self._normalize_event_type(event_trigger)
            if event_type and event_type == trigger_event:
                seen_key = f"event:{event_trigger}"
                if seen_key in seen_triggers:
                    continue
                seen_triggers.add(seen_key)
                matches.append(TriggerMatch(
                    chip=chip,
                    observer=None,
                    trigger=str(event_trigger),
                    confidence=0.85,
                    content_snippet=str(event_trigger)
                ))

        # Tool triggers (contextual)
        tool_name = self._current_tool_name or ""
        for tool_trigger in getattr(chip, "trigger_tools", []) or []:
            if isinstance(tool_trigger, dict):
                name = tool_trigger.get("name", "")
                context_patterns = tool_trigger.get("context_contains", [])
            else:
                name = str(tool_trigger)
                context_patterns = []

            if tool_name and name.lower() == tool_name:
                if context_patterns and context_patterns != ["*"]:
                    if not any(self._match_trigger(p, content_lower) for p in context_patterns):
                        continue
                trigger_label = f"tool:{name}"
                seen_key = f"tool:{trigger_label}"
                if seen_key in seen_triggers:
                    continue
                seen_triggers.add(seen_key)
                matches.append(TriggerMatch(
                    chip=chip,
                    observer=None,
                    trigger=trigger_label,
                    confidence=0.8,
                    content_snippet=name
                ))

        # Match observer-level triggers (higher confidence if observer-specific)
        for observer in chip.observers:
            for trigger in observer.triggers:
                seen_key = f"observer:{observer.name}:{trigger}"
                if seen_key in seen_triggers:
                    continue

                match_result = self._match_trigger(trigger, content_lower)
                if match_result:
                    seen_triggers.add(seen_key)
                    confidence, snippet = match_result
                    # Boost confidence slightly for observer matches
                    matches.append(TriggerMatch(
                        chip=chip,
                        observer=observer,
                        trigger=trigger,
                        confidence=min(1.0, confidence + 0.1),
                        content_snippet=snippet
                    ))

        # Match chip-level triggers
        trigger_patterns = getattr(chip, "trigger_patterns", None) or chip.triggers
        for trigger in trigger_patterns:
            seen_key = f"pattern:{trigger}"
            if seen_key in seen_triggers:
                continue

            match_result = self._match_trigger(trigger, content_lower)
            if match_result:
                seen_triggers.add(seen_key)
                confidence, snippet = match_result
                matches.append(TriggerMatch(
                    chip=chip,
                    observer=None,
                    trigger=trigger,
                    confidence=confidence,
                    content_snippet=snippet
                ))

        return matches

    def _match_trigger(self, trigger: str, content: str) -> Optional[Tuple[float, str]]:
        """
        Match a trigger against content.

        Returns (confidence, snippet) or None.
        """
        trigger_lower = str(trigger or "").strip().lower()
        if not trigger_lower:
            return None

        # Exact word boundary match (highest confidence)
        pattern = r'(?<!\w)' + re.escape(trigger_lower) + r'(?!\w)'
        match = re.search(pattern, content)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            snippet = content[start:end]
            return (0.95, snippet)

        # Substring match (medium confidence) for longer triggers only.
        if len(trigger_lower) >= 4 and trigger_lower in content:
            idx = content.find(trigger_lower)
            start = max(0, idx - 20)
            end = min(len(content), idx + len(trigger_lower) + 20)
            snippet = content[start:end]
            return (0.7, snippet)

        return None

    def get_best_match(self, event: Dict[str, Any], chips: List[Chip]) -> Optional[TriggerMatch]:
        """Get the single best matching chip for an event."""
        matches = self.route_event(event, chips)
        return matches[0] if matches else None

    def get_matching_observers(self, event: Dict[str, Any], chips: List[Chip]) -> List[Tuple[Chip, ChipObserver, float]]:
        """Get all matching observers for an event (deduplicated)."""
        matches = self.route_event(event, chips)

        # Group by observer, keep highest confidence per observer
        observer_matches = {}
        for match in matches:
            if match.observer:
                key = (match.chip.id, match.observer.name)
                if key not in observer_matches or match.confidence > observer_matches[key][2]:
                    observer_matches[key] = (match.chip, match.observer, match.confidence)

        return list(observer_matches.values())



_router: Optional[ChipRouter] = None


def get_router() -> ChipRouter:
    """Get singleton chip router."""
    global _router
    if _router is None:
        _router = ChipRouter()
    return _router
