"""Spark Emotions runtime layer.

Provides bounded emotional state updates, mode routing, and TTS profile mapping.
Designed for conversational humanity with explicit safety boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal
import json

Mode = Literal["spark_alive", "real_talk", "calm_focus"]

SPARK_DIR = Path(__file__).parent.parent / ".spark"
STATE_FILE = SPARK_DIR / "emotion_state.json"


@dataclass
class EmotionState:
    warmth: float = 0.70
    energy: float = 0.62
    confidence: float = 0.72
    calm: float = 0.66
    playfulness: float = 0.48
    strain: float = 0.20
    mode: Mode = "real_talk"
    updated_at: str = ""


MODE_TARGETS: Dict[Mode, Dict[str, float]] = {
    "spark_alive": {"warmth": 0.78, "energy": 0.74, "calm": 0.58, "playfulness": 0.62},
    "real_talk": {"warmth": 0.70, "energy": 0.60, "calm": 0.70, "playfulness": 0.42},
    "calm_focus": {"warmth": 0.62, "energy": 0.40, "calm": 0.86, "playfulness": 0.24},
}

VOICE_PROFILE_BY_MODE: Dict[Mode, Dict[str, Any]] = {
    "spark_alive": {
        "provider": "elevenlabs",
        "speed": 0.92,
        "stability": 0.70,
        "similarityBoost": 0.66,
        "style": 0.14,
    },
    "real_talk": {
        "provider": "elevenlabs",
        "speed": 0.91,
        "stability": 0.70,
        "similarityBoost": 0.70,
        "style": 0.05,
    },
    "calm_focus": {
        "provider": "elevenlabs",
        "speed": 0.89,
        "stability": 0.76,
        "similarityBoost": 0.64,
        "style": 0.02,
    },
}


class SparkEmotions:
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> EmotionState:
        if self.state_file.exists():
            try:
                raw = json.loads(self.state_file.read_text(encoding="utf-8"))
                return EmotionState(**raw)
            except Exception:
                pass
        state = EmotionState(updated_at=self._now())
        self._save_state(state)
        return state

    def _save_state(self, state: EmotionState) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    @staticmethod
    def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, float(v)))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def set_mode(self, mode: Mode) -> EmotionState:
        if mode not in MODE_TARGETS:
            raise ValueError(f"Unsupported mode: {mode}")
        self.state.mode = mode
        targets = MODE_TARGETS[mode]
        for k, target in targets.items():
            cur = getattr(self.state, k)
            # bounded move toward target (no abrupt jumps)
            step = 0.22
            nxt = cur + (target - cur) * step
            setattr(self.state, k, self._clamp(nxt))
        self.state.updated_at = self._now()
        self._save_state(self.state)
        return self.state

    def apply_feedback(
        self,
        *,
        too_fast: bool = False,
        too_sharp: bool = False,
        too_flat: bool = False,
        too_intense: bool = False,
        wants_more_emotion: bool = False,
    ) -> EmotionState:
        s = self.state
        if too_fast:
            s.energy = self._clamp(s.energy - 0.08)
            s.calm = self._clamp(s.calm + 0.08)
        if too_sharp:
            s.calm = self._clamp(s.calm + 0.06)
            s.playfulness = self._clamp(s.playfulness - 0.03)
        if too_flat:
            s.energy = self._clamp(s.energy + 0.06)
            s.playfulness = self._clamp(s.playfulness + 0.06)
        if too_intense:
            s.energy = self._clamp(s.energy - 0.07)
            s.calm = self._clamp(s.calm + 0.07)
        if wants_more_emotion:
            s.warmth = self._clamp(s.warmth + 0.07)
            s.playfulness = self._clamp(s.playfulness + 0.05)

        s.updated_at = self._now()
        self._save_state(s)
        return s

    def voice_profile(self) -> Dict[str, Any]:
        base = dict(VOICE_PROFILE_BY_MODE[self.state.mode])

        # state-conditioned adjustments
        base["speed"] = round(self._clamp(base["speed"] + (self.state.energy - 0.60) * 0.08, 0.85, 1.12), 2)
        base["stability"] = round(self._clamp(base["stability"] + (self.state.calm - 0.65) * 0.25, 0.35, 0.82), 2)
        base["style"] = round(self._clamp(base["style"] + (self.state.playfulness - 0.45) * 0.20, 0.01, 0.35), 2)
        return base

    def status(self) -> Dict[str, Any]:
        return {
            "state": asdict(self.state),
            "voiceProfile": self.voice_profile(),
            "safety": {
                "no_fake_sentience": True,
                "no_manipulation": True,
                "clarity_over_theatrics": True,
            },
        }


__all__ = ["SparkEmotions", "EmotionState", "Mode"]
