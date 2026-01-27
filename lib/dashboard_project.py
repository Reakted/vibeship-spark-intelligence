"""Dashboard helpers for project inference + bank preview.

Kept separate so dashboard.py stays mostly presentation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pathlib import Path
import json

from lib.memory_banks import infer_project_key

_BANK_DIR = Path.home() / ".spark" / "banks"
_PROJECTS_DIR = _BANK_DIR / "projects"



def get_active_project() -> Optional[str]:
    return infer_project_key()


def get_project_memory_preview(project_key: Optional[str], limit: int = 5) -> List[Dict[str, Any]]:
    if not project_key:
        return []

    # MVP: show the most recent project-scoped memories.
    path = _PROJECTS_DIR / f"{project_key}.jsonl"
    if not path.exists():
        return []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
        if len(out) >= limit:
            break

    return out
