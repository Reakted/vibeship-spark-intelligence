"""
ChipRouter: Routes events to matching chips based on triggers.

Handles:
- Pattern matching (text content)
- Event type matching
- Tool context matching
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .loader import ChipSpec
from .registry import get_registry


class ChipRouter:
    """
    Routes events to chips that should process them.

    Matching priority:
    1. Event type triggers (exact match)
    2. Tool triggers (tool name + context)
    3. Pattern triggers (regex in content)
    """

    def __init__(self):
        self._registry = get_registry()

    def route(self, event: Dict) -> List[ChipSpec]:
        """
        Find all chips that should process this event.

        Args:
            event: The event dict to route

        Returns:
            List of ChipSpecs that matched
        """
        matched_chips = []
        active_specs = self._registry.get_active_specs()

        for spec in active_specs:
            if self._matches(spec, event):
                matched_chips.append(spec)

        return matched_chips

    def _matches(self, spec: ChipSpec, event: Dict) -> bool:
        """Check if a chip's triggers match the event."""
        triggers = spec.triggers

        # 1. Check event type triggers
        event_type = event.get("type") or event.get("hook_event") or event.get("kind", "")
        if event_type and event_type in triggers.events:
            return True

        # 2. Check tool triggers
        tool_name = event.get("tool_name") or event.get("tool", "")
        if tool_name:
            for tool_trigger in triggers.tools:
                if tool_trigger.get("name", "").lower() == tool_name.lower():
                    # Check context_contains if specified
                    context_patterns = tool_trigger.get("context_contains", [])
                    if not context_patterns or context_patterns == ["*"]:
                        return True
                    # Check if any context pattern matches
                    event_content = self._get_event_content(event)
                    for pattern in context_patterns:
                        if pattern.lower() in event_content.lower():
                            return True

        # 3. Check pattern triggers
        content = self._get_event_content(event)
        if content and triggers.matches(content):
            return True

        return False

    def _get_event_content(self, event: Dict) -> str:
        """Extract searchable content from event."""
        parts = []

        # Common content fields
        for key in ("content", "text", "message", "prompt", "user_prompt", "description"):
            if key in event:
                parts.append(str(event[key]))

        # Payload content
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            for key in ("text", "content", "message", "prompt"):
                if key in payload:
                    parts.append(str(payload[key]))
        elif isinstance(payload, str):
            parts.append(payload)

        # Tool input/output
        for key in ("tool_input", "tool_output", "result"):
            if key in event:
                val = event[key]
                if isinstance(val, str):
                    parts.append(val)
                elif isinstance(val, dict):
                    parts.append(str(val))

        return " ".join(parts)

    def get_matching_chips_with_scores(self, event: Dict) -> List[Tuple[ChipSpec, float]]:
        """
        Find matching chips with confidence scores.

        Returns list of (ChipSpec, score) tuples, sorted by score.
        """
        results = []
        active_specs = self._registry.get_active_specs()

        for spec in active_specs:
            score = self._match_score(spec, event)
            if score > 0:
                results.append((spec, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _match_score(self, spec: ChipSpec, event: Dict) -> float:
        """Calculate match score for a chip/event pair."""
        score = 0.0
        triggers = spec.triggers

        # Event type match = 1.0
        event_type = event.get("type") or event.get("hook_event") or event.get("kind", "")
        if event_type and event_type in triggers.events:
            score += 1.0

        # Tool match with context = 0.8
        tool_name = event.get("tool_name") or event.get("tool", "")
        if tool_name:
            for tool_trigger in triggers.tools:
                if tool_trigger.get("name", "").lower() == tool_name.lower():
                    score += 0.8
                    break

        # Pattern match = 0.5 per match (max 1.0)
        content = self._get_event_content(event)
        if content:
            pattern_matches = 0
            for pattern in triggers.patterns:
                if pattern.lower() in content.lower():
                    pattern_matches += 1
            score += min(1.0, pattern_matches * 0.5)

        # Domain match = 0.3 per match
        for domain in spec.domains:
            if domain.lower() in content.lower():
                score += 0.3
                break

        return score


# Singleton instance
_router: Optional[ChipRouter] = None


def get_router() -> ChipRouter:
    """Get the global chip router instance."""
    global _router
    if _router is None:
        _router = ChipRouter()
    return _router
