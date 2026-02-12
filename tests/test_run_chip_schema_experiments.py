from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "run_chip_schema_experiments.py"
    spec = importlib.util.spec_from_file_location("run_chip_schema_experiments", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_chip_schema_experiments")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_objective_score_uses_weighted_metrics():
    mod = _load_module()
    metrics = {
        "schema_payload_rate": 0.5,
        "schema_statement_rate": 0.4,
        "merge_eligible_rate": 0.3,
        "learning_quality_pass_rate": 0.8,
        "telemetry_rate": 0.9,
        "payload_valid_emission_rate": 0.75,
    }
    weights = {
        "schema_payload_rate": 0.2,
        "schema_statement_rate": 0.3,
        "merge_eligible_rate": 0.2,
        "learning_quality_pass_rate": 0.1,
        "non_telemetry_rate": 0.1,
        "payload_valid_emission_rate": 0.1,
    }
    out = mod._objective_score(metrics, weights)
    assert out > 0.0
    assert out <= 1.0


def test_build_event_contains_required_fields():
    mod = _load_module()
    rng = __import__("random").Random(7)

    s = mod._build_event("social-convo", 0, rng)
    assert "tweet_id" in s and "outcome_type" in s

    e = mod._build_event("engagement-pulse", 0, rng)
    assert "tweet_id" in e and "snapshot_age" in e

    x = mod._build_event("x_social", 0, rng)
    assert "insight" in x and "confidence" in x
