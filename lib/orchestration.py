"""
Spark Orchestration: Lightweight Agent Coordination

KISS principle: One file, minimal abstractions, maximum stability.

This module enables:
- Agent registration and capability tracking
- Goal hierarchy (company -> team -> agent -> task)
- Handoff tracking between agents
- Team-level pattern extraction
- Coordination learnings that improve over time

Key insight: We don't build a new system. We extend existing Spark
infrastructure (cognitive learner, Mind sync, event queue).
"""

import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Reuse existing Spark infrastructure
from .cognitive_learner import (
    get_cognitive_learner,
    CognitiveInsight,
    CognitiveCategory
)


# ============= Configuration =============
ORCHESTRATION_DIR = Path.home() / ".spark" / "orchestration"
AGENTS_FILE = ORCHESTRATION_DIR / "agents.json"
GOALS_FILE = ORCHESTRATION_DIR / "goals.json"
HANDOFFS_FILE = ORCHESTRATION_DIR / "handoffs.jsonl"
PATTERNS_FILE = ORCHESTRATION_DIR / "team_patterns.json"


# ============= Enums =============
class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class HandoffType(Enum):
    """Type of handoff between agents."""
    SEQUENTIAL = "sequential"      # A finishes, B starts
    PARALLEL = "parallel"          # A and B work simultaneously
    REVIEW = "review"              # B reviews A's work
    FALLBACK = "fallback"          # B takes over when A fails
    ESCALATION = "escalation"      # A escalates to more capable B


# ============= Data Classes =============
@dataclass
class Agent:
    """An agent that can participate in coordination."""
    agent_id: str
    name: str
    capabilities: List[str]          # What skills/tools it has
    specialization: str              # Primary domain
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    success_rate: float = 0.5        # Learned over time
    avg_task_time_ms: float = 0.0    # Learned over time
    total_tasks: int = 0
    total_handoffs_sent: int = 0
    total_handoffs_received: int = 0


@dataclass
class Goal:
    """A goal in the hierarchy."""
    goal_id: str
    title: str
    description: str
    level: str                       # "company", "team", "agent", "task"
    parent_goal_id: Optional[str]    # Links to parent
    status: GoalStatus = GoalStatus.PENDING
    assigned_agents: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    success_criteria: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)  # What we learned


@dataclass
class Handoff:
    """A handoff between agents."""
    handoff_id: str
    from_agent: str
    to_agent: str
    handoff_type: HandoffType
    context: Dict[str, Any]          # What's being passed
    goal_id: Optional[str]           # Which goal this serves
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: Optional[bool] = None   # Outcome (filled later)
    latency_ms: Optional[float] = None
    notes: str = ""


@dataclass
class TeamPattern:
    """A learned pattern about how agents work together."""
    pattern_id: str
    agents_involved: List[str]       # e.g., ["auth-agent", "ui-agent"]
    sequence: List[str]              # e.g., ["auth", "ui", "test"]
    success_rate: float
    avg_duration_ms: float
    times_observed: int
    context: str                     # When this pattern applies
    last_observed: str
    counter_examples: List[str] = field(default_factory=list)


# ============= Core Orchestrator =============
class SparkOrchestrator:
    """
    Lightweight coordinator for agents, goals, and learnings.

    Design principles:
    - Single source of truth (files + cognitive learner)
    - No external dependencies beyond existing Spark
    - Fail gracefully, learn continuously
    - KISS: Simple data structures, simple flows
    """

    def __init__(self):
        ORCHESTRATION_DIR.mkdir(parents=True, exist_ok=True)
        self.agents: Dict[str, Agent] = self._load_agents()
        self.goals: Dict[str, Goal] = self._load_goals()
        self.patterns: Dict[str, TeamPattern] = self._load_patterns()
        self.cognitive = get_cognitive_learner()

    # ============= Agent Management =============
    def register_agent(self, agent: Agent) -> bool:
        """Register an agent for coordination."""
        self.agents[agent.agent_id] = agent
        self._save_agents()

        # Learn about this agent
        self.cognitive.add_insight(
            category=CognitiveCategory.CONTEXT,
            insight=f"Agent '{agent.name}' registered with capabilities: {', '.join(agent.capabilities)}",
            confidence=1.0,
            context=f"specialization: {agent.specialization}"
        )
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def find_agents_for_capability(self, capability: str) -> List[Agent]:
        """Find agents that have a specific capability."""
        return [
            a for a in self.agents.values()
            if capability.lower() in [c.lower() for c in a.capabilities]
        ]

    def update_agent_stats(self, agent_id: str, success: bool, duration_ms: float):
        """Update agent performance stats after a task."""
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        agent.total_tasks += 1

        # Running average for success rate
        old_rate = agent.success_rate
        agent.success_rate = (old_rate * (agent.total_tasks - 1) + (1.0 if success else 0.0)) / agent.total_tasks

        # Running average for task time
        if agent.avg_task_time_ms == 0:
            agent.avg_task_time_ms = duration_ms
        else:
            agent.avg_task_time_ms = (agent.avg_task_time_ms * (agent.total_tasks - 1) + duration_ms) / agent.total_tasks

        self._save_agents()

    # ============= Goal Management =============
    def create_goal(self, goal: Goal) -> str:
        """Create a new goal."""
        if not goal.goal_id:
            goal.goal_id = self._generate_id("goal")

        self.goals[goal.goal_id] = goal
        self._save_goals()

        # Learn about goal creation patterns
        if goal.parent_goal_id:
            parent = self.goals.get(goal.parent_goal_id)
            if parent:
                self.cognitive.add_insight(
                    category=CognitiveCategory.CONTEXT,
                    insight=f"Goal '{goal.title}' created under '{parent.title}'",
                    confidence=0.8,
                    context=f"level: {goal.level}, parent_level: {parent.level}"
                )

        return goal.goal_id

    def update_goal_status(self, goal_id: str, status: GoalStatus, learning: Optional[str] = None):
        """Update goal status and optionally record a learning."""
        if goal_id not in self.goals:
            return False

        goal = self.goals[goal_id]
        old_status = goal.status
        goal.status = status

        if status == GoalStatus.COMPLETED:
            goal.completed_at = datetime.now().isoformat()

        if learning:
            goal.learnings.append(learning)

            # Promote significant learnings
            self.cognitive.add_insight(
                category=CognitiveCategory.WISDOM,
                insight=learning,
                confidence=0.7,
                context=f"goal: {goal.title}, transition: {old_status.value} -> {status.value}"
            )

        self._save_goals()
        return True

    def get_goal_tree(self, root_goal_id: str) -> Dict:
        """Get a goal and all its descendants."""
        if root_goal_id not in self.goals:
            return {}

        root = self.goals[root_goal_id]
        children = [
            self.get_goal_tree(g.goal_id)
            for g in self.goals.values()
            if g.parent_goal_id == root_goal_id
        ]

        return {
            "goal": asdict(root),
            "children": children
        }

    def get_active_goals(self, level: Optional[str] = None) -> List[Goal]:
        """Get goals that are in progress or pending."""
        active_statuses = {GoalStatus.PENDING, GoalStatus.IN_PROGRESS}
        goals = [g for g in self.goals.values() if g.status in active_statuses]

        if level:
            goals = [g for g in goals if g.level == level]

        return sorted(goals, key=lambda g: g.created_at, reverse=True)

    # ============= Handoff Tracking =============
    def record_handoff(self, handoff: Handoff) -> str:
        """Record a handoff between agents."""
        if not handoff.handoff_id:
            handoff.handoff_id = self._generate_id("handoff")

        # Update agent stats
        if handoff.from_agent in self.agents:
            self.agents[handoff.from_agent].total_handoffs_sent += 1
        if handoff.to_agent in self.agents:
            self.agents[handoff.to_agent].total_handoffs_received += 1
        self._save_agents()

        # Append to handoffs log
        with open(HANDOFFS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(handoff), default=str) + "\n")

        return handoff.handoff_id

    def complete_handoff(self, handoff_id: str, success: bool, notes: str = ""):
        """Mark a handoff as complete and learn from it."""
        # Read, find, update, rewrite (simple approach)
        handoffs = self._read_recent_handoffs(100)
        updated = False

        for h in handoffs:
            if h.get("handoff_id") == handoff_id:
                h["success"] = success
                h["notes"] = notes
                updated = True

                # Learn from this handoff
                from_agent = h.get("from_agent", "unknown")
                to_agent = h.get("to_agent", "unknown")
                handoff_type = h.get("handoff_type", "unknown")

                # Convert context dict to string for cognitive insight
                ctx = h.get("context", {})
                ctx_str = json.dumps(ctx)[:200] if isinstance(ctx, dict) else str(ctx)[:200]

                if success:
                    self.cognitive.add_insight(
                        category=CognitiveCategory.COORDINATION,
                        insight=f"Handoff {from_agent} -> {to_agent} ({handoff_type}) succeeded",
                        confidence=0.8,
                        context=ctx_str
                    )
                else:
                    self.cognitive.add_insight(
                        category=CognitiveCategory.SELF_AWARENESS,
                        insight=f"Handoff {from_agent} -> {to_agent} ({handoff_type}) failed: {notes}",
                        confidence=0.9,
                        context=ctx_str
                    )

                break

        if updated:
            self._extract_team_patterns(handoffs)

        return updated

    def _read_recent_handoffs(self, limit: int = 100) -> List[Dict]:
        """Read recent handoffs from the log."""
        if not HANDOFFS_FILE.exists():
            return []

        handoffs = []
        with open(HANDOFFS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    handoffs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        return handoffs[-limit:]

    # ============= Pattern Extraction =============
    def _extract_team_patterns(self, handoffs: List[Dict]):
        """Extract team patterns from handoff history."""
        # Group by goal_id to find sequences
        by_goal: Dict[str, List[Dict]] = {}
        for h in handoffs:
            goal_id = h.get("goal_id")
            if goal_id:
                if goal_id not in by_goal:
                    by_goal[goal_id] = []
                by_goal[goal_id].append(h)

        # Find patterns in sequences
        for goal_id, goal_handoffs in by_goal.items():
            if len(goal_handoffs) < 2:
                continue

            # Sort by timestamp
            sorted_handoffs = sorted(goal_handoffs, key=lambda h: h.get("timestamp", ""))

            # Extract sequence
            agents = []
            for h in sorted_handoffs:
                if h.get("from_agent") and h["from_agent"] not in agents:
                    agents.append(h["from_agent"])
                if h.get("to_agent") and h["to_agent"] not in agents:
                    agents.append(h["to_agent"])

            if len(agents) < 2:
                continue

            # Calculate success rate for this sequence
            successes = sum(1 for h in sorted_handoffs if h.get("success") is True)
            total = sum(1 for h in sorted_handoffs if h.get("success") is not None)

            if total == 0:
                continue

            success_rate = successes / total

            # Create or update pattern
            pattern_key = "->".join(agents)
            pattern_id = hashlib.sha256(pattern_key.encode()).hexdigest()[:12]

            if pattern_id in self.patterns:
                p = self.patterns[pattern_id]
                p.times_observed += 1
                # Running average
                p.success_rate = (p.success_rate * (p.times_observed - 1) + success_rate) / p.times_observed
                p.last_observed = datetime.now().isoformat()
            else:
                goal = self.goals.get(goal_id)
                context = goal.title if goal else "unknown"

                self.patterns[pattern_id] = TeamPattern(
                    pattern_id=pattern_id,
                    agents_involved=agents,
                    sequence=agents,
                    success_rate=success_rate,
                    avg_duration_ms=0,  # TODO: calculate from timestamps
                    times_observed=1,
                    context=context,
                    last_observed=datetime.now().isoformat()
                )

        self._save_patterns()

        # Promote high-confidence patterns to cognitive learnings
        for p in self.patterns.values():
            if p.times_observed >= 3 and p.success_rate >= 0.7:
                self.cognitive.add_insight(
                    category=CognitiveCategory.WISDOM,
                    insight=f"Team pattern: {' -> '.join(p.sequence)} works {p.success_rate:.0%} of the time",
                    confidence=min(0.9, p.success_rate),
                    context=f"observed {p.times_observed} times for '{p.context}'"
                )

    # ============= Coordination Recommendations =============
    def recommend_next_agent(self, current_agent: str, task_type: str, goal_id: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Recommend the next agent based on learned patterns.

        Returns: (agent_id, reasoning)
        """
        # 1. Check if we have a pattern for this
        for p in sorted(self.patterns.values(), key=lambda x: x.success_rate * x.times_observed, reverse=True):
            if current_agent in p.agents_involved:
                idx = p.agents_involved.index(current_agent)
                if idx < len(p.agents_involved) - 1:
                    next_agent = p.agents_involved[idx + 1]
                    reason = f"Pattern '{' -> '.join(p.sequence)}' has {p.success_rate:.0%} success rate ({p.times_observed} observations)"
                    return next_agent, reason

        # 2. Fall back to capability matching
        capable = self.find_agents_for_capability(task_type)
        if capable:
            # Pick best success rate
            best = max(capable, key=lambda a: a.success_rate)
            return best.agent_id, f"Best success rate ({best.success_rate:.0%}) for capability '{task_type}'"

        return None, "No suitable agent found"

    def get_team_effectiveness(self, agent_ids: List[str]) -> Dict:
        """Get effectiveness metrics for a team of agents."""
        relevant_patterns = [
            p for p in self.patterns.values()
            if any(a in p.agents_involved for a in agent_ids)
        ]

        if not relevant_patterns:
            return {
                "team": agent_ids,
                "patterns_found": 0,
                "avg_success_rate": 0.5,
                "recommendation": "No patterns yet. Work together more to build data."
            }

        avg_success = sum(p.success_rate for p in relevant_patterns) / len(relevant_patterns)
        total_obs = sum(p.times_observed for p in relevant_patterns)

        best_pattern = max(relevant_patterns, key=lambda p: p.success_rate)

        return {
            "team": agent_ids,
            "patterns_found": len(relevant_patterns),
            "total_observations": total_obs,
            "avg_success_rate": avg_success,
            "best_sequence": best_pattern.sequence,
            "best_sequence_success": best_pattern.success_rate,
            "recommendation": f"Use sequence: {' -> '.join(best_pattern.sequence)}" if best_pattern.success_rate > 0.7 else "More data needed"
        }

    # ============= Stats and Insights =============
    def get_stats(self) -> Dict:
        """Get orchestration statistics."""
        handoffs = self._read_recent_handoffs(1000)
        successful = sum(1 for h in handoffs if h.get("success") is True)
        failed = sum(1 for h in handoffs if h.get("success") is False)

        active_goals = self.get_active_goals()
        completed_goals = [g for g in self.goals.values() if g.status == GoalStatus.COMPLETED]

        return {
            "agents": {
                "total": len(self.agents),
                "by_specialization": self._count_by_field(self.agents.values(), "specialization"),
            },
            "goals": {
                "total": len(self.goals),
                "active": len(active_goals),
                "completed": len(completed_goals),
                "by_level": self._count_by_field(self.goals.values(), "level"),
            },
            "handoffs": {
                "total": len(handoffs),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / (successful + failed) if (successful + failed) > 0 else 0,
            },
            "patterns": {
                "discovered": len(self.patterns),
                "high_confidence": len([p for p in self.patterns.values() if p.success_rate >= 0.7]),
            }
        }

    def _count_by_field(self, items, field: str) -> Dict[str, int]:
        """Count items by a field value."""
        counts: Dict[str, int] = {}
        for item in items:
            val = getattr(item, field, "unknown") if hasattr(item, field) else item.get(field, "unknown")
            if isinstance(val, Enum):
                val = val.value
            counts[val] = counts.get(val, 0) + 1
        return counts

    # ============= Persistence =============
    def _load_agents(self) -> Dict[str, Agent]:
        """Load agents from disk."""
        if not AGENTS_FILE.exists():
            return {}
        try:
            data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
            return {k: Agent(**v) for k, v in data.items()}
        except Exception:
            return {}

    def _save_agents(self):
        """Save agents to disk."""
        data = {k: asdict(v) for k, v in self.agents.items()}
        AGENTS_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load_goals(self) -> Dict[str, Goal]:
        """Load goals from disk."""
        if not GOALS_FILE.exists():
            return {}
        try:
            data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
            goals = {}
            for k, v in data.items():
                v["status"] = GoalStatus(v.get("status", "pending"))
                goals[k] = Goal(**v)
            return goals
        except Exception:
            return {}

    def _save_goals(self):
        """Save goals to disk."""
        data = {k: asdict(v) for k, v in self.goals.items()}
        GOALS_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load_patterns(self) -> Dict[str, TeamPattern]:
        """Load patterns from disk."""
        if not PATTERNS_FILE.exists():
            return {}
        try:
            data = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
            return {k: TeamPattern(**v) for k, v in data.items()}
        except Exception:
            return {}

    def _save_patterns(self):
        """Save patterns to disk."""
        data = {k: asdict(v) for k, v in self.patterns.items()}
        PATTERNS_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        return f"{prefix}_{int(time.time() * 1000)}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]}"


# ============= Singleton =============
_orchestrator: Optional[SparkOrchestrator] = None

def get_orchestrator() -> SparkOrchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SparkOrchestrator()
    return _orchestrator


# ============= Convenience Functions =============
def register_agent(agent_id: str, name: str, capabilities: List[str], specialization: str) -> bool:
    """Register an agent for coordination."""
    agent = Agent(
        agent_id=agent_id,
        name=name,
        capabilities=capabilities,
        specialization=specialization
    )
    return get_orchestrator().register_agent(agent)


def create_goal(title: str, description: str, level: str, parent_goal_id: Optional[str] = None) -> str:
    """Create a new goal."""
    goal = Goal(
        goal_id="",  # Will be generated
        title=title,
        description=description,
        level=level,
        parent_goal_id=parent_goal_id
    )
    return get_orchestrator().create_goal(goal)


def record_handoff(from_agent: str, to_agent: str, context: Dict, handoff_type: str = "sequential", goal_id: Optional[str] = None) -> str:
    """Record a handoff between agents."""
    handoff = Handoff(
        handoff_id="",  # Will be generated
        from_agent=from_agent,
        to_agent=to_agent,
        handoff_type=HandoffType(handoff_type),
        context=context,
        goal_id=goal_id
    )
    return get_orchestrator().record_handoff(handoff)


def complete_handoff(handoff_id: str, success: bool, notes: str = "") -> bool:
    """Complete a handoff and record outcome."""
    return get_orchestrator().complete_handoff(handoff_id, success, notes)


def recommend_next(current_agent: str, task_type: str) -> Tuple[Optional[str], str]:
    """Get recommendation for next agent."""
    return get_orchestrator().recommend_next_agent(current_agent, task_type)


def get_orchestration_stats() -> Dict:
    """Get orchestration statistics."""
    return get_orchestrator().get_stats()
