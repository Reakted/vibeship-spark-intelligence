"""Spark Intelligence Observatory — full pipeline visualization for Obsidian.

Public API:
    generate_observatory(force=False) — generate all observatory pages
    maybe_sync_observatory(stats=None) — cooldown-gated auto-sync (call from bridge_cycle)
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

from .config import load_config

_last_sync_ts: float = 0.0


def generate_observatory(*, force: bool = False, verbose: bool = False) -> dict:
    """Generate the full observatory (flow dashboard + 12 stage pages + canvas).

    Returns a summary dict with file counts and timing.
    """
    from .readers import read_all_stages
    from .flow_dashboard import generate_flow_dashboard
    from .stage_pages import generate_all_stage_pages
    from .advisory_reverse_engineering import generate_advisory_reverse_engineering
    from .tuneables_deep_dive import generate_tuneables_deep_dive
    from .system_flow_comprehensive import generate_system_flow_comprehensive
    from .system_flow_operator_playbook import generate_system_flow_operator_playbook
    from .canvas_generator import generate_canvas
    from .explorer import generate_explorer
    from .readability_pack import (
        collect_metrics_snapshot,
        generate_readability_pack,
        load_previous_snapshot,
        save_snapshot,
    )

    t0 = time.time()
    cfg = load_config()

    if not cfg.enabled and not force:
        return {"skipped": True, "reason": "disabled"}

    vault = Path(cfg.vault_dir).expanduser()
    obs_dir = vault / "_observatory"
    stages_dir = obs_dir / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)

    # Read all stage data
    data = read_all_stages(max_recent=cfg.max_recent_items)
    if verbose:
        print(f"  [observatory] read {len(data)} stages in {(time.time()-t0)*1000:.0f}ms")

    # Generate flow dashboard
    flow_path = obs_dir / "flow.md"
    flow_content = generate_flow_dashboard(data)
    flow_path.write_text(flow_content, encoding="utf-8")

    # Generate reverse-engineered advisory path page
    reverse_path = obs_dir / "advisory_reverse_engineering.md"
    reverse_content = generate_advisory_reverse_engineering(data)
    reverse_path.write_text(reverse_content, encoding="utf-8")

    # Generate tuneables deep dive page
    tuneables_dive_path = obs_dir / "tuneables_deep_dive.md"
    tuneables_dive_content = generate_tuneables_deep_dive(data)
    tuneables_dive_path.write_text(tuneables_dive_content, encoding="utf-8")

    # Generate comprehensive full-system reverse-engineering page
    comprehensive_path = obs_dir / "system_flow_comprehensive.md"
    comprehensive_content = generate_system_flow_comprehensive(data)
    comprehensive_path.write_text(comprehensive_content, encoding="utf-8")

    # Generate operator playbook page
    playbook_path = obs_dir / "system_flow_operator_playbook.md"
    playbook_content = generate_system_flow_operator_playbook(data)
    playbook_path.write_text(playbook_content, encoding="utf-8")

    # Generate readability/navigation pages
    previous_snapshot = load_previous_snapshot(obs_dir)
    current_snapshot = collect_metrics_snapshot(data)
    for filename, content in generate_readability_pack(
        data, current_snapshot=current_snapshot, previous_snapshot=previous_snapshot
    ):
        (obs_dir / filename).write_text(content, encoding="utf-8")
    save_snapshot(obs_dir, current_snapshot)

    # Generate stage pages
    files_written = 10  # flow + reverse + tuneables_dive + comprehensive + playbook + 5 readability pages
    for filename, content in generate_all_stage_pages(data):
        (stages_dir / filename).write_text(content, encoding="utf-8")
        files_written += 1

    # Generate canvas
    if cfg.generate_canvas:
        canvas_path = obs_dir / "flow.canvas"
        canvas_content = generate_canvas()
        canvas_path.write_text(canvas_content, encoding="utf-8")
        files_written += 1

    # Generate explorer (individual item detail pages)
    t_explore = time.time()
    explorer_counts = generate_explorer(cfg)
    explorer_total = sum(explorer_counts.values()) + 1  # +1 for master index
    files_written += explorer_total
    if verbose:
        print(f"  [observatory] explorer: {explorer_total} files in {(time.time()-t_explore)*1000:.0f}ms")
        for section, count in explorer_counts.items():
            print(f"    {section}: {count} pages")

    elapsed_ms = (time.time() - t0) * 1000
    if verbose:
        print(f"  [observatory] total: {files_written} files in {elapsed_ms:.0f}ms to {obs_dir}")

    return {
        "files_written": files_written,
        "elapsed_ms": round(elapsed_ms, 1),
        "vault_dir": str(vault),
        "explorer": explorer_counts,
    }


def maybe_sync_observatory(stats: dict | None = None) -> None:
    """Cooldown-gated sync — safe to call every bridge cycle."""
    global _last_sync_ts

    try:
        cfg = load_config()
        if not cfg.enabled or not cfg.auto_sync:
            return

        now = time.time()
        if (now - _last_sync_ts) < cfg.sync_cooldown_s:
            return

        _last_sync_ts = now
        generate_observatory()
    except Exception:
        # Non-critical — never crash the pipeline
        traceback.print_exc()
