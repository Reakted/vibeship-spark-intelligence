"""
EIDOS Core Models: The Intelligence Primitives

These are the objects that make learning mandatory and measurable:
- Episode: Bounded learning unit with goals, constraints, budgets
- Step: Decision packet with prediction → outcome → evaluation
- Distillation: Extracted rules from experience
- Policy: Operating constraints
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Phase(Enum):
    """Episode phases - transitions are rule-driven, not LLM-decided."""
    EXPLORE = "explore"         # Gathering information
    DIAGNOSE = "diagnose"       # Understanding the problem
    EXECUTE = "execute"         # Taking action
    CONSOLIDATE = "consolidate" # Extracting lessons
    ESCALATE = "escalate"       # Giving up / asking for help


class Outcome(Enum):
    """Episode outcomes."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ESCALATED = "escalated"
    IN_PROGRESS = "in_progress"


class Evaluation(Enum):
    """Step evaluation results."""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class DistillationType(Enum):
    """Types of distilled knowledge."""
    HEURISTIC = "heuristic"       # "If X, then Y"
    SHARP_EDGE = "sharp_edge"     # Gotcha / pitfall
    ANTI_PATTERN = "anti_pattern" # "Never do X because..."
    PLAYBOOK = "playbook"         # Step-by-step procedure
    POLICY = "policy"             # Operating constraint


class ActionType(Enum):
    """Types of actions a step can take."""
    TOOL_CALL = "tool_call"
    REASONING = "reasoning"
    QUESTION = "question"
    WAIT = "wait"


@dataclass
class Budget:
    """Resource constraints for an episode."""
    max_steps: int = 25
    max_time_seconds: int = 720  # 12 minutes
    max_retries_per_error: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "max_time_seconds": self.max_time_seconds,
            "max_retries_per_error": self.max_retries_per_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        return cls(
            max_steps=data.get("max_steps", 25),
            max_time_seconds=data.get("max_time_seconds", 720),
            max_retries_per_error=data.get("max_retries_per_error", 3),
        )


@dataclass
class Episode:
    """
    A bounded learning unit.

    Every episode has:
    - A clear goal
    - Success criteria
    - Budget constraints
    - Explicit phase tracking
    """
    episode_id: str
    goal: str
    success_criteria: str
    constraints: List[str] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    phase: Phase = Phase.EXPLORE
    outcome: Outcome = Outcome.IN_PROGRESS
    final_evaluation: str = ""
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None

    # Tracking
    step_count: int = 0
    error_counts: Dict[str, int] = field(default_factory=dict)  # error_signature -> count

    def __post_init__(self):
        if not self.episode_id:
            self.episode_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.goal[:50]}:{self.start_ts}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def is_budget_exceeded(self) -> bool:
        """Check if any budget limit is exceeded."""
        if self.step_count >= self.budget.max_steps:
            return True
        elapsed = time.time() - self.start_ts
        if elapsed >= self.budget.max_time_seconds:
            return True
        return False

    def is_error_limit_exceeded(self, error_signature: str) -> bool:
        """Check if we've hit the retry limit for an error."""
        count = self.error_counts.get(error_signature, 0)
        return count >= self.budget.max_retries_per_error

    def record_error(self, error_signature: str):
        """Record an error occurrence."""
        self.error_counts[error_signature] = self.error_counts.get(error_signature, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "goal": self.goal,
            "success_criteria": self.success_criteria,
            "constraints": self.constraints,
            "budget": self.budget.to_dict(),
            "phase": self.phase.value,
            "outcome": self.outcome.value,
            "final_evaluation": self.final_evaluation,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "step_count": self.step_count,
            "error_counts": self.error_counts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        return cls(
            episode_id=data["episode_id"],
            goal=data["goal"],
            success_criteria=data.get("success_criteria", ""),
            constraints=data.get("constraints", []),
            budget=Budget.from_dict(data.get("budget", {})),
            phase=Phase(data.get("phase", "explore")),
            outcome=Outcome(data.get("outcome", "in_progress")),
            final_evaluation=data.get("final_evaluation", ""),
            start_ts=data.get("start_ts", time.time()),
            end_ts=data.get("end_ts"),
            step_count=data.get("step_count", 0),
            error_counts=data.get("error_counts", {}),
        )


@dataclass
class Step:
    """
    The atomic intelligence unit - a decision packet.

    This is the core substrate for learning because it captures:
    - What was decided (and what wasn't)
    - Why it was decided
    - What was predicted
    - What actually happened
    - What we learned

    MANDATORY FIELDS (must be filled for step to be valid):
    - intent
    - decision
    - prediction
    - result (after action)
    - evaluation (after action)
    """
    step_id: str
    episode_id: str

    # BEFORE ACTION (mandatory)
    intent: str                           # What I'm trying to accomplish
    decision: str                         # What I chose to do
    alternatives: List[str] = field(default_factory=list)  # What I considered but didn't do
    assumptions: List[str] = field(default_factory=list)   # What must be true for this to work
    prediction: str = ""                  # What I expect to happen
    confidence_before: float = 0.5        # 0-1, how sure I am

    # THE ACTION
    action_type: ActionType = ActionType.REASONING
    action_details: Dict[str, Any] = field(default_factory=dict)  # Minimal provenance

    # AFTER ACTION (mandatory)
    result: str = ""                      # What actually happened
    evaluation: Evaluation = Evaluation.UNKNOWN
    surprise_level: float = 0.0           # 0-1, how different from prediction
    lesson: str = ""                      # 1-3 bullets, what we learned
    confidence_after: float = 0.5         # Updated confidence

    # MEMORY BINDING (mandatory)
    retrieved_memories: List[str] = field(default_factory=list)  # Memory IDs retrieved
    memory_cited: bool = False            # Did we actually use retrieved memory?
    memory_useful: Optional[bool] = None  # Was the memory helpful?

    # VALIDATION (mandatory)
    validated: bool = False               # Did we check the result?
    validation_method: str = ""           # How we validated

    # Metadata
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.step_id:
            self.step_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.episode_id}:{self.intent[:30]}:{self.created_at}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def is_valid_before_action(self) -> tuple:
        """Check if step has required fields before action."""
        missing = []
        if not self.intent:
            missing.append("intent")
        if not self.decision:
            missing.append("decision")
        if not self.prediction:
            missing.append("prediction")
        return (len(missing) == 0, missing)

    def is_valid_after_action(self) -> tuple:
        """Check if step has required fields after action."""
        missing = []
        if not self.result:
            missing.append("result")
        if self.evaluation == Evaluation.UNKNOWN:
            missing.append("evaluation")
        if not self.validated and not self.validation_method:
            missing.append("validation")
        return (len(missing) == 0, missing)

    def calculate_surprise(self) -> float:
        """Calculate how surprising the result was vs prediction."""
        if not self.prediction or not self.result:
            return 0.0

        # Simple heuristic: if evaluation doesn't match expected, high surprise
        if self.evaluation == Evaluation.FAIL:
            return 0.8  # Failure is usually surprising
        if self.evaluation == Evaluation.PARTIAL:
            return 0.5

        # Check for keyword mismatches
        pred_words = set(self.prediction.lower().split())
        result_words = set(self.result.lower().split())
        if pred_words and result_words:
            overlap = len(pred_words & result_words) / len(pred_words | result_words)
            return 1.0 - overlap

        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "episode_id": self.episode_id,
            "intent": self.intent,
            "decision": self.decision,
            "alternatives": self.alternatives,
            "assumptions": self.assumptions,
            "prediction": self.prediction,
            "confidence_before": self.confidence_before,
            "action_type": self.action_type.value,
            "action_details": self.action_details,
            "result": self.result,
            "evaluation": self.evaluation.value,
            "surprise_level": self.surprise_level,
            "lesson": self.lesson,
            "confidence_after": self.confidence_after,
            "retrieved_memories": self.retrieved_memories,
            "memory_cited": self.memory_cited,
            "memory_useful": self.memory_useful,
            "validated": self.validated,
            "validation_method": self.validation_method,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step":
        return cls(
            step_id=data["step_id"],
            episode_id=data["episode_id"],
            intent=data.get("intent", ""),
            decision=data.get("decision", ""),
            alternatives=data.get("alternatives", []),
            assumptions=data.get("assumptions", []),
            prediction=data.get("prediction", ""),
            confidence_before=data.get("confidence_before", 0.5),
            action_type=ActionType(data.get("action_type", "reasoning")),
            action_details=data.get("action_details", {}),
            result=data.get("result", ""),
            evaluation=Evaluation(data.get("evaluation", "unknown")),
            surprise_level=data.get("surprise_level", 0.0),
            lesson=data.get("lesson", ""),
            confidence_after=data.get("confidence_after", 0.5),
            retrieved_memories=data.get("retrieved_memories", []),
            memory_cited=data.get("memory_cited", False),
            memory_useful=data.get("memory_useful"),
            validated=data.get("validated", False),
            validation_method=data.get("validation_method", ""),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class Distillation:
    """
    Where intelligence lives - extracted rules from experience.

    Types:
    - HEURISTIC: "If X, then Y"
    - SHARP_EDGE: Gotcha / pitfall
    - ANTI_PATTERN: "Never do X because..."
    - PLAYBOOK: Step-by-step procedure
    - POLICY: Operating constraint
    """
    distillation_id: str
    type: DistillationType
    statement: str

    # Applicability
    domains: List[str] = field(default_factory=list)    # Where this applies
    triggers: List[str] = field(default_factory=list)   # When to retrieve this
    anti_triggers: List[str] = field(default_factory=list)  # When NOT to apply

    # Evidence
    source_steps: List[str] = field(default_factory=list)  # Step IDs that generated this
    validation_count: int = 0
    contradiction_count: int = 0
    confidence: float = 0.5

    # Usage tracking
    times_retrieved: int = 0
    times_used: int = 0      # Actually influenced decision
    times_helped: int = 0    # Led to success

    # Metadata
    created_at: float = field(default_factory=time.time)
    revalidate_by: Optional[float] = None

    def __post_init__(self):
        if not self.distillation_id:
            self.distillation_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.type.value}:{self.statement[:50]}:{self.created_at}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    @property
    def effectiveness(self) -> float:
        """How effective is this distillation when used?"""
        if self.times_used == 0:
            return 0.5  # Unknown
        return self.times_helped / self.times_used

    @property
    def reliability(self) -> float:
        """How reliable is this distillation?"""
        total = self.validation_count + self.contradiction_count
        if total == 0:
            return self.confidence
        return self.validation_count / total

    def record_retrieval(self):
        """Record that this was retrieved."""
        self.times_retrieved += 1

    def record_usage(self, helped: bool):
        """Record that this was used and whether it helped."""
        self.times_used += 1
        if helped:
            self.times_helped += 1
            self.validation_count += 1
        else:
            self.contradiction_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distillation_id": self.distillation_id,
            "type": self.type.value,
            "statement": self.statement,
            "domains": self.domains,
            "triggers": self.triggers,
            "anti_triggers": self.anti_triggers,
            "source_steps": self.source_steps,
            "validation_count": self.validation_count,
            "contradiction_count": self.contradiction_count,
            "confidence": self.confidence,
            "times_retrieved": self.times_retrieved,
            "times_used": self.times_used,
            "times_helped": self.times_helped,
            "created_at": self.created_at,
            "revalidate_by": self.revalidate_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Distillation":
        return cls(
            distillation_id=data["distillation_id"],
            type=DistillationType(data["type"]),
            statement=data["statement"],
            domains=data.get("domains", []),
            triggers=data.get("triggers", []),
            anti_triggers=data.get("anti_triggers", []),
            source_steps=data.get("source_steps", []),
            validation_count=data.get("validation_count", 0),
            contradiction_count=data.get("contradiction_count", 0),
            confidence=data.get("confidence", 0.5),
            times_retrieved=data.get("times_retrieved", 0),
            times_used=data.get("times_used", 0),
            times_helped=data.get("times_helped", 0),
            created_at=data.get("created_at", time.time()),
            revalidate_by=data.get("revalidate_by"),
        )


@dataclass
class Policy:
    """
    Operating constraints - what we must respect.

    Sources:
    - USER: Explicitly stated by user
    - DISTILLED: Extracted from experience
    - INFERRED: Detected from patterns
    """
    policy_id: str
    statement: str
    scope: str = "GLOBAL"  # GLOBAL, PROJECT, SESSION
    priority: int = 50     # Higher = more important
    source: str = "INFERRED"
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.policy_id:
            self.policy_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.scope}:{self.statement[:50]}:{self.created_at}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "statement": self.statement,
            "scope": self.scope,
            "priority": self.priority,
            "source": self.source,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        return cls(
            policy_id=data["policy_id"],
            statement=data["statement"],
            scope=data.get("scope", "GLOBAL"),
            priority=data.get("priority", 50),
            source=data.get("source", "INFERRED"),
            created_at=data.get("created_at", time.time()),
        )
