from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "memory_retrieval_ab.py"
    spec = importlib.util.spec_from_file_location("memory_retrieval_ab", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load memory_retrieval_ab module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_error_kind_mapping():
    mod = _load_module()

    assert mod.classify_error_kind("HTTP 401 unauthorized token missing") == "auth"
    assert mod.classify_error_kind("request timeout after 30s") == "timeout"
    assert mod.classify_error_kind("blocked by policy guardrail") == "policy"
    assert mod.classify_error_kind("connection refused by upstream") == "transport"
    assert mod.classify_error_kind("unhandled exception") == "unknown"


def test_compute_case_metrics_with_labels():
    mod = _load_module()

    case = mod.EvalCase(
        case_id="c1",
        query="auth token rotation",
        relevant_insight_keys=["key-2"],
        relevant_contains=[],
        notes="",
    )
    items = [
        mod.RetrievedItem(
            insight_key="key-1",
            text="first result",
            source="hybrid",
            semantic_score=0.9,
            fusion_score=0.9,
            score=0.9,
            why="",
        ),
        mod.RetrievedItem(
            insight_key="key-2",
            text="matching result",
            source="hybrid",
            semantic_score=0.8,
            fusion_score=0.8,
            score=0.8,
            why="",
        ),
    ]

    metrics = mod.compute_case_metrics(case, items, 2)
    assert metrics.hits == 1
    assert metrics.label_count == 1
    assert metrics.precision_at_k == 0.5
    assert metrics.recall_at_k == 1.0
    assert metrics.mrr == 0.5
    assert metrics.top1_hit is False


def test_compute_case_metrics_without_labels():
    mod = _load_module()
    case = mod.EvalCase(case_id="c2", query="any", notes="")
    items = []

    metrics = mod.compute_case_metrics(case, items, 5)
    assert metrics.precision_at_k is None
    assert metrics.recall_at_k is None
    assert metrics.mrr is None
    assert metrics.top1_hit is None
    assert metrics.hits == 0
    assert metrics.label_count == 0
