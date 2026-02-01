"""
EIDOS: Explicit Intelligence with Durable Outcomes & Semantics

The self-evolving intelligence system that forces learning through:
- Mandatory decision packets (not just logs)
- Prediction → Outcome → Evaluation loops
- Memory binding (retrieval is required, not optional)
- Distillation (experience → reusable rules)
- Control plane (watchers, phases, budgets)

The Five Layers:
1. Canonical Memory (SQLite) - Source of truth
2. Semantic Index - Embeddings for retrieval
3. Control Plane - Deterministic enforcement
4. Reasoning Engine - LLM (constrained by Control Plane)
5. Distillation Engine - Post-episode rule extraction

The Vertical Loop:
Action → Prediction → Outcome → Evaluation → Policy Update → Distillation → Mandatory Reuse
"""

from .models import (
    Episode, Step, Distillation, Policy,
    Budget, Phase, Outcome, Evaluation,
    DistillationType, ActionType
)
from .control_plane import (
    ControlPlane, get_control_plane,
    ControlDecision, WatcherAlert,
    WatcherType, BlockType
)
from .memory_gate import (
    MemoryGate, score_step_importance,
    ImportanceScore
)
from .distillation_engine import (
    DistillationEngine, get_distillation_engine,
    ReflectionResult, DistillationCandidate
)
from .store import EidosStore, get_store

__all__ = [
    # Core Models
    "Episode",
    "Step",
    "Distillation",
    "Policy",
    "Budget",
    "Phase",
    "Outcome",
    "Evaluation",
    "DistillationType",
    "ActionType",

    # Control Plane
    "ControlPlane",
    "get_control_plane",
    "ControlDecision",
    "WatcherAlert",
    "WatcherType",
    "BlockType",

    # Memory Gate
    "MemoryGate",
    "score_step_importance",
    "ImportanceScore",

    # Distillation Engine
    "DistillationEngine",
    "get_distillation_engine",
    "ReflectionResult",
    "DistillationCandidate",

    # Store
    "EidosStore",
    "get_store",
]
