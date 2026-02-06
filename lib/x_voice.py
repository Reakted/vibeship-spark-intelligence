#!/usr/bin/env python3
"""
X Voice - Spark's personality engine for X/Twitter.

Handles:
- Tone selection (witty / technical / conversational / provocative)
- Per-user warmth tracking and adaptation
- Tweet/thread rendering within character limits
- Cultural awareness (engage / sit out / be bold)
- Humanization pipeline integration

"Not robotic. Not try-hard. Genuinely interesting."
"""

import json
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.spark_voice import get_spark_voice, SparkVoice
from lib.x_humanizer import get_humanizer, XHumanizer

# State directory
X_VOICE_DIR = Path.home() / ".spark" / "x_voice"
PROFILES_FILE = X_VOICE_DIR / "profiles.json"

# Config shipped with repo
_CONFIG_PATH = Path(__file__).parent / "x_voice_config.json"


def _load_config() -> Dict:
    """Load the static X voice config."""
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


CONFIG = _load_config()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class XVoiceProfile:
    """Settings for a specific tone style."""

    style: str
    tone_markers: List[str]
    avoid_markers: List[str]
    max_length: int = 280
    emoji_frequency: float = 0.1
    hashtag_strategy: str = "none"  # none | minimal | strategic
    thread_style: str = "hook-value-cta"


# Pre-built profiles
TONE_PROFILES: Dict[str, XVoiceProfile] = {
    "witty": XVoiceProfile(
        style="witty",
        tone_markers=[
            "ironic observation",
            "unexpected connection",
            "self-deprecation",
            "playful challenge",
        ],
        avoid_markers=[
            "corporate jargon",
            "hedge words",
            "sycophantic openers",
        ],
        emoji_frequency=0.15,
        hashtag_strategy="none",
    ),
    "technical": XVoiceProfile(
        style="technical",
        tone_markers=[
            "precise language",
            "concrete examples",
            "data references",
            "clear reasoning",
        ],
        avoid_markers=[
            "vague claims",
            "hype words",
            "unnecessary emoji",
        ],
        emoji_frequency=0.0,
        hashtag_strategy="minimal",
    ),
    "conversational": XVoiceProfile(
        style="conversational",
        tone_markers=[
            "casual tone",
            "contractions",
            "direct address",
            "natural flow",
        ],
        avoid_markers=[
            "formal language",
            "academic tone",
            "lengthy explanations",
        ],
        emoji_frequency=0.1,
        hashtag_strategy="none",
    ),
    "provocative": XVoiceProfile(
        style="provocative",
        tone_markers=[
            "strong opinion",
            "challenge assumption",
            "contrarian take",
            "bold claim with reasoning",
        ],
        avoid_markers=[
            "hedging",
            "both-sides-ing",
            "qualifying everything",
        ],
        emoji_frequency=0.0,
        hashtag_strategy="none",
    ),
}


@dataclass
class UserToneProfile:
    """Per-user relationship tracking for X conversations."""

    user_handle: str
    warmth: str = "cold"  # cold | cool | warm | hot | ally
    preferred_tone: str = "conversational"
    interaction_count: int = 0
    successful_tones: Dict[str, int] = field(default_factory=dict)
    topics_of_interest: List[str] = field(default_factory=list)
    last_interaction: str = ""
    they_initiated_count: int = 0
    we_initiated_count: int = 0


# Warmth state machine transitions
WARMTH_TRANSITIONS = {
    "cold": {
        "reply_received": "cool",
        "mutual_like": "cool",
        "we_reply": "cool",
    },
    "cool": {
        "reply_received": "warm",
        "they_mention_us": "warm",
        "multi_turn_convo": "warm",
    },
    "warm": {
        "multi_turn_convo": "hot",
        "they_share_our_content": "hot",
        "sustained_engagement": "hot",
    },
    "hot": {
        "collaboration": "ally",
        "sustained_engagement": "ally",
    },
    "ally": {},  # Terminal state
}


# ---------------------------------------------------------------------------
# Core X Voice engine
# ---------------------------------------------------------------------------


class XVoice:
    """Spark's X/Twitter personality engine.

    Selects tone, adapts for user relationships, renders tweets,
    and decides when to engage based on cultural awareness.
    """

    TWEET_MAX = 280
    THREAD_MAX_TWEETS = 25

    def __init__(self):
        self.voice: SparkVoice = get_spark_voice()
        self.humanizer: XHumanizer = get_humanizer()
        self.config: Dict = CONFIG
        self.user_profiles: Dict[str, UserToneProfile] = {}
        self._load_profiles()

    # ------ Persistence ------

    def _load_profiles(self):
        """Load per-user tone profiles from disk."""
        if PROFILES_FILE.exists():
            try:
                raw = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
                for handle, data in raw.items():
                    self.user_profiles[handle] = UserToneProfile(**data)
            except Exception:
                pass

    def _save_profiles(self):
        """Persist per-user tone profiles."""
        X_VOICE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {h: asdict(p) for h, p in self.user_profiles.items()}
        PROFILES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ------ Tone Selection ------

    def select_tone(
        self,
        context_type: str = "reply",
        user_handle: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> str:
        """Select the best tone for this context.

        Args:
            context_type: reply | quote_tweet | original_post | thread | hot_take
            user_handle: Who we're talking to (if any)
            topic: What the conversation is about

        Returns:
            One of: witty, technical, conversational, provocative
        """
        # Start with default for this context type
        defaults = self.config.get("tone_defaults", {})
        tone = defaults.get(context_type, "conversational")

        # Adapt based on user relationship
        if user_handle:
            profile = self._get_or_create_profile(user_handle)

            # If we know what works with this user, prefer that
            if profile.successful_tones:
                best_tone = max(
                    profile.successful_tones, key=profile.successful_tones.get
                )
                if profile.successful_tones[best_tone] >= 2:
                    tone = best_tone

            # Warmth affects formality
            warmth_config = self.config.get("warmth_levels", {}).get(
                profile.warmth, {}
            )
            if warmth_config.get("formality", 0.5) < 0.2:
                # Very informal = lean witty/conversational
                if tone == "technical":
                    tone = "conversational"

        # Topic override: technical topics favor technical tone
        if topic:
            bold_topics = self.config.get("cultural_rules", {}).get("be_bold_on", [])
            for bold_topic in bold_topics:
                if bold_topic.lower() in topic.lower():
                    if tone == "conversational":
                        tone = "provocative"
                    break

        return tone

    def get_tone_profile(self, tone: str) -> XVoiceProfile:
        """Get the full profile for a tone."""
        return TONE_PROFILES.get(tone, TONE_PROFILES["conversational"])

    # ------ User Adaptation ------

    def _get_or_create_profile(self, user_handle: str) -> UserToneProfile:
        """Get or create a user tone profile."""
        handle = user_handle.lstrip("@").lower()
        if handle not in self.user_profiles:
            self.user_profiles[handle] = UserToneProfile(user_handle=handle)
        return self.user_profiles[handle]

    def get_user_warmth(self, user_handle: str) -> str:
        """Get current warmth level with a user."""
        return self._get_or_create_profile(user_handle).warmth

    def update_warmth(self, user_handle: str, event: str):
        """Update relationship warmth based on interaction event.

        Events: reply_received, mutual_like, we_reply, they_mention_us,
                multi_turn_convo, they_share_our_content,
                sustained_engagement, collaboration
        """
        profile = self._get_or_create_profile(user_handle)
        transitions = WARMTH_TRANSITIONS.get(profile.warmth, {})
        new_warmth = transitions.get(event)
        if new_warmth:
            profile.warmth = new_warmth
        self._save_profiles()

    def record_interaction(
        self,
        user_handle: str,
        tone_used: str,
        they_initiated: bool = False,
        success: bool = True,
    ):
        """Record an interaction for learning."""
        profile = self._get_or_create_profile(user_handle)
        profile.interaction_count += 1
        profile.last_interaction = datetime.now().isoformat()

        if they_initiated:
            profile.they_initiated_count += 1
        else:
            profile.we_initiated_count += 1

        if success:
            profile.successful_tones[tone_used] = (
                profile.successful_tones.get(tone_used, 0) + 1
            )

        self._save_profiles()

    # ------ Tweet Rendering ------

    def render_tweet(
        self,
        content: str,
        style: str = "auto",
        reply_to_handle: Optional[str] = None,
        humanize: bool = True,
    ) -> str:
        """Render content into a tweet, respecting 280 char limit.

        Args:
            content: Raw content to tweet
            style: Tone style or "auto" for auto-select
            reply_to_handle: If replying, who to
            humanize: Whether to run humanization pipeline

        Returns:
            Tweet text within 280 characters
        """
        if style == "auto":
            context_type = "reply" if reply_to_handle else "original_post"
            style = self.select_tone(context_type, reply_to_handle)

        text = content

        # Humanize
        if humanize:
            text = self.humanizer.humanize_tweet(text)

        # Truncate to fit (leave room for ellipsis if needed)
        if len(text) > self.TWEET_MAX:
            text = self._smart_truncate(text, self.TWEET_MAX)

        return text

    def render_thread(
        self,
        content: str,
        style: str = "auto",
        humanize: bool = True,
    ) -> List[str]:
        """Render long content into a thread.

        Follows hook-value-CTA structure:
        - Tweet 1: Hook (problem or promise)
        - Tweets 2-N: Value (the actual content)
        - Last tweet: Takeaway + CTA

        Args:
            content: Long-form content to thread-ify
            style: Tone style
            humanize: Run humanization

        Returns:
            List of tweet strings (each <= 280 chars)
        """
        if style == "auto":
            style = self.select_tone("thread")

        if humanize:
            content = self.humanizer.humanize_tweet(content)

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", content)
        if not sentences:
            return [content[: self.TWEET_MAX]]

        tweets: List[str] = []
        current = ""

        for sentence in sentences:
            # Check if adding this sentence exceeds limit
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= self.TWEET_MAX - 5:  # Leave room for numbering
                current = candidate
            else:
                if current:
                    tweets.append(current)
                current = sentence

        if current:
            tweets.append(current)

        # Enforce thread max
        if len(tweets) > self.THREAD_MAX_TWEETS:
            tweets = tweets[: self.THREAD_MAX_TWEETS]

        return tweets

    def _smart_truncate(self, text: str, max_len: int) -> str:
        """Truncate at a word boundary, adding ellipsis."""
        if len(text) <= max_len:
            return text
        # Cut at word boundary
        cut = text[: max_len - 1].rsplit(" ", 1)[0]
        return cut.rstrip(".,;:!? ") + "\u2026"  # ellipsis character

    # ------ Cultural Awareness ------

    def should_engage(
        self,
        tweet_text: str,
        author_handle: Optional[str] = None,
        thread_context: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Decide whether to engage with a tweet.

        Returns:
            (should_engage: bool, reason: str)
        """
        text_lower = tweet_text.lower()
        context = f"{tweet_text} {thread_context or ''}".lower()
        rules = self.config.get("cultural_rules", {})

        # Check never-engage topics
        for topic in rules.get("never_engage", []):
            topic_words = topic.lower().split()
            if all(w in context for w in topic_words):
                return False, f"Sitting out: '{topic}'"

        # Check sit-out signals
        for signal in rules.get("sit_out_signals", []):
            signal_lower = signal.lower()
            # These are descriptive - check the ones we can detect
            if "no genuine value" in signal_lower:
                # Can't detect this automatically, skip
                continue

        # Check always-engage topics
        for topic in rules.get("always_engage", []):
            topic_words = topic.lower().split()
            if any(w in context for w in topic_words):
                return True, f"Engaging: matches '{topic}'"

        # Check be-bold topics
        for topic in rules.get("be_bold_on", []):
            topic_words = topic.lower().split()
            if any(w in context for w in topic_words):
                return True, f"Being bold: topic is '{topic}'"

        # Default: engage if it seems like a conversation
        if "?" in tweet_text:
            return True, "Engaging: contains a question"
        if author_handle:
            profile = self._get_or_create_profile(author_handle)
            if profile.warmth in ("warm", "hot", "ally"):
                return True, f"Engaging: warm relationship ({profile.warmth})"

        # Default: mild engagement for neutral content
        return True, "Engaging: no reason to sit out"

    # ------ Personality Integration ------

    def get_personality_context(self, topic: Optional[str] = None) -> Dict:
        """Get personality context for content generation.

        Returns a dict with opinion, growth, and identity info
        that can inform tone and content.
        """
        result: Dict = {
            "identity": CONFIG.get("identity", {}),
            "principles": CONFIG.get("identity", {}).get(
                "communication_principles", []
            ),
        }

        # Pull relevant opinion from SparkVoice
        snippet = self.voice.get_personality_snippet(topic)
        if snippet:
            result["opinion_snippet"] = snippet

        # Pull recent growth
        growth = self.voice.get_recent_growth(1)
        if growth:
            g = growth[0]
            result["recent_growth"] = f"I used to {g.before}. Now I {g.after}."

        return result

    def get_stats(self) -> Dict:
        """Get X Voice statistics."""
        warmth_dist: Dict[str, int] = {}
        for p in self.user_profiles.values():
            warmth_dist[p.warmth] = warmth_dist.get(p.warmth, 0) + 1

        return {
            "tracked_users": len(self.user_profiles),
            "warmth_distribution": warmth_dist,
            "total_interactions": sum(
                p.interaction_count for p in self.user_profiles.values()
            ),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_x_voice: Optional[XVoice] = None


def get_x_voice() -> XVoice:
    """Get the singleton XVoice instance."""
    global _x_voice
    if _x_voice is None:
        _x_voice = XVoice()
    return _x_voice
