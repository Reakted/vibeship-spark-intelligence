"""Tests for lib/distillation_transformer.py — advisory quality transformer."""
from __future__ import annotations

import pytest

from lib.distillation_transformer import (
    AdvisoryQuality,
    extract_structure,
    should_suppress,
    transform_for_advisory,
    _detect_domain,
    _score_actionability,
    _score_novelty,
    _score_reasoning,
    _score_specificity,
    _score_outcome_linked,
    _compute_unified_score,
    _compose_advisory_text,
    _DIM_WEIGHTS,
)


# ---------------------------------------------------------------------------
# AdvisoryQuality dataclass
# ---------------------------------------------------------------------------

class TestAdvisoryQualityDefaults:
    def test_all_dims_default_zero(self):
        aq = AdvisoryQuality()
        for dim in ("actionability", "novelty", "reasoning", "specificity",
                    "outcome_linked", "unified_score"):
            assert getattr(aq, dim) == 0.0

    def test_domain_defaults_general(self):
        assert AdvisoryQuality().domain == "general"

    def test_suppressed_defaults_false(self):
        assert AdvisoryQuality().suppressed is False

    def test_suppression_reason_empty(self):
        assert AdvisoryQuality().suppression_reason == ""

    def test_advisory_text_empty(self):
        assert AdvisoryQuality().advisory_text == ""


class TestAdvisoryQualityToDict:
    def test_has_all_required_keys(self):
        aq = AdvisoryQuality(actionability=0.5)
        d = aq.to_dict()
        for key in ("actionability", "novelty", "reasoning", "specificity",
                    "outcome_linked", "unified_score", "structure", "domain",
                    "suppressed", "suppression_reason"):
            assert key in d

    def test_values_rounded_to_3dp(self):
        aq = AdvisoryQuality(actionability=0.123456)
        d = aq.to_dict()
        assert d["actionability"] == 0.123

    def test_advisory_text_omitted_when_empty(self):
        aq = AdvisoryQuality()
        d = aq.to_dict()
        assert "advisory_text" not in d

    def test_advisory_text_included_when_present(self):
        aq = AdvisoryQuality(advisory_text="Use always validate")
        d = aq.to_dict()
        assert "advisory_text" in d
        assert d["advisory_text"] == "Use always validate"


class TestAdvisoryQualityFromDict:
    def test_round_trip(self):
        aq = AdvisoryQuality(
            actionability=0.8, novelty=0.6, reasoning=0.7,
            specificity=0.5, outcome_linked=0.4, unified_score=0.65,
            domain="code", suppressed=False,
        )
        aq2 = AdvisoryQuality.from_dict(aq.to_dict())
        assert abs(aq2.actionability - 0.8) < 0.01
        assert aq2.domain == "code"

    def test_empty_dict_returns_defaults(self):
        aq = AdvisoryQuality.from_dict({})
        assert aq.actionability == 0.0
        assert aq.domain == "general"

    def test_none_returns_defaults(self):
        aq = AdvisoryQuality.from_dict(None)  # type: ignore[arg-type]
        assert aq.actionability == 0.0

    def test_suppressed_field_restored(self):
        d = {"suppressed": True, "suppression_reason": "noise_pattern"}
        aq = AdvisoryQuality.from_dict(d)
        assert aq.suppressed is True
        assert aq.suppression_reason == "noise_pattern"


# ---------------------------------------------------------------------------
# _score_actionability
# ---------------------------------------------------------------------------

class TestScoreActionability:
    def test_action_verb_gives_one(self):
        assert _score_actionability("Always validate user input") == 1.0

    def test_avoid_verb_gives_one(self):
        assert _score_actionability("Avoid using global state") == 1.0

    def test_use_verb_gives_one(self):
        assert _score_actionability("Use TypeScript for this") == 1.0

    def test_soft_verb_gives_half(self):
        assert _score_actionability("Consider the tradeoffs") == 0.5

    def test_no_verbs_gives_zero(self):
        assert _score_actionability("This is a generic observation") == 0.0

    def test_numeric_with_metric_gives_half(self):
        # numeric (2+ digits) + metric word → 0.5
        result = _score_actionability("engagement avg was 250 this week")
        assert result == 0.5


# ---------------------------------------------------------------------------
# _score_novelty
# ---------------------------------------------------------------------------

class TestScoreNovelty:
    def test_two_quality_signals_gives_one(self):
        # "because" + "prefer" → 2 signals → 1.0
        assert _score_novelty("Use this because it's better, prefer TypeScript") == 1.0

    def test_one_quality_signal_gives_half(self):
        assert _score_novelty("Use this because it works") == 0.5

    def test_no_signals_gives_zero(self):
        assert _score_novelty("this is a simple statement") == 0.0

    def test_numeric_with_signal_gives_one(self):
        # has_numeric (3+ digits) + 1 signal → 1.0
        result = _score_novelty("1200 avg likes, because of good hook strategy")
        assert result == 1.0


# ---------------------------------------------------------------------------
# _score_reasoning
# ---------------------------------------------------------------------------

class TestScoreReasoning:
    def test_because_gives_one(self):
        assert _score_reasoning("Use this because it reduces latency") == 1.0

    def test_since_gives_one(self):
        assert _score_reasoning("Since the queue is full, batch it") == 1.0

    def test_soft_keyword_gives_half(self):
        assert _score_reasoning("This helps prevent bugs in production") == 0.5

    def test_no_reasoning_gives_zero(self):
        assert _score_reasoning("add a button here") == 0.0

    def test_data_comparison_gives_half(self):
        result = _score_reasoning("1200 avg outperforms 800 control")
        assert result == 0.5


# ---------------------------------------------------------------------------
# _score_specificity
# ---------------------------------------------------------------------------

class TestScoreSpecificity:
    def test_file_extension_gives_one(self):
        assert _score_specificity("Edit the config.json file") == 1.0

    def test_path_gives_one(self):
        assert _score_specificity("Check /etc/spark/config") == 1.0

    def test_two_markers_gives_one(self):
        # "user" + "typescript"
        assert _score_specificity("The user prefers TypeScript over JavaScript") == 1.0

    def test_one_marker_gives_half(self):
        assert _score_specificity("This is about authentication") == 0.5

    def test_no_markers_gives_zero(self):
        assert _score_specificity("Do it better") == 0.0


# ---------------------------------------------------------------------------
# _score_outcome_linked
# ---------------------------------------------------------------------------

class TestScoreOutcomeLinked:
    def test_outcome_word_gives_one(self):
        assert _score_outcome_linked("This approach fixed the bug") == 1.0

    def test_soft_outcome_gives_half(self):
        assert _score_outcome_linked("It improves user retention") == 0.5

    def test_no_outcome_gives_zero(self):
        assert _score_outcome_linked("add a button") == 0.0

    def test_numeric_with_rate_gives_half(self):
        result = _score_outcome_linked("100% avg conversion rate")
        assert result == 0.5


# ---------------------------------------------------------------------------
# _compute_unified_score
# ---------------------------------------------------------------------------

class TestComputeUnifiedScore:
    def test_all_zero_gives_zero(self):
        dims = {d: 0.0 for d in _DIM_WEIGHTS}
        assert _compute_unified_score(dims) == 0.0

    def test_all_one_gives_one(self):
        dims = {d: 1.0 for d in _DIM_WEIGHTS}
        assert abs(_compute_unified_score(dims) - 1.0) < 1e-9

    def test_weights_sum_respected(self):
        # actionability=1 (weight=0.30), others=0
        dims = {"actionability": 1.0, "novelty": 0.0, "reasoning": 0.0,
                "specificity": 0.0, "outcome_linked": 0.0}
        result = _compute_unified_score(dims)
        assert abs(result - 0.30) < 1e-9

    def test_clamped_at_one(self):
        dims = {d: 2.0 for d in _DIM_WEIGHTS}  # overcapacity inputs
        assert _compute_unified_score(dims) == 1.0

    def test_missing_dims_default_zero(self):
        result = _compute_unified_score({})
        assert result == 0.0


# ---------------------------------------------------------------------------
# extract_structure
# ---------------------------------------------------------------------------

class TestExtractStructure:
    def test_returns_dict_with_four_keys(self):
        result = extract_structure("always use TypeScript")
        for key in ("condition", "action", "reasoning", "outcome"):
            assert key in result

    def test_short_text_returns_all_none(self):
        result = extract_structure("ok")
        assert all(v is None for v in result.values())

    def test_extracts_condition(self):
        result = extract_structure("When the queue is full: use batching")
        assert result["condition"] is not None

    def test_extracts_action(self):
        result = extract_structure("Always use TypeScript for large projects")
        assert result["action"] is not None

    def test_extracts_reasoning(self):
        result = extract_structure("Use memoization because it reduces calls")
        assert result["reasoning"] is not None

    def test_extracts_outcome(self):
        result = extract_structure("Use caching, which leads to faster responses")
        assert result["outcome"] is not None

    def test_empty_string_returns_none_values(self):
        result = extract_structure("")
        assert all(v is None for v in result.values())

    def test_extracted_values_capped_at_120(self):
        long_text = "Use always " + "x" * 200 + " in production"
        result = extract_structure(long_text)
        if result["action"] is not None:
            assert len(result["action"]) <= 120


# ---------------------------------------------------------------------------
# _detect_domain
# ---------------------------------------------------------------------------

class TestDetectDomain:
    def test_code_keywords_returns_code(self):
        assert _detect_domain("Use this TypeScript function") == "code"

    def test_system_keywords_returns_system(self):
        assert _detect_domain("The bridge_cycle runs every 30 seconds") == "system"

    def test_no_markers_returns_general(self):
        assert _detect_domain("Always be kind") == "general"

    def test_depth_in_source_returns_code(self):
        assert _detect_domain("some text", source="depth_session") == "code"


# ---------------------------------------------------------------------------
# should_suppress
# ---------------------------------------------------------------------------

class TestShouldSuppress:
    def _dims(self, **overrides):
        d = {"actionability": 1.0, "novelty": 0.5, "reasoning": 1.0,
             "specificity": 0.5, "outcome_linked": 0.5, "unified_score": 0.7}
        d.update(overrides)
        return d

    def _structure(self, **overrides):
        s = {"condition": None, "action": "validate inputs", "reasoning": None, "outcome": None}
        s.update(overrides)
        return s

    def test_good_advisory_not_suppressed(self):
        suppressed, reason = should_suppress(
            "Always validate user inputs because it prevents SQL injection.",
            self._dims(), self._structure()
        )
        assert suppressed is False

    def test_rt_prefix_suppressed(self):
        suppressed, reason = should_suppress(
            "RT @user: some tweet", self._dims(), self._structure()
        )
        assert suppressed is True
        assert "observation_prefix" in reason

    def test_depth_prefix_suppressed(self):
        suppressed, reason = should_suppress(
            "[DEPTH: 5] Here is analysis", self._dims(), self._structure()
        )
        assert suppressed is True

    def test_code_artifact_suppressed(self):
        # >60% non-alpha in first 100 chars triggers code_artifact suppression
        code_text = "0x1A;0xFF;{};[];1+2=3;4/5;6*7;8-9;!@#$%^&*();" * 3
        suppressed, reason = should_suppress(code_text, self._dims(unified_score=0.5), self._structure())
        assert suppressed is True
        assert reason == "code_artifact"

    def test_no_action_no_reasoning_suppressed(self):
        dims = self._dims(actionability=0.0, reasoning=0.0, outcome_linked=0.0,
                         novelty=0.0, unified_score=0.3)
        structure = self._structure(action=None)
        suppressed, reason = should_suppress("This is just an observation.", dims, structure)
        assert suppressed is True
        assert reason == "no_action_no_reasoning"

    def test_low_unified_score_suppressed(self):
        # actionability=0.5 bypasses no_action_no_reasoning; long text bypasses tautology
        long_text = "Consider this approach for your implementation scenario" + " ..." * 10
        dims = self._dims(actionability=0.5, novelty=0.0, reasoning=0.0,
                         specificity=0.0, outcome_linked=0.0, unified_score=0.05)
        suppressed, reason = should_suppress(long_text, dims, self._structure())
        assert suppressed is True
        assert "unified_score_too_low" in reason

    def test_returns_tuple(self):
        result = should_suppress("text", self._dims(), self._structure())
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# transform_for_advisory
# ---------------------------------------------------------------------------

class TestTransformForAdvisory:
    def test_empty_text_suppressed(self):
        aq = transform_for_advisory("")
        assert aq.suppressed is True
        assert aq.suppression_reason == "empty_text"

    def test_whitespace_text_suppressed(self):
        aq = transform_for_advisory("   ")
        assert aq.suppressed is True

    def test_returns_advisory_quality(self):
        aq = transform_for_advisory("Always validate user inputs because it prevents errors.")
        assert isinstance(aq, AdvisoryQuality)

    def test_actionable_text_not_suppressed(self):
        aq = transform_for_advisory(
            "Always use TypeScript because it catches type errors at compile time, "
            "which reduces runtime bugs in production."
        )
        assert aq.suppressed is False

    def test_actionability_scored(self):
        aq = transform_for_advisory("Always use index hints for large tables.")
        assert aq.actionability > 0.0

    def test_reasoning_scored_with_because(self):
        aq = transform_for_advisory("Use lazy loading because it reduces initial load time.")
        assert aq.reasoning > 0.0

    def test_domain_detected(self):
        aq = transform_for_advisory("Refactor the TypeScript function to use generics.")
        assert aq.domain == "code"

    def test_ralph_score_normalised_from_0_2(self):
        class FakeRalph:
            actionability = 2
            novelty = 1
            reasoning = 2
            specificity = 1
            outcome_linked = 0

        aq = transform_for_advisory("Some text", ralph_score=FakeRalph())
        # actionability=2/2=1.0
        assert aq.actionability == 1.0
        assert aq.novelty == 0.5

    def test_reliability_boosts_unified_score(self):
        base = transform_for_advisory("Always check edge cases.")
        boosted = transform_for_advisory("Always check edge cases.", reliability=0.9)
        assert boosted.unified_score >= base.unified_score

    def test_chip_quality_boosts_unified_score(self):
        base = transform_for_advisory("Always check edge cases.")
        boosted = transform_for_advisory("Always check edge cases.", chip_quality=0.9)
        assert boosted.unified_score >= base.unified_score

    def test_unified_score_clamped_at_one(self):
        aq = transform_for_advisory(
            "Always validate inputs because they improve quality.",
            reliability=1.0, chip_quality=1.0
        )
        assert aq.unified_score <= 1.0

    def test_structure_extracted(self):
        aq = transform_for_advisory(
            "When the queue is full: use batching because it reduces overhead."
        )
        assert isinstance(aq.structure, dict)
