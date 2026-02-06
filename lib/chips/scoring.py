"""
Insight Scoring - Score insights for value and promotion.

Determines whether an insight is primitive (operational) or
valuable (cognitive) based on multiple dimensions.
"""

import logging
import re
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Set

log = logging.getLogger("spark.chips.scoring")


@dataclass
class InsightScore:
    """Multi-dimensional score for an insight."""

    cognitive_value: float = 0.0    # Is this human-useful?
    outcome_linkage: float = 0.0    # Can we link to success/failure?
    uniqueness: float = 0.0         # Is this new information?
    actionability: float = 0.0      # Can this guide future actions?
    transferability: float = 0.0    # Applies beyond this project?
    domain_relevance: float = 0.0   # Relevant to active domain?

    @property
    def total(self) -> float:
        """Calculate weighted total score."""
        weights = {
            "cognitive_value": 0.30,
            "outcome_linkage": 0.20,
            "uniqueness": 0.15,
            "actionability": 0.15,
            "transferability": 0.10,
            "domain_relevance": 0.10,
        }
        return sum(getattr(self, k) * v for k, v in weights.items())

    @property
    def is_valuable(self) -> bool:
        """Quick check if insight is valuable enough."""
        return self.total >= 0.5

    @property
    def promotion_tier(self) -> str:
        """Determine promotion tier."""
        total = self.total
        if total >= 0.75:
            return "long_term"  # Permanent memory
        if total >= 0.5:
            return "working"    # Project memory
        if total >= 0.3:
            return "session"    # Session only
        return "discard"        # Don't store

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["total"] = self.total
        data["promotion_tier"] = self.promotion_tier
        return data


# Patterns that indicate PRIMITIVE (operational) insights
PRIMITIVE_PATTERNS = [
    # Tool sequences
    r"(?i)^(read|edit|write|bash|glob|grep)\s*(->|then)\s*(read|edit|write|bash)",
    r"(?i)tool\s+(sequence|chain|pattern)",
    r"(?i)(success|failure)\s+rate",
    # Timing/metrics
    r"(?i)\d+\s*(ms|seconds?|minutes?)\s*(timeout|elapsed|took)",
    r"(?i)processed\s+\d+\s+(events?|files?|lines?)",
    # File operations without context
    r"(?i)^(modified|read|wrote|deleted)\s+file",
    r"(?i)^file\s+(exists|not found|created)",
    # Error counts without insight
    r"(?i)^\d+\s+errors?\s+(found|detected|fixed)",
]

# Patterns that indicate VALUABLE (cognitive) insights
VALUABLE_PATTERNS = [
    # Decisions and rationale
    r"(?i)(chose|decided|prefer|because|instead of|rather than)",
    r"(?i)(better|worse|tradeoff|balance)",
    # Domain knowledge
    r"(?i)(health|damage|physics|balance|gameplay)",  # Game
    r"(?i)(audience|campaign|brand|conversion)",      # Marketing
    r"(?i)(architecture|pattern|design|structure)",   # Engineering
    r"(?i)(user|customer|experience|feedback)",       # UX
    # Learning signals
    r"(?i)(learned|discovered|realized|found that)",
    r"(?i)(works better|fixed by|caused by|due to)",
    r"(?i)(should|shouldn't|must|avoid|prefer)",
    # Specific values with context
    r"(?i)(set|changed|adjusted|tuned)\s+\w+\s+to\s+\d+",
    r"(?i)\d+\s*(->|to)\s*\d+\s+(for|because|to)",
]

# Keywords that boost value
VALUE_BOOST_KEYWORDS = {
    "decision": 0.2,
    "rationale": 0.2,
    "preference": 0.15,
    "lesson": 0.2,
    "mistake": 0.15,
    "fixed": 0.1,
    "improved": 0.1,
    "because": 0.1,
    "tradeoff": 0.15,
    "balance": 0.1,
}

# Keywords that reduce value
VALUE_REDUCE_KEYWORDS = {
    "timeout": -0.1,
    "retry": -0.05,
    "sequence": -0.1,
    "pattern detected": -0.1,
    "tool used": -0.15,
    "file modified": -0.1,
}


class InsightScorer:
    """Score insights for promotion decisions."""

    def __init__(self):
        self._seen_content: Set[str] = set()
        self._seen_order: List[str] = []
        self._max_seen = 5000
        self._domain_keywords: Dict[str, List[str]] = {
            "game_dev": ["health", "damage", "physics", "player", "enemy", "level", "spawn", "collision"],
            "marketing": ["audience", "campaign", "brand", "conversion", "engagement", "funnel"],
            "vibecoding": ["component", "hook", "state", "render", "api", "route", "deploy"],
            "biz-ops": ["revenue", "cost", "margin", "growth", "churn", "retention"],
            "market-intel": ["competitor", "market", "gap", "audience", "trend", "sentiment", "opportunity"],
            "bench_core": ["benchmark", "method", "acceptance", "confidence", "outcome", "coverage"],
            "bench-core": ["benchmark", "method", "acceptance", "confidence", "outcome", "coverage"],
            "spark-core": ["tool", "workflow", "debug", "failure", "fix", "preference", "pattern"],
            "moltbook": ["book", "author", "chapter", "reader", "publish", "summary", "narrative"],
        }

    def _canonical_chip_id(self, chip_id: Optional[str]) -> str:
        return str(chip_id or "").strip().lower().replace("_", "-")

    def _keywords_from_context(self, context: Optional[Dict]) -> List[str]:
        if not isinstance(context, dict):
            return []
        out: List[str] = []

        chip_domains = context.get("chip_domains") or []
        if isinstance(chip_domains, list):
            for domain in chip_domains:
                for token in re.findall(r"[a-z]{3,}", str(domain).lower()):
                    out.append(token)

        trigger_patterns = context.get("trigger_patterns") or []
        if isinstance(trigger_patterns, list):
            for pattern in trigger_patterns[:24]:
                for token in re.findall(r"[a-z]{4,}", str(pattern).lower()):
                    out.append(token)

        # Keep unique order.
        deduped: List[str] = []
        seen = set()
        for token in out:
            if token in seen:
                continue
            seen.add(token)
            deduped.append(token)
        return deduped[:40]

    def score(self, insight: Dict, context: Optional[Dict] = None) -> InsightScore:
        """Score an insight across all dimensions."""
        content = insight.get("content", "")
        captured_data = insight.get("captured_data", {})

        score = InsightScore(
            cognitive_value=self._score_cognitive_value(content, captured_data),
            uniqueness=self._score_uniqueness(content),
            actionability=self._score_actionability(content),
            transferability=self._score_transferability(content, captured_data),
            domain_relevance=self._score_domain_relevance(content, insight.get("chip_id"), context),
        )
        # Outcome linkage is scored separately when outcomes are detected.
        score.outcome_linkage = insight.get("outcome_score", 0.0)
        return score

    def _score_cognitive_value(self, content: str, captured_data: Dict) -> float:
        """Score how cognitively valuable (human-useful) the insight is."""
        score = 0.5  # Start neutral.

        for pattern in PRIMITIVE_PATTERNS:
            if re.search(pattern, content):
                score -= 0.2

        for pattern in VALUABLE_PATTERNS:
            if re.search(pattern, content):
                score += 0.15

        content_lower = content.lower()
        for keyword, boost in VALUE_BOOST_KEYWORDS.items():
            if keyword in content_lower:
                score += boost

        for keyword, reduction in VALUE_REDUCE_KEYWORDS.items():
            if keyword in content_lower:
                score += reduction  # reduction is negative

        if captured_data.get("change_summary"):
            change = captured_data["change_summary"]
            if re.search(r"numbers?:\s*\[", change):
                score += 0.1
            if "added:" in change:
                score += 0.1

        return max(0.0, min(1.0, score))

    def _score_uniqueness(self, content: str) -> float:
        """Score how unique/new this insight is."""
        normalized = content.lower().strip()
        if not normalized:
            return 0.1

        if normalized in self._seen_content:
            return 0.1  # Duplicate.

        for seen in self._seen_content:
            if self._similarity(normalized, seen) > 0.8:
                return 0.3  # Very similar.

        self._seen_content.add(normalized)
        self._seen_order.append(normalized)
        if len(self._seen_order) > self._max_seen:
            oldest = self._seen_order.pop(0)
            self._seen_content.discard(oldest)
        return 0.9

    def _similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _score_actionability(self, content: str) -> float:
        """Score how actionable the insight is."""
        score = 0.3  # Base.
        actionable_patterns = [
            (r"(?i)(should|must|always|never|avoid|prefer)", 0.3),
            (r"(?i)(next time|in future|going forward)", 0.2),
            (r"(?i)(fix|solution|workaround|approach)", 0.2),
            (r"(?i)(set|use|configure|enable|disable)\s+\w+\s+to", 0.2),
        ]
        for pattern, boost in actionable_patterns:
            if re.search(pattern, content):
                score += boost
        return min(1.0, score)

    def _score_transferability(self, content: str, captured_data: Dict) -> float:
        """Score how transferable to other projects."""
        score = 0.3  # Base.
        universal_patterns = [
            (r"(?i)(always|never|best practice|anti-pattern)", 0.3),
            (r"(?i)(validate|test|check|verify) (input|output|data)", 0.2),
            (r"(?i)(error handling|edge case|boundary)", 0.2),
        ]
        for pattern, boost in universal_patterns:
            if re.search(pattern, content):
                score += boost

        specific_patterns = [
            (r"(?i)(this project|here we|in this codebase)", -0.2),
            (r"(?i)(file|path|directory)\s+['\"]?[A-Za-z0-9_/\\]+", -0.1),
        ]
        for pattern, reduction in specific_patterns:
            if re.search(pattern, content):
                score += reduction

        return max(0.0, min(1.0, score))

    def _score_domain_relevance(self, content: str, chip_id: Optional[str], context: Optional[Dict]) -> float:
        """Score relevance to the active domain."""
        if not chip_id:
            return 0.5

        canonical_id = self._canonical_chip_id(chip_id)
        keywords = list(self._domain_keywords.get(chip_id, []))
        keywords.extend(self._domain_keywords.get(canonical_id, []))
        keywords.extend(self._keywords_from_context(context))
        # De-dupe keywords.
        keywords = list(dict.fromkeys([kw for kw in keywords if kw]))
        if not keywords:
            return 0.5

        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)

        if matches == 0:
            return 0.2
        if matches == 1:
            return 0.6
        if matches == 2:
            return 0.8
        return 1.0

    def score_batch(self, insights: List[Dict], context: Optional[Dict] = None) -> List[tuple]:
        """Score a batch of insights."""
        results = []
        for insight in insights:
            score = self.score(insight, context)
            results.append((insight, score))
        return results

    def filter_valuable(self, insights: List[Dict], threshold: float = 0.5) -> List[tuple]:
        """Filter to only valuable insights."""
        scored = self.score_batch(insights)
        return [(insight, score) for insight, score in scored if score.total >= threshold]


# Singleton scorer
_scorer: Optional[InsightScorer] = None


def get_scorer() -> InsightScorer:
    """Get singleton scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = InsightScorer()
    return _scorer


def score_insight(insight: Dict, context: Optional[Dict] = None) -> InsightScore:
    """Score a single insight (convenience function)."""
    return get_scorer().score(insight, context)
