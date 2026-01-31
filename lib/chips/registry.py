"""
ChipRegistry: Tracks installed and active chips.

Manages:
- Which chips are installed
- Which chips are active (processing events)
- Chip metadata and stats
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .loader import ChipSpec, load_chip


# Default paths
SPARK_DIR = Path.home() / ".spark"
CHIPS_DIR = SPARK_DIR / "chips"
REGISTRY_FILE = CHIPS_DIR / "registry.json"
ACTIVE_FILE = CHIPS_DIR / "active.json"


@dataclass
class ChipStats:
    """Statistics for a chip."""
    insights_generated: int = 0
    events_processed: int = 0
    predictions_made: int = 0
    prediction_accuracy: float = 0.0
    evolutions: int = 0
    last_active: Optional[str] = None


@dataclass
class ChipEntry:
    """Registry entry for an installed chip."""
    id: str
    name: str
    version: str
    source: str  # "official", "community", "custom"
    path: str
    installed_at: str
    active: bool = False
    stats: ChipStats = field(default_factory=ChipStats)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "path": self.path,
            "installed_at": self.installed_at,
            "active": self.active,
            "stats": {
                "insights_generated": self.stats.insights_generated,
                "events_processed": self.stats.events_processed,
                "predictions_made": self.stats.predictions_made,
                "prediction_accuracy": self.stats.prediction_accuracy,
                "evolutions": self.stats.evolutions,
                "last_active": self.stats.last_active,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChipEntry":
        """Create from dictionary."""
        stats_data = data.get("stats", {})
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            source=data.get("source", "custom"),
            path=data["path"],
            installed_at=data["installed_at"],
            active=data.get("active", False),
            stats=ChipStats(
                insights_generated=stats_data.get("insights_generated", 0),
                events_processed=stats_data.get("events_processed", 0),
                predictions_made=stats_data.get("predictions_made", 0),
                prediction_accuracy=stats_data.get("prediction_accuracy", 0.0),
                evolutions=stats_data.get("evolutions", 0),
                last_active=stats_data.get("last_active"),
            ),
        )


class ChipRegistry:
    """
    Registry of installed and active chips.

    Manages chip lifecycle:
    - install: Add chip to registry
    - uninstall: Remove chip from registry
    - activate: Enable chip for event processing
    - deactivate: Disable chip
    """

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or REGISTRY_FILE
        self._chips: Dict[str, ChipEntry] = {}
        self._loaded_specs: Dict[str, ChipSpec] = {}
        self._load()

    def _load(self):
        """Load registry from disk."""
        if not self.registry_path.exists():
            self._chips = {}
            return

        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)
            for chip_id, chip_data in data.get("chips", {}).items():
                self._chips[chip_id] = ChipEntry.from_dict(chip_data)
        except Exception:
            self._chips = {}

    def _save(self):
        """Save registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "chips": {chip_id: entry.to_dict() for chip_id, entry in self._chips.items()},
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def install(self, path: Path, source: str = "custom") -> ChipEntry:
        """
        Install a chip from YAML file.

        Args:
            path: Path to chip YAML file
            source: "official", "community", or "custom"

        Returns:
            ChipEntry for the installed chip
        """
        spec = load_chip(path)

        # Check if already installed
        if spec.id in self._chips:
            existing = self._chips[spec.id]
            # Update if newer version
            if spec.version > existing.version:
                existing.version = spec.version
                existing.path = str(path.resolve())
                self._save()
            return existing

        # Create new entry
        entry = ChipEntry(
            id=spec.id,
            name=spec.name,
            version=spec.version,
            source=source,
            path=str(path.resolve()),
            installed_at=datetime.utcnow().isoformat(),
            active=False,
        )

        self._chips[spec.id] = entry
        self._loaded_specs[spec.id] = spec
        self._save()

        return entry

    def uninstall(self, chip_id: str) -> bool:
        """Uninstall a chip."""
        if chip_id not in self._chips:
            return False

        del self._chips[chip_id]
        if chip_id in self._loaded_specs:
            del self._loaded_specs[chip_id]
        self._save()
        return True

    def activate(self, chip_id: str) -> bool:
        """Activate a chip for event processing."""
        if chip_id not in self._chips:
            return False

        self._chips[chip_id].active = True
        self._save()
        return True

    def deactivate(self, chip_id: str) -> bool:
        """Deactivate a chip."""
        if chip_id not in self._chips:
            return False

        self._chips[chip_id].active = False
        self._save()
        return True

    def get(self, chip_id: str) -> Optional[ChipEntry]:
        """Get chip entry by ID."""
        return self._chips.get(chip_id)

    def get_spec(self, chip_id: str) -> Optional[ChipSpec]:
        """Get loaded chip spec by ID."""
        if chip_id not in self._loaded_specs:
            entry = self._chips.get(chip_id)
            if entry:
                try:
                    self._loaded_specs[chip_id] = load_chip(Path(entry.path))
                except Exception:
                    return None
        return self._loaded_specs.get(chip_id)

    def list_all(self) -> List[ChipEntry]:
        """List all installed chips."""
        return list(self._chips.values())

    def list_active(self) -> List[ChipEntry]:
        """List active chips."""
        return [c for c in self._chips.values() if c.active]

    def get_active_specs(self) -> List[ChipSpec]:
        """Get specs for all active chips."""
        specs = []
        for entry in self.list_active():
            spec = self.get_spec(entry.id)
            if spec:
                specs.append(spec)
        return specs

    def update_stats(self, chip_id: str, **updates):
        """Update chip statistics."""
        entry = self._chips.get(chip_id)
        if not entry:
            return

        stats = entry.stats
        for key, value in updates.items():
            if hasattr(stats, key):
                if key in ("insights_generated", "events_processed", "predictions_made", "evolutions"):
                    # Increment counters
                    current = getattr(stats, key)
                    setattr(stats, key, current + value)
                else:
                    setattr(stats, key, value)

        stats.last_active = datetime.utcnow().isoformat()
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        active = self.list_active()
        return {
            "total_installed": len(self._chips),
            "total_active": len(active),
            "chips": {chip_id: entry.to_dict() for chip_id, entry in self._chips.items()},
        }


# Singleton instance
_registry: Optional[ChipRegistry] = None


def get_registry() -> ChipRegistry:
    """Get the global chip registry instance."""
    global _registry
    if _registry is None:
        _registry = ChipRegistry()
    return _registry
