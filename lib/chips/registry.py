"""
Chip Registry - Track which chips are active per project.

This was the second missing piece: knowing which chips to run
for a given project context.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

from .loader import Chip, ChipLoader

log = logging.getLogger("spark.chips")

REGISTRY_FILE = Path.home() / ".spark" / "chip_registry.json"


class ChipRegistry:
    """
    Tracks which chips are installed and active.

    - Installed: Available in the system
    - Active: Currently enabled for a project or globally
    """

    def __init__(self, auto_discover: bool = True):
        self.loader = ChipLoader()
        self._installed: Dict[str, Chip] = {}
        self._active: Dict[str, Set[str]] = {}  # project_path -> chip_ids
        self._global_active: Set[str] = set()   # chips active for all projects
        self._load_registry()
        if auto_discover:
            self._discover_chips()

    def _load_registry(self):
        """Load registry from disk."""
        if REGISTRY_FILE.exists():
            try:
                with open(REGISTRY_FILE, 'r') as f:
                    data = json.load(f)
                    for proj, chips in data.get('active', {}).items():
                        self._active[proj] = set(chips)
                    self._global_active = set(data.get('global_active', []))
            except Exception as e:
                log.warning(f"Failed to load registry: {e}")

    def _save_registry(self):
        """Save registry to disk."""
        try:
            REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'active': {k: list(v) for k, v in self._active.items()},
                'global_active': list(self._global_active),
                'updated_at': datetime.now().isoformat()
            }
            with open(REGISTRY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save registry: {e}")

    def _discover_chips(self):
        """Discover and install all available chips."""
        chips = self.loader.discover_chips()
        for chip in chips:
            self._installed[chip.id] = chip
        log.info(f"Installed {len(chips)} chips")

    def get_installed(self) -> List[Chip]:
        """Get all installed chips."""
        return list(self._installed.values())

    def get_chip(self, chip_id: str) -> Optional[Chip]:
        """Get an installed chip by ID."""
        return self._installed.get(chip_id)

    def activate(self, chip_id: str, project_path: str = None) -> bool:
        """Activate a chip for a project (or globally if no project)."""
        if chip_id not in self._installed:
            log.warning(f"Chip {chip_id} not installed")
            return False

        if project_path:
            if project_path not in self._active:
                self._active[project_path] = set()
            self._active[project_path].add(chip_id)
        else:
            self._global_active.add(chip_id)

        self._save_registry()
        log.info(f"Activated chip {chip_id}" + (f" for {project_path}" if project_path else " globally"))
        return True

    def deactivate(self, chip_id: str, project_path: str = None):
        """Deactivate a chip."""
        if project_path and project_path in self._active:
            self._active[project_path].discard(chip_id)
        else:
            self._global_active.discard(chip_id)
        self._save_registry()

    def get_active_chips(self, project_path: str = None) -> List[Chip]:
        """Get all active chips for a project (includes global)."""
        chip_ids = set(self._global_active)
        if project_path and project_path in self._active:
            chip_ids.update(self._active[project_path])

        return [self._installed[cid] for cid in chip_ids if cid in self._installed]

    def auto_activate_for_content(self, content: str, project_path: str = None) -> List[Chip]:
        """
        Auto-activate chips based on content matching triggers.

        This is the KEY feature: when we see "lobster", "Three.js", "health",
        we automatically activate the game_dev chip.
        """
        activated = []
        content_lower = content.lower()

        for chip in self._installed.values():
            # Check if chip already active
            if chip.id in self._global_active:
                continue
            if project_path and project_path in self._active and chip.id in self._active[project_path]:
                continue

            # Check triggers
            matches = chip.matches_content(content)
            if matches:
                if project_path:
                    if project_path not in self._active:
                        self._active[project_path] = set()
                    self._active[project_path].add(chip.id)
                else:
                    self._global_active.add(chip.id)

                activated.append(chip)
                log.info(f"Auto-activated chip {chip.id} (matched: {matches[:3]})")

        if activated:
            self._save_registry()

        return activated
