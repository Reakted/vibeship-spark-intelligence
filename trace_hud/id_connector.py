"""Trace-ID context compatibility connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EidosStep:
    step_id: str = ""
    intent: str = ""
    prediction: str = ""
    result: str = ""
    evaluation: str = ""
    lesson: str = ""
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    surprise_level: float = 0.0


@dataclass
class EidosEpisode:
    episode_id: str = ""
    goal: str = ""
    outcome: str = ""
    phase: str = ""
    step_count: int = 0
    steps: List[EidosStep] = field(default_factory=list)


@dataclass
class AdvisoryRecord:
    advisory_id: str = ""
    task_plane: str = ""
    intent_family: str = ""
    emitted: bool = False
    advice: str = ""


@dataclass
class AgentFeedbackRecord:
    report_id: str = ""
    task: str = ""
    success: bool = False
    outcome: str = ""
    lesson_learned: str = ""


@dataclass
class CognitiveInsightRecord:
    insight_id: str = ""
    category: str = ""
    signal: str = ""
    confidence: float = 0.0
    times_validated: int = 0


@dataclass
class TraceContext:
    eidos_episodes: List[EidosEpisode] = field(default_factory=list)
    advisories: List[AdvisoryRecord] = field(default_factory=list)
    agent_feedback: List[AgentFeedbackRecord] = field(default_factory=list)
    cognitive_insights: List[CognitiveInsightRecord] = field(default_factory=list)


class IDConnector:
    """Minimal compatibility facade for trace context joins."""

    def __init__(self, spark_dir: Optional[Path] = None):
        self.spark_dir = Path(spark_dir or (Path.home() / ".spark"))

    def get_full_context(self, trace_id: str, session_id: str = "") -> TraceContext:
        del trace_id, session_id
        return TraceContext()

    def get_session_timeline(self, session_id: str) -> Dict[str, Any]:
        return {
            "session_id": str(session_id or ""),
            "eidos_episodes": [],
            "recent_traces": [],
        }
