"""
EIDOS Distillation Engine: Where Intelligence Crystallizes

Runs after every episode to extract reusable rules from experience.

The distillation process:
1. Post-episode reflection (what happened? why?)
2. Pattern identification (what's generalizable?)
3. Rule generation (if X, then Y)
4. Evidence linking (which steps prove this?)
5. Confidence assignment (how sure are we?)
6. Revalidation scheduling (when to re-check?)

Types of distillations:
- HEURISTIC: "If X, then Y"
- SHARP_EDGE: Gotcha / pitfall
- ANTI_PATTERN: "Never do X because..."
- PLAYBOOK: Step-by-step procedure
- POLICY: Operating constraint
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    Episode, Step, Distillation, DistillationType,
    Outcome, Evaluation, Phase
)


@dataclass
class ReflectionResult:
    """Results of post-episode reflection."""
    bottleneck: str = ""           # What was the real bottleneck?
    wrong_assumption: str = ""     # Which assumption was wrong?
    preventive_check: str = ""     # What check would have prevented this?
    new_rule: str = ""             # What rule should we adopt?
    stop_doing: str = ""           # What should we stop doing?
    key_insight: str = ""          # Most important learning
    confidence: float = 0.5


@dataclass
class DistillationCandidate:
    """A candidate distillation before validation."""
    type: DistillationType
    statement: str
    domains: List[str]
    triggers: List[str]
    source_steps: List[str]
    confidence: float
    rationale: str


class DistillationEngine:
    """
    Engine that extracts reusable rules from episode experience.

    The engine doesn't just summarize - it crystallizes actionable
    intelligence that can be reused in future episodes.
    """

    def __init__(self):
        # Track patterns across episodes
        self.pattern_counts: Dict[str, int] = {}  # pattern_sig -> count
        self.distillation_history: List[Distillation] = []

        # Revalidation tracking
        self.pending_revalidation: List[str] = []  # distillation_ids

    def reflect_on_episode(
        self,
        episode: Episode,
        steps: List[Step]
    ) -> ReflectionResult:
        """
        Perform post-episode reflection to identify key learnings.

        This generates prompts for LLM reflection, but the questions
        are deterministic based on episode outcome.
        """
        result = ReflectionResult()

        if not steps:
            return result

        # Analyze episode outcome
        if episode.outcome == Outcome.SUCCESS:
            result = self._reflect_on_success(episode, steps)
        elif episode.outcome == Outcome.FAILURE:
            result = self._reflect_on_failure(episode, steps)
        elif episode.outcome == Outcome.ESCALATED:
            result = self._reflect_on_escalation(episode, steps)
        else:
            result = self._reflect_on_partial(episode, steps)

        return result

    def _reflect_on_success(self, episode: Episode, steps: List[Step]) -> ReflectionResult:
        """Reflect on successful episode."""
        result = ReflectionResult()

        # Find the breakthrough step
        breakthrough = None
        for step in reversed(steps):
            if step.evaluation == Evaluation.PASS and step.confidence_after > 0.7:
                breakthrough = step
                break

        if breakthrough:
            result.key_insight = f"Success came from: {breakthrough.decision}"
            result.new_rule = f"When {breakthrough.intent}, try: {breakthrough.decision}"

        # Check for initial wrong assumptions
        wrong_assumptions = [s for s in steps if s.evaluation == Evaluation.FAIL and s.assumptions]
        if wrong_assumptions:
            first_wrong = wrong_assumptions[0]
            result.wrong_assumption = f"Initially assumed: {first_wrong.assumptions[0] if first_wrong.assumptions else 'N/A'}"
            result.preventive_check = f"Check assumption: {first_wrong.assumptions[0] if first_wrong.assumptions else 'N/A'}"

        # Identify what could be faster
        total_steps = len(steps)
        if total_steps > 5:
            result.bottleneck = f"Took {total_steps} steps - could optimize discovery phase"

        result.confidence = 0.8

        return result

    def _reflect_on_failure(self, episode: Episode, steps: List[Step]) -> ReflectionResult:
        """Reflect on failed episode."""
        result = ReflectionResult()

        # Find repeated errors
        error_steps = [s for s in steps if s.evaluation == Evaluation.FAIL]
        if len(error_steps) >= 2:
            result.bottleneck = f"Repeated failures ({len(error_steps)} times)"

        # Find the first failure
        if error_steps:
            first_fail = error_steps[0]
            result.wrong_assumption = f"First failure: {first_fail.prediction} vs {first_fail.result}"
            if first_fail.assumptions:
                result.preventive_check = f"Validate: {first_fail.assumptions[0]}"

        # Identify anti-pattern
        result.stop_doing = self._identify_anti_pattern(steps)
        result.confidence = 0.6

        return result

    def _reflect_on_escalation(self, episode: Episode, steps: List[Step]) -> ReflectionResult:
        """Reflect on escalated episode."""
        result = ReflectionResult()

        result.bottleneck = "Escalated - exceeded capability or budget"

        # What was tried
        approaches = set()
        for step in steps:
            if step.decision:
                approaches.add(step.decision[:50])

        if approaches:
            result.key_insight = f"Tried {len(approaches)} approaches without success"

        result.new_rule = "Escalate earlier when similar patterns appear"
        result.confidence = 0.5

        return result

    def _reflect_on_partial(self, episode: Episode, steps: List[Step]) -> ReflectionResult:
        """Reflect on partial success episode."""
        result = ReflectionResult()

        # What worked
        success_steps = [s for s in steps if s.evaluation == Evaluation.PASS]
        fail_steps = [s for s in steps if s.evaluation == Evaluation.FAIL]

        if success_steps:
            result.key_insight = f"{len(success_steps)} steps succeeded, {len(fail_steps)} failed"

        result.confidence = 0.6

        return result

    def _identify_anti_pattern(self, steps: List[Step]) -> str:
        """Identify what should be stopped."""
        # Look for repeated failures with same approach
        decisions = [s.decision for s in steps if s.evaluation == Evaluation.FAIL]

        if len(decisions) >= 2:
            # Simple check for repeated decision
            from collections import Counter
            counts = Counter(decisions)
            most_common = counts.most_common(1)
            if most_common and most_common[0][1] >= 2:
                return f"Stop: {most_common[0][0][:50]}"

        return ""

    def generate_distillations(
        self,
        episode: Episode,
        steps: List[Step],
        reflection: ReflectionResult
    ) -> List[DistillationCandidate]:
        """
        Generate candidate distillations from episode experience.

        Returns candidates that need validation before becoming
        permanent distillations.
        """
        candidates = []

        # 1. Generate from new_rule (HEURISTIC)
        if reflection.new_rule:
            candidates.append(DistillationCandidate(
                type=DistillationType.HEURISTIC,
                statement=reflection.new_rule,
                domains=self._extract_domains(episode, steps),
                triggers=self._extract_triggers(steps),
                source_steps=[s.step_id for s in steps if s.evaluation == Evaluation.PASS],
                confidence=reflection.confidence,
                rationale=f"Derived from successful episode: {episode.goal[:50]}"
            ))

        # 2. Generate from stop_doing (ANTI_PATTERN)
        if reflection.stop_doing:
            candidates.append(DistillationCandidate(
                type=DistillationType.ANTI_PATTERN,
                statement=reflection.stop_doing,
                domains=self._extract_domains(episode, steps),
                triggers=self._extract_triggers(steps),
                source_steps=[s.step_id for s in steps if s.evaluation == Evaluation.FAIL],
                confidence=reflection.confidence * 0.8,
                rationale=f"Derived from failures in: {episode.goal[:50]}"
            ))

        # 3. Generate from preventive_check (SHARP_EDGE)
        if reflection.preventive_check:
            candidates.append(DistillationCandidate(
                type=DistillationType.SHARP_EDGE,
                statement=reflection.preventive_check,
                domains=self._extract_domains(episode, steps),
                triggers=["before", "check", "validate"],
                source_steps=[s.step_id for s in steps[:3]],  # Early steps
                confidence=reflection.confidence * 0.7,
                rationale=f"Would have prevented issues in: {episode.goal[:50]}"
            ))

        # 4. Generate PLAYBOOK if episode was successful and had clear steps
        if episode.outcome == Outcome.SUCCESS and len(steps) >= 3:
            playbook = self._generate_playbook(episode, steps)
            if playbook:
                candidates.append(playbook)

        return candidates

    def _generate_playbook(
        self,
        episode: Episode,
        steps: List[Step]
    ) -> Optional[DistillationCandidate]:
        """Generate a playbook from successful episode."""
        # Get successful steps
        success_steps = [s for s in steps if s.evaluation == Evaluation.PASS]

        if len(success_steps) < 2:
            return None

        # Build step-by-step
        playbook_steps = []
        for i, step in enumerate(success_steps[:5], 1):  # Max 5 steps
            playbook_steps.append(f"{i}. {step.decision[:60]}")

        statement = f"Playbook for '{episode.goal[:30]}': " + " → ".join(playbook_steps)

        return DistillationCandidate(
            type=DistillationType.PLAYBOOK,
            statement=statement,
            domains=self._extract_domains(episode, steps),
            triggers=[episode.goal.split()[0].lower()] if episode.goal else [],
            source_steps=[s.step_id for s in success_steps],
            confidence=0.6,
            rationale="Successful step sequence"
        )

    def _extract_domains(self, episode: Episode, steps: List[Step]) -> List[str]:
        """Extract domains from episode and steps."""
        domains = set()

        # From episode goal
        goal_words = episode.goal.lower().split()
        domain_keywords = ["api", "auth", "database", "ui", "test", "deploy", "config"]
        for word in goal_words:
            if word in domain_keywords:
                domains.add(word)

        # From step intents
        for step in steps[:5]:
            for word in step.intent.lower().split()[:3]:
                if word in domain_keywords:
                    domains.add(word)

        return list(domains) if domains else ["general"]

    def _extract_triggers(self, steps: List[Step]) -> List[str]:
        """Extract triggers from steps."""
        triggers = set()

        for step in steps:
            # Extract first significant word from intent
            words = step.intent.lower().split()
            if words:
                triggers.add(words[0])

        return list(triggers)[:5]

    def finalize_distillation(
        self,
        candidate: DistillationCandidate
    ) -> Distillation:
        """
        Convert a validated candidate into a permanent distillation.
        """
        return Distillation(
            distillation_id="",  # Will be auto-generated
            type=candidate.type,
            statement=candidate.statement,
            domains=candidate.domains,
            triggers=candidate.triggers,
            source_steps=candidate.source_steps,
            confidence=candidate.confidence,
            # Set revalidation for 7 days
            revalidate_by=time.time() + (7 * 86400)
        )

    def schedule_revalidation(self, distillation_id: str, days: int = 7):
        """Schedule a distillation for revalidation."""
        self.pending_revalidation.append(distillation_id)

    def get_due_for_revalidation(self) -> List[str]:
        """Get distillation IDs due for revalidation."""
        due = self.pending_revalidation.copy()
        self.pending_revalidation = []
        return due

    def validate_distillation(
        self,
        distillation: Distillation,
        episode: Episode,
        steps: List[Step],
        helped: bool
    ) -> Distillation:
        """
        Update distillation based on validation outcome.

        Called when a distillation was retrieved and used.
        """
        distillation.times_used += 1

        if helped:
            distillation.times_helped += 1
            distillation.validation_count += 1
            # Increase confidence
            distillation.confidence = min(1.0, distillation.confidence + 0.05)
        else:
            distillation.contradiction_count += 1
            # Decrease confidence
            distillation.confidence = max(0.1, distillation.confidence - 0.1)

        return distillation

    def merge_similar_distillations(
        self,
        distillations: List[Distillation]
    ) -> List[Distillation]:
        """
        Merge distillations that are semantically similar.

        This prevents duplicate rules from accumulating.
        """
        if len(distillations) < 2:
            return distillations

        # Group by type
        by_type: Dict[DistillationType, List[Distillation]] = {}
        for d in distillations:
            if d.type not in by_type:
                by_type[d.type] = []
            by_type[d.type].append(d)

        merged = []
        for dtype, group in by_type.items():
            # Simple text similarity check
            merged.extend(self._merge_group(group))

        return merged

    def _merge_group(self, group: List[Distillation]) -> List[Distillation]:
        """Merge a group of same-type distillations."""
        if len(group) < 2:
            return group

        # Simple merge: keep highest confidence, combine evidence
        result = []
        used = set()

        for i, d1 in enumerate(group):
            if i in used:
                continue

            # Find similar distillations
            similar = [d1]
            for j, d2 in enumerate(group[i+1:], i+1):
                if j in used:
                    continue
                if self._are_similar(d1.statement, d2.statement):
                    similar.append(d2)
                    used.add(j)

            # Merge similar ones
            if len(similar) > 1:
                merged = self._merge_distillations(similar)
                result.append(merged)
            else:
                result.append(d1)

            used.add(i)

        return result

    def _are_similar(self, s1: str, s2: str) -> bool:
        """Check if two statements are similar."""
        # Simple word overlap check
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2) / len(words1 | words2)
        return overlap > 0.5

    def _merge_distillations(self, similar: List[Distillation]) -> Distillation:
        """Merge multiple similar distillations into one."""
        # Keep the one with highest confidence as base
        base = max(similar, key=lambda d: d.confidence)

        # Combine evidence
        all_sources = set()
        total_validations = 0
        total_contradictions = 0
        total_used = 0
        total_helped = 0

        for d in similar:
            all_sources.update(d.source_steps)
            total_validations += d.validation_count
            total_contradictions += d.contradiction_count
            total_used += d.times_used
            total_helped += d.times_helped

        # Update base with combined data
        base.source_steps = list(all_sources)
        base.validation_count = total_validations
        base.contradiction_count = total_contradictions
        base.times_used = total_used
        base.times_helped = total_helped

        return base


# Singleton instance
_distillation_engine: Optional[DistillationEngine] = None


def get_distillation_engine() -> DistillationEngine:
    """Get the singleton distillation engine instance."""
    global _distillation_engine
    if _distillation_engine is None:
        _distillation_engine = DistillationEngine()
    return _distillation_engine
