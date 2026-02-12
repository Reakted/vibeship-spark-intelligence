from __future__ import annotations

from types import SimpleNamespace

from lib import advisory_engine


def test_advice_rows_include_proof_refs_and_evidence_hash():
    item = SimpleNamespace(
        advice_id="aid-1",
        insight_key="reasoning:k1",
        text="Run focused tests after edit.",
        confidence=0.8,
        source="cognitive",
        context_match=0.7,
        reason="Recent failures on the same flow.",
    )

    rows = advisory_engine._advice_to_rows_with_proof([item], trace_id="trace-123")
    assert len(rows) == 1
    row = rows[0]
    assert row["proof_refs"]["trace_id"] == "trace-123"
    assert row["proof_refs"]["insight_key"] == "reasoning:k1"
    assert row["proof_refs"]["source"] == "cognitive"
    assert row["evidence_hash"]


def test_advice_rows_wrapper_works_without_trace_id():
    item = SimpleNamespace(
        advice_id="aid-2",
        insight_key="context:k2",
        text="Validate payload contract before merge.",
        confidence=0.6,
        source="advisor",
        context_match=0.5,
        reason="",
    )

    rows = advisory_engine._advice_to_rows([item])
    assert len(rows) == 1
    assert "trace_id" not in rows[0]["proof_refs"]
    assert rows[0]["proof_refs"]["advice_id"] == "aid-2"
