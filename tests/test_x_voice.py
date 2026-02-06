#!/usr/bin/env python3
"""Tests for X Voice personality engine and humanizer."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is on path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# XHumanizer tests
# ---------------------------------------------------------------------------


class TestXHumanizer:
    """Tests for the humanization engine."""

    def _get_humanizer(self):
        from lib.x_humanizer import XHumanizer
        return XHumanizer()

    def test_removes_furthermore(self):
        h = self._get_humanizer()
        result = h.humanize_tweet("Furthermore, this is interesting.")
        assert "Furthermore" not in result
        assert "interesting" in result

    def test_removes_additionally(self):
        h = self._get_humanizer()
        result = h.humanize_tweet("Additionally, we should consider this.")
        assert "Additionally" not in result
        assert "Also" in result

    def test_removes_its_important_to_note(self):
        h = self._get_humanizer()
        result = h.humanize_tweet(
            "It's important to note that AI is evolving fast."
        )
        assert "important to note" not in result.lower()
        assert "AI" in result

    def test_removes_sycophantic_opener(self):
        h = self._get_humanizer()
        result = h.humanize_tweet(
            "That's a great question! Here's what I think."
        )
        assert "great question" not in result.lower()
        assert "think" in result

    def test_adds_contractions(self):
        h = self._get_humanizer()
        result = h.humanize_tweet("I would not recommend this. It is too slow.")
        assert "wouldn't" in result or "I would not" not in result
        assert "it's" in result.lower() or "It is" not in result

    def test_cleans_whitespace(self):
        h = self._get_humanizer()
        result = h.humanize_tweet("Too  many   spaces  here.")
        assert "  " not in result

    def test_score_humanness_high_for_natural(self):
        h = self._get_humanizer()
        natural = "I've been thinking about this. It's wild how fast things move. What do you think?"
        score = h.score_humanness(natural)
        assert score >= 0.7

    def test_score_humanness_low_for_robotic(self):
        h = self._get_humanizer()
        robotic = (
            "It is important to note that this represents a significant advancement. "
            "Furthermore, the implications are substantial. Additionally, one should consider "
            "the broader context. In conclusion, this is noteworthy."
        )
        score = h.score_humanness(robotic)
        assert score < 0.6

    def test_humanize_preserves_meaning(self):
        h = self._get_humanizer()
        original = "Furthermore, Python 3.12 is significantly faster."
        result = h.humanize_tweet(original)
        assert "Python" in result
        assert "3.12" in result
        assert "faster" in result

    def test_personality_quirk_respects_280(self):
        h = self._get_humanizer()
        text = "A" * 275
        result = h.add_personality_quirk(text, "Short quirk.")
        assert len(result) <= 280


# ---------------------------------------------------------------------------
# XVoice tests
# ---------------------------------------------------------------------------


class TestXVoice:
    """Tests for the X voice engine."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        """Set up temporary state directory."""
        self.tmp_dir = tmp_path / "x_voice"
        self.tmp_dir.mkdir()
        monkeypatch.setattr(
            "lib.x_voice.X_VOICE_DIR", self.tmp_dir
        )
        monkeypatch.setattr(
            "lib.x_voice.PROFILES_FILE", self.tmp_dir / "profiles.json"
        )

    def _get_voice(self):
        from lib.x_voice import XVoice
        return XVoice()

    def test_select_tone_defaults(self):
        xv = self._get_voice()
        assert xv.select_tone("reply") == "conversational"
        assert xv.select_tone("quote_tweet") == "witty"
        assert xv.select_tone("original_post") == "technical"
        assert xv.select_tone("hot_take") == "provocative"

    def test_select_tone_adapts_to_warm_user(self):
        xv = self._get_voice()
        handle = "testuser"
        # Manually warm up the user
        profile = xv._get_or_create_profile(handle)
        profile.warmth = "hot"
        profile.successful_tones = {"witty": 5, "technical": 1}
        xv._save_profiles()

        tone = xv.select_tone("reply", user_handle=handle)
        assert tone == "witty"  # Learned preference

    def test_render_tweet_respects_280_chars(self):
        xv = self._get_voice()
        long_text = "This is a very long tweet. " * 20
        result = xv.render_tweet(long_text, humanize=False)
        assert len(result) <= 280

    def test_render_tweet_humanizes_by_default(self):
        xv = self._get_voice()
        robotic = "Furthermore, it is important to note that this works."
        result = xv.render_tweet(robotic)
        assert "Furthermore" not in result
        assert "important to note" not in result.lower()

    def test_render_thread_creates_multiple_tweets(self):
        xv = self._get_voice()
        long_content = ". ".join(
            [f"This is sentence number {i} about AI intelligence" for i in range(20)]
        )
        thread = xv.render_thread(long_content, humanize=False)
        assert len(thread) > 1
        for tweet in thread:
            assert len(tweet) <= 280

    def test_render_thread_max_25_tweets(self):
        xv = self._get_voice()
        very_long = ". ".join([f"Sentence {i}" for i in range(200)])
        thread = xv.render_thread(very_long, humanize=False)
        assert len(thread) <= 25

    def test_should_engage_filters_political(self):
        xv = self._get_voice()
        engage, reason = xv.should_engage(
            "Hot take on political controversy today"
        )
        assert not engage
        assert "Sitting out" in reason

    def test_should_engage_allows_technical(self):
        xv = self._get_voice()
        engage, reason = xv.should_engage(
            "How do you handle genuine technical questions about coding?"
        )
        assert engage

    def test_should_engage_allows_building_in_public(self):
        xv = self._get_voice()
        engage, reason = xv.should_engage(
            "Just shipped a new feature building in public with AI tools"
        )
        assert engage

    def test_warmth_transitions(self):
        xv = self._get_voice()
        handle = "newuser"

        assert xv.get_user_warmth(handle) == "cold"

        xv.update_warmth(handle, "we_reply")
        assert xv.get_user_warmth(handle) == "cool"

        xv.update_warmth(handle, "reply_received")
        assert xv.get_user_warmth(handle) == "warm"

        xv.update_warmth(handle, "multi_turn_convo")
        assert xv.get_user_warmth(handle) == "hot"

        xv.update_warmth(handle, "collaboration")
        assert xv.get_user_warmth(handle) == "ally"

    def test_warmth_persists(self):
        from lib.x_voice import XVoice

        xv1 = self._get_voice()
        xv1.update_warmth("persistuser", "we_reply")
        xv1._save_profiles()

        xv2 = self._get_voice()
        assert xv2.get_user_warmth("persistuser") == "cool"

    def test_record_interaction_tracks_success(self):
        xv = self._get_voice()
        xv.record_interaction("testuser", "witty", success=True)
        xv.record_interaction("testuser", "witty", success=True)
        xv.record_interaction("testuser", "technical", success=True)

        profile = xv._get_or_create_profile("testuser")
        assert profile.successful_tones["witty"] == 2
        assert profile.successful_tones["technical"] == 1
        assert profile.interaction_count == 3

    def test_smart_truncate_at_word_boundary(self):
        xv = self._get_voice()
        text = "This is a sentence that is longer than the limit we set"
        result = xv._smart_truncate(text, 30)
        assert len(result) <= 30
        assert result.endswith("\u2026")  # ellipsis
        assert " " not in result[-2:]  # Doesn't cut mid-word

    def test_get_stats(self):
        xv = self._get_voice()
        xv.record_interaction("user1", "witty")
        xv.record_interaction("user2", "technical")
        stats = xv.get_stats()
        assert stats["tracked_users"] == 2
        assert stats["total_interactions"] == 2


# ---------------------------------------------------------------------------
# SparkVoice personality snippet tests
# ---------------------------------------------------------------------------


class TestPersonalitySnippet:
    """Tests for the get_personality_snippet method on SparkVoice."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        self.tmp_dir = tmp_path / "spark"
        self.tmp_dir.mkdir()
        monkeypatch.setattr("lib.spark_voice.SPARK_DIR", self.tmp_dir)
        monkeypatch.setattr(
            "lib.spark_voice.VOICE_FILE", self.tmp_dir / "voice.json"
        )

    def _get_voice(self):
        from lib.spark_voice import SparkVoice
        return SparkVoice()

    def test_returns_none_when_empty(self):
        v = self._get_voice()
        assert v.get_personality_snippet() is None

    def test_returns_topic_opinion(self):
        v = self._get_voice()
        v.form_opinion("code quality", "clean, readable code", "it reduces bugs")
        snippet = v.get_personality_snippet("code quality")
        assert snippet is not None
        assert "clean" in snippet

    def test_returns_strongest_opinion_as_fallback(self):
        v = self._get_voice()
        v.form_opinion("testing", "always test", "tests are docs", strength=0.9)
        snippet = v.get_personality_snippet("unrelated topic")
        assert snippet is not None
        assert "test" in snippet.lower()

    def test_returns_growth_as_last_fallback(self):
        v = self._get_voice()
        v.record_growth(
            before="ignore tests",
            after="write tests first",
            trigger="a bug",
            impact="fewer bugs"
        )
        snippet = v.get_personality_snippet()
        assert snippet is not None
        assert "write tests first" in snippet


# ---------------------------------------------------------------------------
# User resonance calculation tests
# ---------------------------------------------------------------------------


class TestUserResonance:
    """Tests for per-user resonance calculation."""

    def test_zero_interactions(self):
        from lib.resonance import calculate_user_resonance
        score = calculate_user_resonance("newuser")
        assert score == 0.0

    def test_high_interaction_scores_high(self):
        from lib.resonance import calculate_user_resonance
        score = calculate_user_resonance(
            "activeuser",
            interaction_count=30,
            they_initiated_count=15,
            successful_tones=8,
            topics_shared=6,
        )
        assert score > 70

    def test_one_sided_scores_lower(self):
        from lib.resonance import calculate_user_resonance
        # All interactions initiated by us, none by them
        score = calculate_user_resonance(
            "onesided",
            interaction_count=20,
            they_initiated_count=0,
            successful_tones=5,
            topics_shared=3,
        )
        # Same interactions but with reciprocity
        score_reciprocal = calculate_user_resonance(
            "reciprocal",
            interaction_count=20,
            they_initiated_count=10,
            successful_tones=5,
            topics_shared=3,
        )
        assert score_reciprocal > score

    def test_score_capped_at_100(self):
        from lib.resonance import calculate_user_resonance
        score = calculate_user_resonance(
            "maxuser",
            interaction_count=1000,
            they_initiated_count=500,
            successful_tones=100,
            topics_shared=50,
        )
        assert score <= 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
