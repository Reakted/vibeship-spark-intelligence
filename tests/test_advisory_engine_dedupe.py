from __future__ import annotations

import time

from lib import advisory_engine
from lib.advisory_state import SessionState


def test_text_fingerprint_normalizes_whitespace_and_case():
    a = advisory_engine._text_fingerprint("Run focused TESTS now")
    b = advisory_engine._text_fingerprint("  run focused tests   now  ")
    assert a
    assert a == b


def test_duplicate_repeat_state_within_cooldown(monkeypatch):
    monkeypatch.setattr(advisory_engine, "ADVISORY_TEXT_REPEAT_COOLDOWN_S", 60.0)
    state = SessionState(session_id="s1")
    state.last_advisory_text_fingerprint = advisory_engine._text_fingerprint(
        "Run focused tests now"
    )
    state.last_advisory_at = time.time() - 10

    meta = advisory_engine._duplicate_repeat_state(state, "run focused tests now")
    assert meta["repeat"] is True
    assert meta["fingerprint"] == state.last_advisory_text_fingerprint


def test_duplicate_repeat_state_allows_after_cooldown(monkeypatch):
    monkeypatch.setattr(advisory_engine, "ADVISORY_TEXT_REPEAT_COOLDOWN_S", 15.0)
    state = SessionState(session_id="s2")
    state.last_advisory_text_fingerprint = advisory_engine._text_fingerprint(
        "Run focused tests now"
    )
    state.last_advisory_at = time.time() - 30

    meta = advisory_engine._duplicate_repeat_state(state, "run focused tests now")
    assert meta["repeat"] is False
