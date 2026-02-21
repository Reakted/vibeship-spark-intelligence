"""Generate per-stage detail pages for the Obsidian observatory."""

from __future__ import annotations

from typing import Any, Iterator

from .linker import (
    stage_link_from_stage, flow_link, fmt_ts, fmt_ago, fmt_num, fmt_size, health_badge,
)


def generate_all_stage_pages(data: dict[int, dict[str, Any]]) -> Iterator[tuple[str, str]]:
    """Yield (filename, content) for each stage page."""
    generators = {
        1: _gen_event_capture,
        2: _gen_queue,
        3: _gen_pipeline,
        4: _gen_memory_capture,
        5: _gen_meta_ralph,
        6: _gen_cognitive,
        7: _gen_eidos,
        8: _gen_advisory,
        9: _gen_promotion,
        10: _gen_chips,
        11: _gen_predictions,
        12: _gen_tuneables,
    }
    slugs = {
        1: "01-event-capture.md",
        2: "02-queue.md",
        3: "03-pipeline.md",
        4: "04-memory-capture.md",
        5: "05-meta-ralph.md",
        6: "06-cognitive-learner.md",
        7: "07-eidos.md",
        8: "08-advisory.md",
        9: "09-promotion.md",
        10: "10-chips.md",
        11: "11-predictions.md",
        12: "12-tuneables.md",
    }
    for num in range(1, 13):
        gen = generators[num]
        filename = slugs[num]
        content = gen(data.get(num, {}), data)
        yield filename, content


def _header(num: int, name: str, purpose: str, upstream: list[int], downstream: list[int]) -> str:
    """Generate consistent page header with breadcrumbs."""
    lines = [f"# Stage {num}: {name}\n"]
    lines.append(f"> Part of the {flow_link()}")

    up_links = " | ".join(stage_link_from_stage(u) for u in upstream) if upstream else "External events"
    down_links = " | ".join(stage_link_from_stage(d) for d in downstream) if downstream else "End of flow"
    lines.append(f"> Upstream: {up_links}")
    lines.append(f"> Downstream: {down_links}\n")
    lines.append(f"**Purpose:** {purpose}\n")
    return "\n".join(lines)


def _health_table(rows: list[tuple[str, str, str]]) -> str:
    """Generate a health metrics table."""
    lines = ["## Health\n"]
    lines.append("| Metric | Value | Status |")
    lines.append("|--------|-------|--------|")
    for metric, value, status in rows:
        lines.append(f"| {metric} | {value} | {health_badge(status)} |")
    lines.append("")
    return "\n".join(lines)


def _source_files(lib_path: str, state_files: list[str]) -> str:
    """Generate source files section."""
    lines = ["## Source Files\n"]
    lines.append(f"- `{lib_path}` — Core implementation")
    for sf in state_files:
        lines.append(f"- `~/.spark/{sf}` — State storage")
    lines.append("")
    return "\n".join(lines)


# ── Stage 1: Event Capture ──────────────────────────────────────────

def _gen_event_capture(d: dict, all_data: dict) -> str:
    s = _header(1, "Event Capture", "Hooks into Claude Code to capture tool events, make predictions, and start EIDOS steps.", [], [2])
    s += _health_table([
        ("Last cycle", fmt_ago(d.get("last_cycle_ts")), "healthy" if d.get("last_cycle_ts") else "warning"),
        ("Scheduler", fmt_ago(d.get("scheduler_ts")), "healthy" if d.get("scheduler_ts") else "warning"),
        ("Watchdog", d.get("watchdog_status", "unknown"), "healthy" if d.get("watchdog_status") == "ok" else "warning"),
        ("Errors last cycle", str(len(d.get("errors", []))), "healthy" if not d.get("errors") else "warning"),
    ])

    if d.get("errors"):
        s += "## Recent Errors\n\n"
        for err in d["errors"][:5]:
            s += f"- {err}\n"
        s += "\n"

    s += _source_files("hooks/observe.py", [
        "bridge_worker_heartbeat.json",
        "scheduler_heartbeat.json",
        "watchdog_state.json",
    ])
    return s


# ── Stage 2: Queue ──────────────────────────────────────────────────

def _gen_queue(d: dict, all_data: dict) -> str:
    pending = d.get("estimated_pending", 0)
    status = "healthy" if pending < 5000 else ("warning" if pending < 20000 else "critical")
    s = _header(2, "Queue", "Buffers events from hooks for batch processing. Uses append-only JSONL with overflow sidecar for lock contention.", [1], [3])
    s += _health_table([
        ("Estimated pending", f"~{fmt_num(pending)}", status),
        ("Events file size", fmt_size(d.get("events_file_size", 0)), "healthy"),
        ("Head bytes", fmt_num(d.get("head_bytes", 0)), "healthy"),
        ("Overflow active", "yes" if d.get("overflow_exists") else "no",
         "warning" if d.get("overflow_exists") else "healthy"),
        ("Last write", fmt_ago(d.get("events_mtime")), "healthy"),
    ])

    if d.get("overflow_exists"):
        s += f"## Overflow Sidecar\n\nOverflow file exists ({fmt_size(d.get('overflow_size', 0))}). "
        s += "This means lock contention was detected — events are being buffered safely.\n\n"

    s += _source_files("lib/queue.py", [
        "queue/events.jsonl",
        "queue/state.json",
        "queue/events.overflow.jsonl",
    ])
    return s


# ── Stage 3: Pipeline ───────────────────────────────────────────────

def _gen_pipeline(d: dict, all_data: dict) -> str:
    s = _header(3, "Pipeline", "Processes event batches in priority order (HIGH > MEDIUM > LOW). Extracts patterns, tool effectiveness, error patterns, and session workflows.", [2], [4, 5, 7, 10, 11])
    s += _health_table([
        ("Events processed", fmt_num(d.get("total_events_processed", 0)), "healthy"),
        ("Insights created", fmt_num(d.get("total_insights_created", 0)), "healthy"),
        ("Processing rate", f"{d.get('last_processing_rate', 0):.1f} ev/s", "healthy"),
        ("Last batch size", fmt_num(d.get("last_batch_size", 0)), "healthy"),
        ("Empty cycles", fmt_num(d.get("consecutive_empty_cycles", 0)),
         "healthy" if d.get("consecutive_empty_cycles", 0) < 10 else "warning"),
        ("Last cycle", fmt_ago(d.get("last_cycle_ts")), "healthy"),
    ])

    # Recent cycles table
    cycles = d.get("recent_cycles", [])
    if cycles:
        s += "## Recent Cycles\n\n"
        s += "| Duration | Events | Insights | Patterns | Rate | Health |\n"
        s += "|----------|--------|----------|----------|------|--------|\n"
        for c in cycles:
            dur = f"{c.get('cycle_duration_ms', 0):.0f}ms"
            evts = c.get("events_read", 0)
            ly = c.get("learning_yield", {})
            insights = ly.get("insights_created", 0)
            patterns = ly.get("patterns_detected", 0)
            health = c.get("health", {})
            rate = f"{health.get('processing_rate_eps', 0):.0f}"
            bp = health.get("backpressure_level", "?")
            s += f"| {dur} | {evts} | {insights} | {patterns} | {rate} ev/s | {bp} |\n"
        s += "\n"

    s += _source_files("lib/pipeline.py + lib/bridge_cycle.py", [
        "pipeline_state.json",
        "pipeline_metrics.json",
    ])
    return s


# ── Stage 4: Memory Capture ─────────────────────────────────────────

def _gen_memory_capture(d: dict, all_data: dict) -> str:
    s = _header(4, "Memory Capture", "Scans events for high-signal user intent (explicit markers + importance scoring). Detects domain hints and categorizes memories.", [3], [5])
    s += _health_table([
        ("Pending memories", fmt_num(d.get("pending_count", 0)), "healthy"),
        ("Last capture", fmt_ago(d.get("last_capture_ts")), "healthy"),
    ])

    # Category distribution
    cats = d.get("category_distribution", {})
    if cats:
        s += "## Category Distribution\n\n"
        s += "| Category | Count |\n"
        s += "|----------|-------|\n"
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            s += f"| {cat} | {count} |\n"
        s += "\n"

    # Recent pending items
    items = d.get("recent_pending", [])
    if items:
        s += "## Recent Pending Items\n\n"
        for i, item in enumerate(items, 1):
            s += f"{i}. **[{item['category']}]** (score: {item['score']:.2f}, {item['status']})\n"
            s += f"   {item['text']}\n"
        s += "\n"

    s += _source_files("lib/memory_capture.py", [
        "pending_memory.json",
        "memory_capture_state.json",
    ])
    return s


# ── Stage 5: Meta-Ralph ─────────────────────────────────────────────

def _gen_meta_ralph(d: dict, all_data: dict) -> str:
    s = _header(5, "Meta-Ralph", "Quality gate for ALL insights. Multi-dimensional scoring: actionability, novelty, reasoning, specificity, outcome-linkage, ethics. Detects primitives, tautologies, circular reasoning, and noise.", [4, 3], [6])
    s += _health_table([
        ("Total roasted", fmt_num(d.get("total_roasted", 0)), "healthy"),
        ("Learnings stored", fmt_num(d.get("learnings_count", 0)), "healthy"),
    ])

    # Verdict distribution
    verdicts = d.get("verdict_distribution", {})
    if verdicts:
        total = sum(verdicts.values())
        s += "## Verdict Distribution\n\n"
        s += "| Verdict | Count | % |\n"
        s += "|---------|-------|---|\n"
        for v, count in sorted(verdicts.items(), key=lambda x: -x[1]):
            pct = round(count / max(total, 1) * 100, 1)
            s += f"| {v} | {count} | {pct}% |\n"
        s += "\n"

    # Recent verdicts
    recent = d.get("recent_verdicts", [])
    if recent:
        s += "## Recent Verdicts\n\n"
        s += "| Time | Source | Verdict | Score | Issues |\n"
        s += "|------|--------|---------|-------|--------|\n"
        for entry in recent:
            issues = ", ".join(entry.get("issues", [])[:2]) or "—"
            s += f"| {entry['ts'][:19]} | {entry['source']} | **{entry['verdict']}** | {entry['score']} | {issues} |\n"
        s += "\n"

    s += _source_files("lib/meta_ralph.py", [
        "meta_ralph/learnings_store.json",
        "meta_ralph/roast_history.json",
        "meta_ralph/outcome_tracking.json",
    ])
    return s


# ── Stage 6: Cognitive Learner ───────────────────────────────────────

def _gen_cognitive(d: dict, all_data: dict) -> str:
    s = _header(6, "Cognitive Learner", "Stores refined insights with reliability tracking, validation counts, and promotion status. Noise filter: 41 patterns. Deduplication via similarity threshold.", [5], [8, 9])
    s += _health_table([
        ("Total insights", fmt_num(d.get("total_insights", 0)), "healthy"),
        ("Categories", fmt_num(len(d.get("category_distribution", {}))), "healthy"),
        ("Last updated", fmt_ago(d.get("mtime")), "healthy"),
    ])

    # Category distribution
    cats = d.get("category_distribution", {})
    if cats:
        s += "## Category Distribution\n\n"
        s += "```mermaid\npie title Insight Categories\n"
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            s += f'    "{cat}" : {count}\n'
        s += "```\n\n"

    # Top insights
    top = d.get("top_insights", [])
    if top:
        s += "## Top Insights (by reliability)\n\n"
        s += "| Key | Category | Reliability | Validations | Promoted | Insight |\n"
        s += "|-----|----------|-------------|-------------|----------|--------|\n"
        for item in top[:15]:
            promoted = "yes" if item["promoted"] else "—"
            s += f"| `{item['key']}` | {item['category']} | {item['reliability']:.0%} | {item['validations']} | {promoted} | {item['insight']} |\n"
        s += "\n"

    s += _source_files("lib/cognitive_learner.py", [
        "cognitive_insights.json",
        "cognitive_metrics.json",
    ])
    return s


# ── Stage 7: EIDOS ──────────────────────────────────────────────────

def _gen_eidos(d: dict, all_data: dict) -> str:
    s = _header(7, "EIDOS", "Episodic intelligence with mandatory predict-then-evaluate loop. Stores episodes (session-scoped), steps (prediction/outcome/evaluation triples), and distillations (extracted rules).", [3, 11], [8])

    db_status = "healthy" if d.get("db_exists") else "critical"
    s += _health_table([
        ("Database", "exists" if d.get("db_exists") else "MISSING", db_status),
        ("DB size", fmt_size(d.get("db_size", 0)), "healthy"),
        ("Episodes", fmt_num(d.get("episodes", 0)), "healthy"),
        ("Steps", fmt_num(d.get("steps", 0)), "healthy"),
        ("Distillations", fmt_num(d.get("distillations", 0)), "healthy"),
        ("Active episodes", fmt_num(d.get("active_episodes", 0)), "healthy"),
        ("Active steps", fmt_num(d.get("active_steps", 0)), "healthy"),
    ])

    # Recent distillations
    recent = d.get("recent_distillations", [])
    if recent:
        s += "## Recent Distillations\n\n"
        for i, dist in enumerate(recent, 1):
            dtype = dist.get("type", dist.get("distillation_type", "?"))
            statement = str(dist.get("statement", dist.get("text", "?")))[:150]
            confidence = dist.get("confidence", "?")
            s += f"{i}. **[{dtype}]** (confidence: {confidence})\n"
            s += f"   {statement}\n"
        s += "\n"
    elif not d.get("db_exists"):
        s += "## Status\n\neidos.db not found. EIDOS episodic learning is not active.\n\n"

    s += _source_files("lib/eidos/ (aggregator.py, distiller.py, store.py, models.py)", [
        "eidos.db",
        "eidos_active_episodes.json",
        "eidos_active_steps.json",
    ])
    return s


# ── Stage 8: Advisory ───────────────────────────────────────────────

def _gen_advisory(d: dict, all_data: dict) -> str:
    s = _header(8, "Advisory", "Just-in-time advice engine. Retrieves from Cognitive, EIDOS, Chips, and Mind. RRF fusion + cross-encoder reranking. Tracks implicit feedback (tool success/failure after advice).", [6, 7, 10], [9])

    followed_status = "healthy" if d.get("followed_rate", 0) > 40 else "warning"
    s += _health_table([
        ("Total advice given", fmt_num(d.get("total_advice_given", 0)), "healthy"),
        ("Followed", f"{fmt_num(d.get('total_followed', 0))} ({d.get('followed_rate', 0)}%)", followed_status),
        ("Helpful", fmt_num(d.get("total_helpful", 0)), "healthy"),
        ("Cognitive helpful rate", f"{d.get('cognitive_helpful_rate', 0):.1%}", "healthy"),
        ("Advice log entries", f"~{fmt_num(d.get('advice_log_count', 0))}", "healthy"),
    ])

    # By-source breakdown
    by_source = d.get("by_source", {})
    if by_source:
        s += "## Source Effectiveness\n\n"
        s += "| Source | Total | Helpful | Rate |\n"
        s += "|--------|-------|---------|------|\n"
        for src, stats in sorted(by_source.items(), key=lambda x: -x[1].get("total", 0)):
            total = stats.get("total", 0)
            helpful = stats.get("helpful", 0)
            rate = f"{helpful/max(total,1)*100:.1f}%" if total > 0 else "—"
            s += f"| {src} | {fmt_num(total)} | {fmt_num(helpful)} | {rate} |\n"
        s += "\n"

    # Recent advice
    recent = d.get("recent_advice", [])
    advice_items = [r for r in recent if "advice_texts" in r]
    if advice_items:
        s += "## Recent Advice Given\n\n"
        for i, entry in enumerate(advice_items[-10:], 1):
            tool = entry.get("tool", "?")
            texts = entry.get("advice_texts", [])
            sources = entry.get("sources", [])
            ts = entry.get("timestamp", "?")[:19]
            s += f"{i}. **{tool}** ({ts})\n"
            for j, txt in enumerate(texts[:3]):
                src = sources[j] if j < len(sources) else "?"
                s += f"   - [{src}] {txt[:120]}\n"
        s += "\n"

    s += "## Deep Dive\n\n"
    s += "- [[../../watchtower|Advisory Watchtower]] — full advisory packet analysis\n"
    s += "- [[../../packets/index|Packet Catalog]] — individual packet inspection\n\n"

    s += _source_files("lib/advisor.py", [
        "advisor/advice_log.jsonl",
        "advisor/effectiveness.json",
        "advisor/metrics.json",
        "advisor/retrieval_router.jsonl",
        "advisory_decision_ledger.jsonl",
    ])
    return s


# ── Stage 9: Promotion ──────────────────────────────────────────────

def _gen_promotion(d: dict, all_data: dict) -> str:
    s = _header(9, "Promotion", "Promotes high-reliability insights (80%+ reliability, 5+ validations) to project files: CLAUDE.md, AGENTS.md, TOOLS.md, SOUL.md. Rate-limited to once per hour.", [6, 8], [])
    s += _health_table([
        ("Total log entries", fmt_num(d.get("total_entries", 0)), "healthy"),
        ("Log size", fmt_size(d.get("log_size", 0)), "healthy"),
        ("Last activity", fmt_ago(d.get("mtime")), "healthy"),
    ])

    # Target distribution
    targets = d.get("target_distribution", {})
    if targets:
        s += "## Target Distribution (recent)\n\n"
        s += "| Target | Count |\n"
        s += "|--------|-------|\n"
        for t, count in sorted(targets.items(), key=lambda x: -x[1]):
            s += f"| {t} | {count} |\n"
        s += "\n"

    # Result distribution
    results = d.get("result_distribution", {})
    if results:
        s += "## Results (recent)\n\n"
        s += "| Result | Count |\n"
        s += "|--------|-------|\n"
        for r, count in sorted(results.items(), key=lambda x: -x[1]):
            s += f"| {r} | {count} |\n"
        s += "\n"

    # Recent promotions
    recent = d.get("recent_promotions", [])
    if recent:
        s += "## Recent Activity\n\n"
        s += "| Time | Key | Target | Result | Reason |\n"
        s += "|------|-----|--------|--------|--------|\n"
        for entry in recent:
            reason = entry.get("reason", "")[:40]
            s += f"| {entry['ts'][:19]} | `{entry['key']}` | {entry['target']} | {entry['result']} | {reason} |\n"
        s += "\n"

    s += _source_files("lib/promoter.py", [
        "promotion_log.jsonl",
    ])
    return s


# ── Stage 10: Chips ─────────────────────────────────────────────────

def _gen_chips(d: dict, all_data: dict) -> str:
    s = _header(10, "Chips", "Domain-specific intelligence modules. Each chip stores patterns, observations, and insights for its domain. Chips inject advice during advisory retrieval.", [3], [8])
    s += _health_table([
        ("Active chips", fmt_num(d.get("total_chips", 0)), "healthy"),
        ("Total size", fmt_size(d.get("total_size", 0)), "healthy"),
    ])

    chips = d.get("chips", [])
    if chips:
        s += "## Active Chips\n\n"
        s += "| Chip | Entries | Size | Last Updated |\n"
        s += "|------|---------|------|--------------|\n"
        for chip in chips:
            s += f"| **{chip['name']}** | ~{fmt_num(chip['count'])} | {fmt_size(chip['size'])} | {fmt_ago(chip.get('mtime'))} |\n"
        s += "\n"

        # Show recent entries per chip
        for chip in chips:
            if chip.get("recent"):
                s += f"### {chip['name']} — recent entries\n\n"
                for i, entry in enumerate(chip["recent"][:3], 1):
                    # Entries vary per chip, show what we can
                    text = str(entry)[:200]
                    s += f"{i}. `{text}`\n"
                s += "\n"

    s += _source_files("lib/chips/ (runtime.py, store.py)", [
        "chip_insights/*.jsonl",
    ])
    return s


# ── Stage 11: Predictions ───────────────────────────────────────────

def _gen_predictions(d: dict, all_data: dict) -> str:
    s = _header(11, "Predictions", "Tracks prediction-outcome pairs for surprise detection. Predictions made on pre_tool, outcomes recorded on post_tool. Surprise drives learning priority.", [3], [7])

    link_rate = 0
    if d.get("outcomes_count") and d.get("links_count"):
        link_rate = round(d["links_count"] / max(d["outcomes_count"], 1) * 100, 1)

    s += _health_table([
        ("Predictions", f"~{fmt_num(d.get('predictions_count', 0))}", "healthy"),
        ("Outcomes", f"~{fmt_num(d.get('outcomes_count', 0))}", "healthy"),
        ("Outcome links", f"~{fmt_num(d.get('links_count', 0))}", "healthy"),
        ("Link rate", f"{link_rate}%", "healthy" if link_rate > 10 else "warning"),
        ("Prediction state keys", fmt_num(d.get("prediction_state_keys", 0)), "healthy"),
    ])

    # Predictor config
    predictor = d.get("predictor", {})
    if predictor:
        s += "## Outcome Predictor\n\n"
        for k, v in predictor.items():
            s += f"- **{k}**: {v}\n"
        s += "\n"

    # Recent outcomes
    recent = d.get("recent_outcomes", [])
    if recent:
        s += "## Recent Outcomes\n\n"
        for i, entry in enumerate(recent[-10:], 1):
            text = str(entry)[:200]
            s += f"{i}. `{text}`\n"
        s += "\n"

    s += _source_files("hooks/observe.py (prediction logic)", [
        "predictions.jsonl",
        "outcomes.jsonl",
        "outcome_links.jsonl",
        "prediction_state.json",
        "outcome_predictor.json",
    ])
    return s


# ── Stage 12: Tuneables ─────────────────────────────────────────────

def _gen_tuneables(d: dict, all_data: dict) -> str:
    s = _header(12, "Tuneables", "Central configuration for all pipeline stages. Supports hot-reload. Available in both runtime (~/.spark/tuneables.json) and version-controlled (config/tuneables.json) locations.", [], [])

    s += _health_table([
        ("Source", d.get("source", "?"), "healthy" if d.get("source") != "none" else "critical"),
        ("Sections", fmt_num(len(d.get("sections", {}))), "healthy"),
        ("Last modified", fmt_ago(d.get("mtime")), "healthy"),
    ])

    sections = d.get("sections", {})
    if sections:
        s += "## Sections\n\n"
        s += "| Section | Keys | Sample Keys |\n"
        s += "|---------|------|-------------|\n"
        for name, info in sorted(sections.items()):
            keys = ", ".join(f"`{k}`" for k in info.get("keys", [])[:5])
            if info.get("key_count", 0) > 5:
                keys += ", ..."
            s += f"| **{name}** | {info.get('key_count', 0)} | {keys} |\n"
        s += "\n"

    s += "## Which Stages Each Section Configures\n\n"
    s += f"- `values` — {stage_link_from_stage(3)}, {stage_link_from_stage(7)}\n"
    s += f"- `semantic` — {stage_link_from_stage(8)}\n"
    s += f"- `promotion` — {stage_link_from_stage(9)}\n"
    s += f"- `advisor` — {stage_link_from_stage(8)}\n"
    s += f"- `meta_ralph` — {stage_link_from_stage(5)}\n"
    s += f"- `eidos` — {stage_link_from_stage(7)}\n"
    s += f"- `observatory` — Observatory auto-sync\n"
    s += "\n"

    s += _source_files("lib/tuneables_schema.py + lib/tuneables_reload.py", [
        "tuneables.json",
    ])
    s += f"\nVersion-controlled: `config/tuneables.json`\n"
    return s
