from __future__ import annotations

import lib.advisory_packet_store as store
import lib.advisory_prefetch_worker as worker


def _patch_store_paths(monkeypatch, tmp_path):
    packet_dir = tmp_path / "advice_packets"
    monkeypatch.setattr(store, "PACKET_DIR", packet_dir)
    monkeypatch.setattr(store, "INDEX_FILE", packet_dir / "index.json")
    monkeypatch.setattr(store, "PREFETCH_QUEUE_FILE", packet_dir / "prefetch_queue.jsonl")


def test_process_prefetch_queue_creates_packets(monkeypatch, tmp_path):
    _patch_store_paths(monkeypatch, tmp_path)
    store.enqueue_prefetch_job(
        {
            "session_id": "s1",
            "project_key": "proj",
            "intent_family": "auth_security",
            "task_plane": "build_delivery",
            "session_context_key": "ctx",
        }
    )

    result = worker.process_prefetch_queue(max_jobs=1, max_tools_per_job=2)
    assert result.get("ok") is True
    assert int(result.get("jobs_processed", 0)) == 1
    assert int(result.get("packets_created", 0)) >= 1

    status = worker.get_worker_status()
    assert int(status.get("processed_count", 0)) >= 1
    assert int(status.get("pending_jobs", 0)) == 0


def test_prefetch_worker_pause_resume(monkeypatch, tmp_path):
    _patch_store_paths(monkeypatch, tmp_path)
    worker.set_worker_paused(True, reason="test")
    store.enqueue_prefetch_job(
        {
            "session_id": "s2",
            "project_key": "proj",
            "intent_family": "testing_validation",
            "task_plane": "build_delivery",
            "session_context_key": "ctx2",
        }
    )

    paused_result = worker.process_prefetch_queue(max_jobs=1, max_tools_per_job=1)
    assert paused_result.get("ok") is False
    assert paused_result.get("reason") == "paused"

    worker.set_worker_paused(False)
    resumed_result = worker.process_prefetch_queue(max_jobs=1, max_tools_per_job=1)
    assert resumed_result.get("ok") is True
    assert int(resumed_result.get("jobs_processed", 0)) >= 1

