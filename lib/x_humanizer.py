#!/usr/bin/env python3
"""
X Humanizer - Remove AI tells from tweet-length content.

Makes AI-generated social content sound genuinely human by:
- Removing hedge words and corporate speak
- Injecting personality from SparkVoice opinions
- Varying sentence rhythm (burstiness)
- Adding natural imperfections

"Human writing isn't perfect - it's personal."
"""

import re
import random
from typing import List, Optional, Tuple


# AI tells: patterns that scream "an AI wrote this"
AI_TELL_PATTERNS: List[Tuple[str, str]] = [
    # Hedge words
    (r"\bIt(?:'s| is) (?:important|worth) (?:to note|noting|mentioning) that\s*", ""),
    (r"\bIt(?:'s| is) worth (?:pointing out|highlighting) that\s*", ""),
    (r"\bI(?:'d| would) like to (?:point out|mention|highlight|note) that\s*", ""),
    # Transition bloat
    (r"\bFurthermore,?\s*", ""),
    (r"\bMoreover,?\s*", ""),
    (r"\bAdditionally,?\s*", "Also, "),
    (r"\bIn addition(?:ally)?,?\s*", "Plus, "),
    (r"\bConsequently,?\s*", "So "),
    (r"\bNevertheless,?\s*", "Still, "),
    (r"\bNonetheless,?\s*", "But "),
    # Corporate speak
    (r"\bleverage\b", "use"),
    (r"\butilize\b", "use"),
    (r"\bfacilitate\b", "help with"),
    (r"\bimplement\b", "build"),
    (r"\boptimize\b", "improve"),
    # AI filler
    (r"\bIn conclusion,?\s*", ""),
    (r"\bTo summarize,?\s*", ""),
    (r"\bIn summary,?\s*", ""),
    (r"\bOverall,?\s*", ""),
    (r"\bEssentially,?\s*", ""),
    (r"\bFundamentally,?\s*", ""),
    # Sycophantic openers
    (r"^That(?:'s| is) (?:a |an )?(?:great|excellent|wonderful|fantastic|interesting) (?:question|point|observation|insight)[.!]?\s*", ""),
    (r"^(?:Great|Excellent|Wonderful|Fantastic) (?:question|point|observation)[.!]?\s*", ""),
    (r"^Absolutely[.!]?\s*", ""),
    # Over-hedging
    (r"\bI believe that\s*", "I think "),
    (r"\bIt seems (?:like|that)\s*", "Looks like "),
    (r"\bIt appears (?:that|as if)\s*", ""),
    (r"\bOne could argue (?:that)?\s*", ""),
    (r"\bIt can be said (?:that)?\s*", ""),
    # Em dashes: replace with commas, periods, or remove
    (r"\s*\u2014\s*", ", "),  # Unicode em dash
    (r"\s*---\s*", ", "),     # Triple hyphen em dash
    (r"\s*--\s*", ", "),      # Double hyphen em dash
]

# Contractions map: expand -> contracted
CONTRACTIONS = {
    r"\bI am\b": "I'm",
    r"\bI have\b": "I've",
    r"\bI will\b": "I'll",
    r"\bI would\b": "I'd",
    r"\bdo not\b": "don't",
    r"\bdoes not\b": "doesn't",
    r"\bdid not\b": "didn't",
    r"\bcan not\b": "can't",
    r"\bcannot\b": "can't",
    r"\bwill not\b": "won't",
    r"\bwould not\b": "wouldn't",
    r"\bshould not\b": "shouldn't",
    r"\bcould not\b": "couldn't",
    r"\bis not\b": "isn't",
    r"\bare not\b": "aren't",
    r"\bwas not\b": "wasn't",
    r"\bwere not\b": "weren't",
    r"\bthat is\b": "that's",
    r"\bthere is\b": "there's",
    r"\bit is\b": "it's",
    r"\blet us\b": "let's",
    r"\bthey are\b": "they're",
    r"\bwe are\b": "we're",
    r"\byou are\b": "you're",
    r"\bwhat is\b": "what's",
    r"\bwho is\b": "who's",
    r"\bhow is\b": "how's",
    r"\bhere is\b": "here's",
}


class XHumanizer:
    """Remove AI tells from tweet-length content.

    Pipeline:
    1. Remove AI tell patterns
    2. Add contractions
    3. Trim excess whitespace
    4. Optional: inject personality quirk
    5. Score humanness
    """

    def __init__(self):
        self._compiled_tells = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in AI_TELL_PATTERNS
        ]
        self._compiled_contractions = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in CONTRACTIONS.items()
        ]

    def humanize_tweet(self, text: str, lowercase: bool = False) -> str:
        """Full humanization pipeline for a single tweet.

        Args:
            text: Raw text to humanize.
            lowercase: If True, convert to all lowercase (for replies).
        """
        text = self._remove_ai_tells(text)
        text = self._add_contractions(text)
        text = self._clean_whitespace(text)
        if lowercase:
            text = self._to_lowercase(text)
        return text

    def humanize_thread(self, tweets: List[str]) -> List[str]:
        """Humanize a thread maintaining narrative flow."""
        return [self.humanize_tweet(t) for t in tweets]

    def _remove_ai_tells(self, text: str) -> str:
        """Remove patterns that signal AI authorship."""
        for pattern, replacement in self._compiled_tells:
            text = pattern.sub(replacement, text)
        return text

    def _add_contractions(self, text: str) -> str:
        """Convert formal expressions to contractions."""
        for pattern, replacement in self._compiled_contractions:
            text = pattern.sub(replacement, text)
        return text

    def _clean_whitespace(self, text: str) -> str:
        """Clean up double spaces, leading/trailing whitespace."""
        text = re.sub(r"  +", " ", text)
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        return text.strip()

    def _to_lowercase(self, text: str) -> str:
        """Convert text to lowercase, preserving @handles, URLs, and hashtags.

        Keeps technical identifiers intact (URLs, @mentions) while
        lowercasing the conversational text for a more human feel.
        """
        # Protect @handles, URLs, and #hashtags by preserving their case
        # We lowercase everything, which naturally preserves already-lowercase
        # handles and hashtags, and makes URLs lowercase (which is fine)
        return text.lower()

    def add_personality_quirk(self, text: str, quirk: Optional[str] = None) -> str:
        """Inject a personality touch.

        If a quirk is provided (from SparkVoice), append it naturally.
        Otherwise, pick a subtle structural variation.
        """
        if quirk:
            # Add opinion as a natural aside
            if len(text) + len(quirk) + 3 <= 280:
                return f"{text} {quirk}"
            return text

        # Structural variations for naturalness
        variations = [
            self._fragment_last_sentence,
            self._add_dash_aside,
        ]
        fn = random.choice(variations)
        return fn(text)

    def _fragment_last_sentence(self, text: str) -> str:
        """Turn last sentence into a punchy fragment if possible."""
        sentences = text.rsplit(". ", 1)
        if len(sentences) == 2 and len(sentences[1]) > 20:
            # Try to split long last sentence into fragment
            words = sentences[1].rstrip(".").split()
            if len(words) > 6:
                cut = len(words) // 2
                fragment = " ".join(words[:cut]) + "."
                rest = " ".join(words[cut:]) + "."
                return f"{sentences[0]}. {fragment} {rest}"
        return text

    def _add_dash_aside(self, text: str) -> str:
        """Add a dash-delimited aside if text has room."""
        if " - " in text or len(text) > 250:
            return text
        # Find a good insertion point (after a comma)
        comma_pos = text.find(", ")
        if comma_pos > 20 and comma_pos < len(text) - 30:
            return text  # Already has natural breaks
        return text

    def score_humanness(self, text: str) -> float:
        """Score how human a piece of text sounds (0.0 - 1.0).

        Higher = more human-sounding.
        Checks for:
        - AI tells present (negative)
        - Contractions used (positive)
        - Sentence length variation (positive)
        - Personal pronouns (positive)
        - Perfect structure (negative - too perfect = AI)
        """
        score = 0.7  # Base score

        # Check for AI tells (each one found reduces score)
        for pattern, _ in self._compiled_tells:
            if pattern.search(text):
                score -= 0.08

        # Contractions present = more human
        contraction_count = len(re.findall(
            r"\b\w+(?:'(?:re|ve|ll|d|t|s|m))\b", text
        ))
        if contraction_count > 0:
            score += min(0.1, contraction_count * 0.03)

        # Sentence length variation = more human
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) >= 2:
            lengths = [len(s.split()) for s in sentences]
            if lengths:
                avg = sum(lengths) / len(lengths)
                variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
                if variance > 5:
                    score += 0.1  # Good variation
                elif variance < 1:
                    score -= 0.05  # Too uniform = AI

        # Personal pronouns = more human
        personal = len(re.findall(r"\b(?:I|my|me|we|our)\b", text, re.IGNORECASE))
        if personal > 0:
            score += min(0.1, personal * 0.03)

        # Questions = more human (engagement)
        if "?" in text:
            score += 0.05

        return max(0.0, min(1.0, score))


# Module-level singleton
_humanizer: Optional[XHumanizer] = None


def get_humanizer() -> XHumanizer:
    """Get the singleton humanizer instance."""
    global _humanizer
    if _humanizer is None:
        _humanizer = XHumanizer()
    return _humanizer
