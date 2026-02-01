"""Heuristics for filtering primitive/operational text from learnings."""

from __future__ import annotations

import re


_TOOL_TOKENS = (
    "read",
    "edit",
    "write",
    "bash",
    "glob",
    "grep",
    "todowrite",
    "taskoutput",
    "webfetch",
    "powershell",
    "python",
    "killshell",
    "cli",
)

_PRIM_KW = (
    "struggle",
    "overconfident",
    "fails",
    "failed",
    "error",
    "timeout",
    "usage",
    "sequence",
    "pattern",
)

_TOOL_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _TOOL_TOKENS) + r")\b", re.I)


def is_primitive_text(text: str) -> bool:
    """Return True when text looks like low-level operational telemetry."""
    if not text:
        return False
    tl = text.lower()
    if "->" in text or "→" in text:
        return True
    if "sequence" in tl and ("work" in tl or "pattern" in tl):
        return True
    if _TOOL_RE.search(tl) and any(k in tl for k in _PRIM_KW):
        return True
    return False
