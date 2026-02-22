from __future__ import annotations

import json

import lib.advisory_gate as gate


def test_load_gate_config_reads_advisory_gate_section(tmp_path):
    tuneables = tmp_path / "tuneables.json"
    tuneables.write_text(
        json.dumps(
            {
                "advisor": {"max_items": 4},
                "advisory_gate": {
                    "max_emit_per_call": 2,
                    "tool_cooldown_s": 120,
                    "advice_repeat_cooldown_s": 2400,
                    "shown_advice_ttl_s": 3600,
                    "category_cooldown_multipliers": {"security": 2.0, "mind": 0.5},
                },
            }
        ),
        encoding="utf-8",
    )

    cfg = gate._load_gate_config(path=tuneables)

    assert cfg["max_emit_per_call"] == 2
    assert cfg["tool_cooldown_s"] == 120
    assert cfg["advice_repeat_cooldown_s"] == 2400
    assert cfg["shown_advice_ttl_s"] == 3600
    assert cfg["category_cooldown_multipliers"]["security"] == 2.0


def test_apply_gate_config_updates_runtime_values():
    original = gate.get_gate_config()
    try:
        result = gate.apply_gate_config(
            {
                "max_emit_per_call": 2,
                "tool_cooldown_s": 180,
                "advice_repeat_cooldown_s": 7200,
                "shown_advice_ttl_s": 900,
                "category_cooldown_multipliers": {"security": 1.8, "context": 0.8},
                "warning_threshold": 0.82,
                "note_threshold": 0.52,
                "whisper_threshold": 0.36,
            }
        )
        cfg = gate.get_gate_config()

        assert "max_emit_per_call" in result["applied"]
        assert "tool_cooldown_s" in result["applied"]
        assert "advice_repeat_cooldown_s" in result["applied"]
        assert "shown_advice_ttl_s" in result["applied"]
        assert "category_cooldown_multipliers" in result["applied"]
        assert cfg["max_emit_per_call"] == 2
        assert cfg["tool_cooldown_s"] == 180
        assert cfg["advice_repeat_cooldown_s"] == 7200
        assert cfg["shown_advice_ttl_s"] == 900
        assert cfg["category_cooldown_multipliers"]["security"] == 1.8
        assert cfg["warning_threshold"] == 0.82
        assert cfg["note_threshold"] == 0.52
        assert cfg["whisper_threshold"] == 0.36
    finally:
        gate.apply_gate_config(original)
