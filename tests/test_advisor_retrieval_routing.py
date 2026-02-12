from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import lib.advisor as advisor_mod
import lib.semantic_retriever as semantic_retriever_mod


class _DummyCognitive:
    def __init__(self) -> None:
        self.insights = {
            "insight-1": SimpleNamespace(insight="Rotate auth tokens safely", reliability=0.8, context="auth"),
            "insight-2": SimpleNamespace(insight="Diagnose memory transport timeouts", reliability=0.75, context="memory"),
            "insight-3": SimpleNamespace(insight="Verify session scope before retrieval", reliability=0.7, context="session"),
        }

    def is_noise_insight(self, _text: str) -> bool:
        return False

    def get_insights_for_context(self, *_args, **_kwargs):
        return []


class _FakeRetriever:
    def __init__(self, *, primary_count: int = 3, primary_score: float = 0.86, facet_score: float = 0.74) -> None:
        self.primary_count = primary_count
        self.primary_score = primary_score
        self.facet_score = facet_score
        self.calls = []

    def retrieve(self, query: str, _insights, limit: int = 8):
        self.calls.append(query)
        if "failure pattern and fix" in query:
            token = query.split()[0]
            return [
                SimpleNamespace(
                    insight_key=f"facet:{token}",
                    insight_text=f"{token} fallback fix",
                    semantic_sim=self.facet_score,
                    trigger_conf=0.0,
                    fusion_score=self.facet_score,
                    source_type="semantic",
                    why="Facet retrieval",
                )
            ][:limit]

        rows = []
        for idx in range(self.primary_count):
            score = max(0.05, self.primary_score - (0.02 * idx))
            rows.append(
                SimpleNamespace(
                    insight_key=f"primary:{idx}",
                    insight_text=f"primary retrieval result {idx}",
                    semantic_sim=score,
                    trigger_conf=0.0,
                    fusion_score=score,
                    source_type="semantic",
                    why="Primary retrieval",
                )
            )
        return rows[:limit]


def _patch_advisor_runtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(advisor_mod, "ADVISOR_DIR", tmp_path)
    monkeypatch.setattr(advisor_mod, "ADVICE_LOG", tmp_path / "advice_log.jsonl")
    monkeypatch.setattr(advisor_mod, "EFFECTIVENESS_FILE", tmp_path / "effectiveness.json")
    monkeypatch.setattr(advisor_mod, "ADVISOR_METRICS", tmp_path / "metrics.json")
    monkeypatch.setattr(advisor_mod, "RECENT_ADVICE_LOG", tmp_path / "recent_advice.jsonl")
    monkeypatch.setattr(advisor_mod, "RETRIEVAL_ROUTE_LOG", tmp_path / "retrieval_router.jsonl")
    monkeypatch.setattr(advisor_mod, "get_cognitive_learner", lambda: _DummyCognitive())
    monkeypatch.setattr(advisor_mod, "get_mind_bridge", lambda: None)


def _policy_with(advisor: advisor_mod.SparkAdvisor, **updates):
    policy = copy.deepcopy(advisor.retrieval_policy)
    policy.update(updates)
    return policy


def _load_last_route(path: Path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    return json.loads(lines[-1])


def test_embeddings_only_mode_skips_agentic_queries(monkeypatch, tmp_path):
    _patch_advisor_runtime(monkeypatch, tmp_path)
    fake = _FakeRetriever(primary_count=3, primary_score=0.9)
    monkeypatch.setattr(semantic_retriever_mod, "get_semantic_retriever", lambda: fake)

    advisor = advisor_mod.SparkAdvisor()
    advisor.retrieval_policy = _policy_with(
        advisor,
        mode="embeddings_only",
        max_queries=4,
        agentic_query_limit=4,
        min_results_no_escalation=1,
        min_top_score_no_escalation=0.2,
    )

    advice = advisor._get_semantic_cognitive_advice("Edit", "memory retrieval diagnostics and session checks")

    assert advice
    assert len(fake.calls) == 1
    assert all(item.source in {"semantic", "trigger"} for item in advice)


def test_auto_mode_uses_primary_route_for_strong_simple_query(monkeypatch, tmp_path):
    _patch_advisor_runtime(monkeypatch, tmp_path)
    fake = _FakeRetriever(primary_count=4, primary_score=0.9)
    monkeypatch.setattr(semantic_retriever_mod, "get_semantic_retriever", lambda: fake)

    advisor = advisor_mod.SparkAdvisor()
    advisor.retrieval_policy = _policy_with(
        advisor,
        mode="auto",
        complexity_threshold=4,
        max_queries=4,
        agentic_query_limit=4,
        min_results_no_escalation=3,
        min_top_score_no_escalation=0.8,
    )

    advice = advisor._get_semantic_cognitive_advice("Read", "fix memory indexing issue")
    route = _load_last_route(tmp_path / "retrieval_router.jsonl")

    assert advice
    assert len(fake.calls) == 1
    assert all(item.source in {"semantic", "trigger"} for item in advice)
    assert route["escalated"] is False
    assert route["route"] == "semantic"


def test_auto_mode_escalates_for_complex_high_risk_query(monkeypatch, tmp_path):
    _patch_advisor_runtime(monkeypatch, tmp_path)
    fake = _FakeRetriever(primary_count=4, primary_score=0.88, facet_score=0.72)
    monkeypatch.setattr(semantic_retriever_mod, "get_semantic_retriever", lambda: fake)

    advisor = advisor_mod.SparkAdvisor()
    advisor.retrieval_policy = _policy_with(
        advisor,
        mode="auto",
        complexity_threshold=2,
        max_queries=4,
        agentic_query_limit=3,
        min_results_no_escalation=1,
        min_top_score_no_escalation=0.2,
    )

    advice = advisor._get_semantic_cognitive_advice(
        "Bash",
        "What root cause pattern should we compare across auth token session failures in production memory retrieval?",
    )

    assert advice
    assert len(fake.calls) > 1
    assert any(item.source == "semantic-agentic" for item in advice)


def test_hybrid_agentic_mode_always_escalates(monkeypatch, tmp_path):
    _patch_advisor_runtime(monkeypatch, tmp_path)
    fake = _FakeRetriever(primary_count=3, primary_score=0.9)
    monkeypatch.setattr(semantic_retriever_mod, "get_semantic_retriever", lambda: fake)

    advisor = advisor_mod.SparkAdvisor()
    advisor.retrieval_policy = _policy_with(
        advisor,
        mode="hybrid_agentic",
        max_queries=4,
        agentic_query_limit=3,
        min_results_no_escalation=5,
        min_top_score_no_escalation=0.99,
    )

    advice = advisor._get_semantic_cognitive_advice(
        "Edit",
        "memory retrieval diagnostics compare timeline and transport behavior",
    )

    assert advice
    assert len(fake.calls) > 1
    assert any(item.source == "semantic-agentic" for item in advice)


def test_bm25_rerank_prefers_term_dense_candidate(monkeypatch, tmp_path):
    _patch_advisor_runtime(monkeypatch, tmp_path)

    class _FixedRetriever:
        def retrieve(self, _query: str, _insights, limit: int = 8):
            rows = [
                SimpleNamespace(
                    insight_key="dense-a",
                    insight_text="auth token session rotation guide",
                    semantic_sim=0.82,
                    trigger_conf=0.0,
                    fusion_score=0.8,
                    source_type="semantic",
                    why="semantic baseline",
                ),
                SimpleNamespace(
                    insight_key="dense-b",
                    insight_text="auth token session token token token rollback pattern",
                    semantic_sim=0.82,
                    trigger_conf=0.0,
                    fusion_score=0.8,
                    source_type="semantic",
                    why="semantic baseline",
                ),
            ]
            return rows[:limit]

    monkeypatch.setattr(semantic_retriever_mod, "get_semantic_retriever", lambda: _FixedRetriever())

    advisor = advisor_mod.SparkAdvisor()
    advisor.retrieval_policy = _policy_with(
        advisor,
        mode="embeddings_only",
        lexical_weight=0.4,
        bm25_mix=0.8,
        max_queries=1,
        agentic_query_limit=1,
        min_results_no_escalation=1,
        min_top_score_no_escalation=0.1,
    )

    advice = advisor._get_semantic_cognitive_advice("Read", "auth token session rollback")

    assert advice
    assert advice[0].insight_key == "dense-b"
