"""
Chip Loader - Parse chip YAML files into usable objects.

This was the first missing piece: we had beautiful YAML specs
but no code to read them.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

log = logging.getLogger("spark.chips")

# Default chips directory (relative to this package)
CHIPS_DIR = Path(__file__).parent.parent.parent / "chips"


@dataclass
class ChipObserver:
    """An observer that captures domain-specific data."""
    name: str
    description: str
    triggers: List[str]
    capture_required: Dict[str, str] = field(default_factory=dict)
    capture_optional: Dict[str, str] = field(default_factory=dict)


@dataclass
class Chip:
    """A loaded chip definition."""
    id: str
    name: str
    version: str
    description: str
    domains: List[str]
    triggers: List[str]  # All triggers (patterns + events + observer triggers)
    observers: List[ChipObserver]
    outcomes_positive: List[Dict]
    outcomes_negative: List[Dict]
    questions: List[Dict]
    source_path: Optional[Path] = None

    def matches_content(self, content: str) -> List[str]:
        """Check which triggers match the content. Returns matched triggers."""
        content_lower = content.lower()
        matched = []
        for trigger in self.triggers:
            if trigger.lower() in content_lower:
                matched.append(trigger)
        return matched

    def get_matching_observers(self, content: str) -> List[ChipObserver]:
        """Get observers whose triggers match the content."""
        content_lower = content.lower()
        matched = []
        for obs in self.observers:
            for trigger in obs.triggers:
                if trigger.lower() in content_lower:
                    matched.append(obs)
                    break
        return matched


class ChipLoader:
    """Loads chip definitions from YAML files."""

    def __init__(self, chips_dir: Path = None):
        self.chips_dir = chips_dir or CHIPS_DIR
        self._cache: Dict[str, Chip] = {}

    def load_chip(self, path: Path) -> Optional[Chip]:
        """Load a chip from a YAML file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            # Handle nested 'chip' key
            chip_data = data.get('chip', data)

            # Parse triggers from multiple sources
            triggers = self._parse_triggers(data)

            # Parse observers
            observers = self._parse_observers(data.get('observers', []))

            # Add observer triggers to chip triggers
            for obs in observers:
                triggers.extend(obs.triggers)
            triggers = list(set(triggers))  # Dedupe

            # Parse outcomes
            outcomes = data.get('outcomes', {})

            chip = Chip(
                id=chip_data.get('id', path.stem.replace('.chip', '')),
                name=chip_data.get('name', chip_data.get('id', 'Unknown')),
                version=chip_data.get('version', '0.1.0'),
                description=chip_data.get('description', ''),
                domains=chip_data.get('domains', []),
                triggers=triggers,
                observers=observers,
                outcomes_positive=outcomes.get('positive', []),
                outcomes_negative=outcomes.get('negative', []),
                questions=data.get('questions', []),
                source_path=path
            )

            self._cache[chip.id] = chip
            log.info(f"Loaded chip: {chip.id} with {len(triggers)} triggers, {len(observers)} observers")
            return chip

        except Exception as e:
            log.error(f"Failed to load chip {path}: {e}")
            return None

    def _parse_triggers(self, data: Dict) -> List[str]:
        """Parse triggers from chip data."""
        triggers = []
        triggers_data = data.get('triggers', {})

        if isinstance(triggers_data, dict):
            triggers.extend(triggers_data.get('patterns', []))
            triggers.extend(triggers_data.get('events', []))
        elif isinstance(triggers_data, list):
            triggers = triggers_data

        return triggers

    def _parse_observers(self, observers_data: List) -> List[ChipObserver]:
        """Parse observer definitions."""
        observers = []
        for obs in observers_data:
            capture = obs.get('capture', {})
            observers.append(ChipObserver(
                name=obs.get('name', ''),
                description=obs.get('description', ''),
                triggers=obs.get('triggers', []),
                capture_required=capture.get('required', {}),
                capture_optional=capture.get('optional', {})
            ))
        return observers

    def discover_chips(self) -> List[Chip]:
        """Discover all chips in the chips directory."""
        chips = []

        if not self.chips_dir.exists():
            log.warning(f"Chips directory not found: {self.chips_dir}")
            return chips

        # Load single-file chips
        for path in self.chips_dir.glob("*.chip.yaml"):
            chip = self.load_chip(path)
            if chip:
                chips.append(chip)

        log.info(f"Discovered {len(chips)} chips")
        return chips

    def get_chip(self, chip_id: str) -> Optional[Chip]:
        """Get a cached chip by ID."""
        return self._cache.get(chip_id)

    def get_all_chips(self) -> List[Chip]:
        """Get all cached chips."""
        return list(self._cache.values())
