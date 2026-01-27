#!/usr/bin/env python3
"""Spark event schema (v1)

Goal: make Spark ingestion platform-agnostic.

Adapters (Clawdbot, Claude Code, webhooks, etc.) emit SparkEventV1 objects.
Spark core stores them, then distills into insights/surprises/voice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SparkEventKind(str, Enum):
    MESSAGE = "message"
    TOOL = "tool"
    COMMAND = "command"
    SYSTEM = "system"


@dataclass
class SparkEventV1:
    """Normalized event payload."""

    v: int
    source: str                 # e.g., "clawdbot", "claude_code", "webhook"
    kind: SparkEventKind        # message/tool/command/system
    ts: float                   # unix seconds
    session_id: str
    payload: Dict[str, Any]
    trace_id: Optional[str] = None  # de-dupe across adapters

    def to_dict(self) -> Dict[str, Any]:
        return {
            "v": self.v,
            "source": self.source,
            "kind": self.kind.value,
            "ts": self.ts,
            "session_id": self.session_id,
            "payload": self.payload,
            "trace_id": self.trace_id,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SparkEventV1":
        if int(d.get("v", 0)) != 1:
            raise ValueError("Unsupported event version")
        return SparkEventV1(
            v=1,
            source=str(d.get("source") or "unknown"),
            kind=SparkEventKind(str(d.get("kind") or "system")),
            ts=float(d.get("ts") or 0),
            session_id=str(d.get("session_id") or "unknown"),
            payload=dict(d.get("payload") or {}),
            trace_id=(str(d["trace_id"]) if d.get("trace_id") else None),
        )
