"""TasteBank API helpers for dashboard.

Keep dashboard logic thin.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.tastebank import add_item, stats, recent


def add_from_dashboard(payload: Dict[str, Any]) -> Dict[str, Any]:
    domain = str(payload.get("domain") or "").strip()
    source = str(payload.get("source") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    label = str(payload.get("label") or "").strip()

    if not domain or not source:
        return {"ok": False, "error": "missing_domain_or_source"}

    item = add_item(domain=domain, source=source, notes=notes, label=label)
    return {"ok": True, "item": item.to_dict()}
