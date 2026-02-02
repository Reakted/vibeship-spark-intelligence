# Pattern Detection → EIDOS Integration Plan

**Goal:** Connect pattern detectors to EIDOS infrastructure so learning becomes mandatory and produces intelligence, not noise.

**Status:** IMPLEMENTED
**Created:** 2026-02-02
**Completed:** 2026-02-02
**Author:** Spark Intelligence

## Implementation Summary

All phases completed:

| Phase | Component | File | Status |
|-------|-----------|------|--------|
| 1 | RequestTracker | `lib/pattern_detection/request_tracker.py` | DONE |
| 2 | PatternDistiller | `lib/pattern_detection/distiller.py` | DONE |
| 3 | MemoryGate | `lib/pattern_detection/memory_gate.py` | DONE |
| 4 | Store methods | `lib/eidos/store.py` (enhanced) | DONE |
| 5 | StructuralRetriever | `lib/eidos/retriever.py` | DONE |
| 6 | Pipeline integration | `lib/pattern_detection/aggregator.py` | DONE |

---

## The Problem

Current state: Two disconnected systems

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Raw Events ──→ Pattern Detectors ──→ cognitive_insights.json  │
│       │              │                        │                 │
│       │              │                        ▼                 │
│       │              │                   SHALLOW                │
│       │              │              "User persistently          │
│       │              │               asking about: X"           │
│       │              │                                          │
│       ▼              │                                          │
│  EIDOS Steps ────────┼──────────────→ eidos_store.db           │
│  (unused by          │                      │                   │
│   pattern            │                      ▼                   │
│   detectors)         │                 STRUCTURED               │
│                      │              intent, prediction,         │
│                      │              outcome, lesson             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Problems:
1. Pattern detectors ignore EIDOS Step structure
2. No link between user requests and outcomes
3. Insights lack decision context
4. Two separate storage systems
5. No distillation into reusable rules
```

---

## The Solution

Connect pattern detection to EIDOS so every insight has decision→outcome→lesson structure.

```
┌─────────────────────────────────────────────────────────────────┐
│                    TARGET ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Message                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │  Step Envelope  │  ← Wrap in EIDOS structure                │
│  │  - intent       │                                           │
│  │  - prediction   │                                           │
│  │  - hypothesis   │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│       Action Taken                                              │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ Complete Step   │  ← Fill outcome fields                    │
│  │  - result       │                                           │
│  │  - evaluation   │                                           │
│  │  - lesson       │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌──────────────────┐                  │
│  │ Pattern         │────▶│ Memory Gate      │                  │
│  │ Detection       │     │ (score > 0.5?)   │                  │
│  └────────┬────────┘     └────────┬─────────┘                  │
│           │                       │                             │
│           │              ┌────────┴─────────┐                  │
│           │              │                  │                   │
│           ▼              ▼                  ▼                   │
│  ┌─────────────────┐  PERSIST         DISCARD                  │
│  │ Distillation    │                                           │
│  │ - heuristic     │                                           │
│  │ - sharp_edge    │                                           │
│  │ - playbook      │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│     eidos_store.db (single source of truth)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Step Envelope for User Requests
**Priority:** HIGH
**Effort:** Medium
**Files:** `lib/pattern_detection/semantic.py`, `lib/pattern_detection/repetition.py`

#### 1.1 Create UserRequestStep wrapper

```python
# lib/pattern_detection/request_tracker.py (NEW FILE)

from lib.eidos.models import Step, Evaluation, ActionType
from typing import Optional, Dict, Any
from dataclasses import dataclass
import time

@dataclass
class PendingRequest:
    """A user request awaiting resolution."""
    step: Step
    request_text: str
    context: Dict[str, Any]
    created_at: float

class RequestTracker:
    """
    Track user requests through the EIDOS Step lifecycle.

    Flow:
    1. on_user_message() → Creates Step envelope
    2. on_action_taken() → Records decision
    3. on_outcome() → Completes Step with result/evaluation/lesson
    """

    def __init__(self):
        self.pending: Dict[str, PendingRequest] = {}  # step_id → PendingRequest
        self.completed: List[Step] = []

    def on_user_message(
        self,
        message: str,
        episode_id: str,
        context: Dict[str, Any]
    ) -> Step:
        """Wrap user request in EIDOS Step structure."""

        step = Step(
            step_id="",  # Auto-generated
            episode_id=episode_id,
            intent=f"Fulfill user request: {message[:100]}",
            decision="pending",
            hypothesis=self._extract_hypothesis(message),
            prediction="User satisfied if request fulfilled correctly",
            action_type=ActionType.REASONING,
            action_details={
                "request_text": message,
                "context_snapshot": context
            }
        )

        self.pending[step.step_id] = PendingRequest(
            step=step,
            request_text=message,
            context=context,
            created_at=time.time()
        )

        return step

    def on_action_taken(self, step_id: str, decision: str, tool_used: str = ""):
        """Record what action was taken for this request."""
        if step_id not in self.pending:
            return

        self.pending[step_id].step.decision = decision
        self.pending[step_id].step.action_details["tool_used"] = tool_used

    def on_outcome(
        self,
        step_id: str,
        result: str,
        success: bool,
        user_feedback: Optional[str] = None
    ) -> Step:
        """Complete the Step with outcome."""
        if step_id not in self.pending:
            return None

        pending = self.pending.pop(step_id)
        step = pending.step

        step.result = result
        step.evaluation = Evaluation.PASS if success else Evaluation.FAIL
        step.validated = True
        step.validation_method = "user_feedback" if user_feedback else "implicit"
        step.lesson = self._extract_lesson(step, user_feedback)
        step.surprise_level = step.calculate_surprise()

        self.completed.append(step)
        return step

    def _extract_hypothesis(self, message: str) -> str:
        """Extract testable hypothesis from user message."""
        # Simple extraction - can be enhanced
        msg_lower = message.lower()

        if "push" in msg_lower or "commit" in msg_lower:
            return "User wants code changes persisted to repository"
        if "fix" in msg_lower or "bug" in msg_lower:
            return "User wants identified issue resolved"
        if "add" in msg_lower or "create" in msg_lower:
            return "User wants new functionality implemented"
        if "clean" in msg_lower or "remove" in msg_lower:
            return "User wants unwanted items eliminated"

        return f"User wants: {message[:50]}"

    def _extract_lesson(self, step: Step, feedback: Optional[str]) -> str:
        """Extract lesson from completed step."""
        if step.evaluation == Evaluation.PASS:
            return f"Request '{step.intent[:30]}' resolved by: {step.decision[:50]}"
        else:
            return f"Request '{step.intent[:30]}' failed. Approach: {step.decision[:30]}. Need different strategy."

    def get_completed_steps(self, limit: int = 50) -> List[Step]:
        """Get recently completed steps for pattern detection."""
        return self.completed[-limit:]

    def get_pending_count(self) -> int:
        """Get count of unresolved requests."""
        return len(self.pending)
```

#### 1.2 Integrate into event processing

```python
# Modify lib/pattern_detection/aggregator.py

from lib.pattern_detection.request_tracker import RequestTracker

class PatternAggregator:
    def __init__(self):
        self.request_tracker = RequestTracker()
        # ... existing init

    def process_event(self, event: dict):
        # If user message, wrap in Step
        if event.get("type") == "user_message":
            step = self.request_tracker.on_user_message(
                message=event["content"],
                episode_id=event.get("episode_id", "default"),
                context=event.get("context", {})
            )
            event["step_id"] = step.step_id

        # If action completed, link to pending request
        if event.get("type") == "action_complete":
            self.request_tracker.on_action_taken(
                step_id=event.get("step_id"),
                decision=event.get("action"),
                tool_used=event.get("tool", "")
            )

        # If outcome observed, complete the Step
        if event.get("type") in ["success", "failure", "user_feedback"]:
            completed = self.request_tracker.on_outcome(
                step_id=event.get("step_id"),
                result=event.get("result", ""),
                success=event.get("type") != "failure",
                user_feedback=event.get("feedback")
            )
            if completed:
                self._process_completed_step(completed)
```

---

### Phase 2: Pattern Distiller
**Priority:** HIGH
**Effort:** Medium
**Files:** `lib/pattern_detection/distiller.py` (NEW)

#### 2.1 Create PatternDistiller

```python
# lib/pattern_detection/distiller.py (NEW FILE)

from lib.eidos.models import Step, Distillation, DistillationType, Evaluation
from typing import List, Optional, Dict
from collections import Counter

class PatternDistiller:
    """
    Convert detected patterns into EIDOS Distillations.

    This is the bridge between pattern detection and durable intelligence.
    Only patterns that pass the memory gate become Distillations.
    """

    def __init__(self, min_occurrences: int = 3, min_confidence: float = 0.6):
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence

    def distill_user_patterns(self, steps: List[Step]) -> List[Distillation]:
        """
        Analyze completed Steps to extract user behavior patterns.

        Returns Distillations only for patterns that:
        1. Occur >= min_occurrences times
        2. Have clear success/failure signal
        3. Pass memory gate scoring
        """
        distillations = []

        # Group steps by similar intent
        intent_groups = self._group_by_intent(steps)

        for intent_key, group_steps in intent_groups.items():
            if len(group_steps) < self.min_occurrences:
                continue

            distillation = self._distill_intent_group(intent_key, group_steps)
            if distillation and self._passes_memory_gate(distillation, group_steps):
                distillations.append(distillation)

        return distillations

    def _group_by_intent(self, steps: List[Step]) -> Dict[str, List[Step]]:
        """Group steps by normalized intent."""
        groups = {}
        for step in steps:
            key = self._normalize_intent(step.intent)
            if key not in groups:
                groups[key] = []
            groups[key].append(step)
        return groups

    def _normalize_intent(self, intent: str) -> str:
        """Normalize intent for grouping."""
        # Remove variable parts, keep semantic core
        intent_lower = intent.lower()

        # Extract action verbs
        actions = ["push", "commit", "fix", "add", "remove", "clean", "update", "create"]
        for action in actions:
            if action in intent_lower:
                return f"request:{action}"

        return f"request:{intent[:30]}"

    def _distill_intent_group(
        self,
        intent_key: str,
        steps: List[Step]
    ) -> Optional[Distillation]:
        """Create Distillation from a group of similar steps."""

        # Separate successes and failures
        successes = [s for s in steps if s.evaluation == Evaluation.PASS]
        failures = [s for s in steps if s.evaluation == Evaluation.FAIL]

        if not successes and not failures:
            return None

        # Calculate confidence
        total = len(successes) + len(failures)
        confidence = len(successes) / total if total > 0 else 0.5

        if confidence < self.min_confidence:
            # More failures than successes - create anti-pattern
            return self._create_anti_pattern(intent_key, failures, confidence)
        else:
            # More successes - create heuristic
            return self._create_heuristic(intent_key, successes, confidence)

    def _create_heuristic(
        self,
        intent_key: str,
        successes: List[Step],
        confidence: float
    ) -> Distillation:
        """Create a positive heuristic from successful patterns."""

        # Find most common successful decision
        decisions = [s.decision for s in successes if s.decision]
        if not decisions:
            return None

        best_decision = Counter(decisions).most_common(1)[0][0]

        # Extract lessons
        lessons = [s.lesson for s in successes if s.lesson]
        combined_lesson = lessons[0] if lessons else ""

        return Distillation(
            distillation_id="",  # Auto-generated
            type=DistillationType.HEURISTIC,
            statement=f"When user requests '{intent_key.replace('request:', '')}', "
                      f"respond with: {best_decision[:100]}",
            domains=["user_interaction"],
            triggers=[intent_key],
            source_steps=[s.step_id for s in successes[:5]],
            confidence=confidence
        )

    def _create_anti_pattern(
        self,
        intent_key: str,
        failures: List[Step],
        confidence: float
    ) -> Distillation:
        """Create an anti-pattern from failed attempts."""

        # Find what didn't work
        failed_decisions = [s.decision for s in failures if s.decision]
        if not failed_decisions:
            return None

        worst_decision = Counter(failed_decisions).most_common(1)[0][0]

        return Distillation(
            distillation_id="",
            type=DistillationType.ANTI_PATTERN,
            statement=f"When user requests '{intent_key.replace('request:', '')}', "
                      f"avoid: {worst_decision[:100]}",
            domains=["user_interaction"],
            anti_triggers=[intent_key],
            source_steps=[s.step_id for s in failures[:5]],
            confidence=1.0 - confidence  # Confidence in the anti-pattern
        )

    def _passes_memory_gate(
        self,
        distillation: Distillation,
        source_steps: List[Step]
    ) -> bool:
        """
        Determine if distillation should persist.

        Scoring:
        - Impact (unblocked progress): +0.3
        - Novelty (new pattern): +0.2
        - Surprise (prediction != outcome): +0.3
        - Recurrence (3+ times): +0.2
        - Irreversible (high stakes): +0.4

        Threshold: score > 0.5
        """
        score = 0.0

        # Impact: Did these steps make progress?
        progress_steps = [s for s in source_steps if s.progress_made]
        if len(progress_steps) > len(source_steps) * 0.5:
            score += 0.3

        # Novelty: Is this a new pattern? (check against existing distillations)
        # TODO: Check existing distillations for similarity
        score += 0.2  # Assume novel for now

        # Surprise: Were outcomes unexpected?
        avg_surprise = sum(s.surprise_level for s in source_steps) / len(source_steps)
        if avg_surprise > 0.3:
            score += 0.3

        # Recurrence: Multiple occurrences
        if len(source_steps) >= 3:
            score += 0.2

        # Irreversible: High stakes actions
        high_stakes = ["delete", "push", "deploy", "remove", "drop"]
        if any(hs in distillation.statement.lower() for hs in high_stakes):
            score += 0.4

        return score > 0.5
```

---

### Phase 3: Memory Gate Integration
**Priority:** MEDIUM
**Effort:** Small
**Files:** `lib/pattern_detection/memory_gate.py` (NEW)

#### 3.1 Standalone Memory Gate

```python
# lib/pattern_detection/memory_gate.py (NEW FILE)

from lib.eidos.models import Step, Distillation
from typing import Tuple
from dataclasses import dataclass

@dataclass
class GateScore:
    """Memory gate scoring result."""
    score: float
    passes: bool
    reasons: list[str]

class MemoryGate:
    """
    Decides what earns persistence.

    Only high-signal items become durable memory.
    Low-score items stay as short-lived cache only.
    """

    THRESHOLD = 0.5

    def score_step(self, step: Step) -> GateScore:
        """Score a Step for persistence."""
        score = 0.0
        reasons = []

        # Impact: Did it unblock progress?
        if step.progress_made:
            score += 0.3
            reasons.append("progress_made")

        # Novelty: New pattern?
        if not self._seen_similar_step(step):
            score += 0.2
            reasons.append("novel")

        # Surprise: Prediction != outcome?
        if step.surprise_level > 0.5:
            score += 0.3
            reasons.append(f"surprise:{step.surprise_level:.2f}")

        # Lesson extracted?
        if step.lesson and len(step.lesson) > 20:
            score += 0.15
            reasons.append("has_lesson")

        # Evidence gathered?
        if step.evidence_gathered:
            score += 0.1
            reasons.append("evidence")

        return GateScore(
            score=score,
            passes=score > self.THRESHOLD,
            reasons=reasons
        )

    def score_distillation(self, distillation: Distillation) -> GateScore:
        """Score a Distillation for persistence."""
        score = 0.0
        reasons = []

        # Has source evidence?
        if len(distillation.source_steps) >= 2:
            score += 0.3
            reasons.append(f"evidence:{len(distillation.source_steps)}")

        # High confidence?
        if distillation.confidence > 0.7:
            score += 0.2
            reasons.append(f"confidence:{distillation.confidence:.2f}")

        # Actionable (has triggers)?
        if distillation.triggers:
            score += 0.2
            reasons.append("actionable")

        # Not too generic?
        if len(distillation.statement) > 30:
            score += 0.1
            reasons.append("specific")

        # High stakes?
        high_stakes = ["security", "delete", "deploy", "auth", "payment"]
        if any(hs in distillation.statement.lower() for hs in high_stakes):
            score += 0.3
            reasons.append("high_stakes")

        return GateScore(
            score=score,
            passes=score > self.THRESHOLD,
            reasons=reasons
        )

    def _seen_similar_step(self, step: Step) -> bool:
        """Check if we've seen similar steps before."""
        # TODO: Implement similarity check against EIDOS store
        return False
```

---

### Phase 4: Unified Storage (EIDOS Store)
**Priority:** MEDIUM
**Effort:** Medium
**Files:** `lib/eidos/store.py`

#### 4.1 Add Distillation storage

```python
# Additions to lib/eidos/store.py

def save_distillation(self, distillation: Distillation) -> str:
    """Save a distillation to the store."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO distillations (
                distillation_id, type, statement, domains, triggers,
                anti_triggers, source_steps, validation_count,
                contradiction_count, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            distillation.distillation_id,
            distillation.type.value,
            distillation.statement,
            json.dumps(distillation.domains),
            json.dumps(distillation.triggers),
            json.dumps(distillation.anti_triggers),
            json.dumps(distillation.source_steps),
            distillation.validation_count,
            distillation.contradiction_count,
            distillation.confidence,
            distillation.created_at
        ))
        conn.commit()
    return distillation.distillation_id

def get_distillations_by_trigger(self, trigger: str) -> List[Distillation]:
    """Retrieve distillations that match a trigger."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM distillations
            WHERE triggers LIKE ?
            ORDER BY confidence DESC, validation_count DESC
        """, (f'%{trigger}%',))

        rows = cursor.fetchall()
        return [self._row_to_distillation(row) for row in rows]
```

---

### Phase 5: Retrieval by Structure
**Priority:** LOW
**Effort:** Medium
**Files:** `lib/eidos/retriever.py` (NEW)

#### 5.1 Structural retrieval

```python
# lib/eidos/retriever.py (NEW FILE)

from lib.eidos.models import Step, Distillation, DistillationType
from lib.eidos.store import EidosStore
from typing import List

class StructuralRetriever:
    """
    Retrieve by EIDOS structure, not text similarity.

    Priority order:
    1. Policies (what must we respect?)
    2. Playbooks (if task matches)
    3. Sharp edges (stack gotchas)
    4. Heuristics (if X then Y)
    5. Similar failures (learn from mistakes)
    """

    def __init__(self, store: EidosStore):
        self.store = store

    def retrieve_for_step(self, step: Step) -> List[Distillation]:
        """Retrieve relevant distillations for a step."""
        results = []

        # 1. Policies first (always apply)
        results.extend(self._get_policies())

        # 2. Playbooks if task matches
        playbooks = self._get_playbooks(step.intent)
        results.extend(playbooks)

        # 3. Sharp edges for tools being used
        tool = step.action_details.get("tool", "")
        if tool:
            results.extend(self._get_sharp_edges(tool))

        # 4. Heuristics matching intent
        results.extend(self._get_heuristics(step.intent))

        # 5. Similar failures
        if step.hypothesis:
            results.extend(self._get_similar_failures(step.hypothesis))

        # Dedupe and sort by confidence
        seen = set()
        unique = []
        for d in results:
            if d.distillation_id not in seen:
                seen.add(d.distillation_id)
                unique.append(d)

        return sorted(unique, key=lambda d: d.confidence, reverse=True)[:10]

    def _get_policies(self) -> List[Distillation]:
        return self.store.get_distillations_by_type(DistillationType.POLICY)

    def _get_playbooks(self, intent: str) -> List[Distillation]:
        playbooks = self.store.get_distillations_by_type(DistillationType.PLAYBOOK)
        return [p for p in playbooks if self._matches_trigger(intent, p.triggers)]

    def _get_sharp_edges(self, tool: str) -> List[Distillation]:
        edges = self.store.get_distillations_by_type(DistillationType.SHARP_EDGE)
        return [e for e in edges if tool.lower() in str(e.domains).lower()]

    def _get_heuristics(self, intent: str) -> List[Distillation]:
        return self.store.get_distillations_by_trigger(intent[:30])

    def _get_similar_failures(self, hypothesis: str) -> List[Distillation]:
        anti_patterns = self.store.get_distillations_by_type(DistillationType.ANTI_PATTERN)
        # Simple keyword matching for now
        keywords = set(hypothesis.lower().split())
        return [
            a for a in anti_patterns
            if any(k in a.statement.lower() for k in keywords)
        ][:3]

    def _matches_trigger(self, intent: str, triggers: List[str]) -> bool:
        intent_lower = intent.lower()
        return any(t.lower() in intent_lower for t in triggers)
```

---

## Migration Path

### Step 1: Add New Files (No Breaking Changes)
- [ ] Create `lib/pattern_detection/request_tracker.py`
- [ ] Create `lib/pattern_detection/distiller.py`
- [ ] Create `lib/pattern_detection/memory_gate.py`
- [ ] Create `lib/eidos/retriever.py`

### Step 2: Wire Into Existing Pipeline
- [ ] Modify `aggregator.py` to use RequestTracker
- [ ] Modify EIDOS store to save Distillations
- [ ] Add distillations table to SQLite schema

### Step 3: Deprecate Old Path
- [ ] Mark cognitive_insights.json as legacy
- [ ] Migrate existing valuable insights to Distillations
- [ ] Remove noise filtering from cognitive_learner (no longer needed)

### Step 4: Validate
- [ ] Test that user requests create Steps
- [ ] Test that patterns create Distillations
- [ ] Test that retrieval returns structured results
- [ ] Verify no regression in existing functionality

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Insights with decision context | ~0% | 100% |
| Insights with outcome tracking | ~0% | 100% |
| Noise ratio in storage | ~80% | <10% |
| Distillations (reusable rules) | 0 | 50+ |
| Retrieval by structure | No | Yes |

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `lib/pattern_detection/request_tracker.py` | Wrap user requests in Step envelopes |
| `lib/pattern_detection/distiller.py` | Convert patterns to Distillations |
| `lib/pattern_detection/memory_gate.py` | Score items for persistence |
| `lib/eidos/retriever.py` | Structural retrieval |

### Modified Files
| File | Changes |
|------|---------|
| `lib/pattern_detection/aggregator.py` | Use RequestTracker |
| `lib/eidos/store.py` | Add Distillation storage |
| `lib/eidos/models.py` | Already complete |

### Deprecated Files
| File | Action |
|------|--------|
| `lib/cognitive_learner.py` | Keep for now, phase out |
| `~/.spark/cognitive_insights.json` | Migrate then remove |

---

## Timeline

| Week | Focus |
|------|-------|
| 1 | Phase 1: RequestTracker + Step envelopes |
| 2 | Phase 2: PatternDistiller |
| 3 | Phase 3: Memory Gate + Phase 4: Storage |
| 4 | Phase 5: Retrieval + Migration |

---

## Open Questions

1. **Migration Strategy:** How do we migrate the 277 existing cognitive insights to Distillations?
2. **Real-time vs Batch:** Should distillation run in real-time or batch?
3. **Confidence Decay:** Should Distillation confidence decay over time like CognitiveInsight?
4. **User Feedback Signal:** How do we reliably detect user satisfaction?

---

*This plan converts pattern detection from a noise generator into an intelligence distillation pipeline by connecting it to EIDOS infrastructure.*
