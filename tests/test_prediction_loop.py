import json
import time

from lib import prediction_loop as pl
from lib.queue import EventType, SparkEvent


def _read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_build_predictions_applies_source_budgets(tmp_path, monkeypatch):
    pred_file = tmp_path / "predictions.jsonl"
    monkeypatch.setattr(pl, "PREDICTIONS_FILE", pred_file)

    exposures = []
    for i in range(6):
        exposures.append({"insight_key": f"k-chip-{i}", "text": f"chip insight {i}", "source": "chip_merge"})
    for i in range(4):
        exposures.append({"insight_key": f"k-sync-{i}", "text": f"sync insight {i}", "source": "sync_context"})
    for i in range(4):
        exposures.append({"insight_key": f"k-inj-{i}", "text": f"inject insight {i}", "source": "spark_inject"})

    monkeypatch.setattr(pl, "read_recent_exposures", lambda **_kwargs: exposures)
    monkeypatch.setattr(pl, "get_cognitive_learner", lambda: object())
    monkeypatch.setenv("SPARK_PREDICTION_TOTAL_BUDGET", "20")
    monkeypatch.setenv("SPARK_PREDICTION_DEFAULT_SOURCE_BUDGET", "10")
    monkeypatch.setenv(
        "SPARK_PREDICTION_SOURCE_BUDGETS",
        "chip_merge=2,sync_context=2,spark_inject=2",
    )

    built = pl.build_predictions()
    rows = _read_jsonl(pred_file)
    by_source = {}
    for row in rows:
        source = row.get("source")
        by_source[source] = by_source.get(source, 0) + 1

    assert built == 6
    assert sum(by_source.values()) == 6
    assert by_source.get("chip_merge", 0) <= 2
    assert by_source.get("sync_context", 0) <= 2
    assert by_source.get("spark_inject", 0) <= 2


def test_collect_outcomes_captures_post_tool_success(monkeypatch):
    events = [
        SparkEvent(
            event_type=EventType.POST_TOOL,
            session_id="s1",
            timestamp=123.0,
            data={"trace_id": "trace-1"},
            tool_name="Bash",
            tool_input={"command": "pytest -q"},
        )
    ]

    monkeypatch.setattr(pl, "count_events", lambda: len(events))
    monkeypatch.setattr(pl, "read_events", lambda limit, offset: events[offset : offset + limit])
    monkeypatch.setattr(pl, "_load_state", lambda: {"offset": 0, "matched_ids": []})
    monkeypatch.setattr(pl, "_save_state", lambda _state: None)

    captured = {"rows": []}

    def _capture(rows):
        captured["rows"] = list(rows)
        return len(captured["rows"])

    monkeypatch.setattr(pl, "append_outcomes", _capture)
    stats = pl.collect_outcomes(limit=20)

    assert stats["processed"] == 1
    assert stats["outcomes"] == 1
    assert len(captured["rows"]) == 1
    row = captured["rows"][0]
    assert row["event_type"] == "tool_success"
    assert row["polarity"] == "pos"
    assert row["tool"] == "Bash"
    assert "success" in row["text"]


def test_process_prediction_cycle_runs_auto_link_when_due(monkeypatch):
    saved_states = []
    state = {"offset": 0, "matched_ids": [], "last_auto_link_ts": 0.0}
    calls = {"count": 0}

    monkeypatch.setenv("SPARK_PREDICTION_AUTO_LINK", "1")
    monkeypatch.setenv("SPARK_PREDICTION_AUTO_LINK_INTERVAL_S", "60")
    monkeypatch.setattr(pl, "build_predictions", lambda: 1)
    monkeypatch.setattr(pl, "build_project_predictions", lambda: 0)
    monkeypatch.setattr(pl, "collect_outcomes", lambda limit=200: {"processed": 1, "outcomes": 1})
    monkeypatch.setattr(
        pl,
        "match_predictions",
        lambda: {"matched": 0, "validated": 0, "contradicted": 0, "surprises": 0},
    )
    monkeypatch.setattr(pl, "_load_state", lambda: dict(state))
    monkeypatch.setattr(pl, "_save_state", lambda s: saved_states.append(dict(s)))

    def _auto_link(**_kwargs):
        calls["count"] += 1
        return {"processed": 5, "linked": 2, "skipped": 3}

    monkeypatch.setattr(pl, "auto_link_outcomes", _auto_link)

    stats = pl.process_prediction_cycle(limit=120)

    assert calls["count"] == 1
    assert stats["auto_link_processed"] == 5
    assert stats["auto_link_linked"] == 2
    assert stats["auto_link_skipped"] == 3
    assert any((s.get("last_auto_link_ts") or 0) > 0 for s in saved_states)


def test_process_prediction_cycle_skips_auto_link_within_interval(monkeypatch):
    calls = {"count": 0}
    now = time.time()

    monkeypatch.setenv("SPARK_PREDICTION_AUTO_LINK", "1")
    monkeypatch.setenv("SPARK_PREDICTION_AUTO_LINK_INTERVAL_S", "3600")
    monkeypatch.setattr(pl, "build_predictions", lambda: 0)
    monkeypatch.setattr(pl, "build_project_predictions", lambda: 0)
    monkeypatch.setattr(pl, "collect_outcomes", lambda limit=200: {"processed": 0, "outcomes": 0})
    monkeypatch.setattr(
        pl,
        "match_predictions",
        lambda: {"matched": 0, "validated": 0, "contradicted": 0, "surprises": 0},
    )
    monkeypatch.setattr(pl, "_load_state", lambda: {"offset": 0, "matched_ids": [], "last_auto_link_ts": now})
    monkeypatch.setattr(pl, "_save_state", lambda _state: None)

    def _auto_link(**_kwargs):
        calls["count"] += 1
        return {"processed": 1, "linked": 1, "skipped": 0}

    monkeypatch.setattr(pl, "auto_link_outcomes", _auto_link)
    stats = pl.process_prediction_cycle(limit=50)

    assert calls["count"] == 0
    assert stats["auto_link_processed"] == 0
    assert stats["auto_link_linked"] == 0
