<p align="center">
  <a href="https://spark.vibeship.co"><img src="header.png" alt="Spark Intelligence" width="100%"></a>
</p>
<p align="center">
  <a href="https://github.com/vibeforge1111/vibeship-spark-intelligence/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/runs-100%25_local-green?style=flat-square" alt="Local">
  <img src="https://img.shields.io/badge/platform-Win%20%7C%20Mac%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

---

Learns constantly. Adapts with your flow.
Runs 100% on your machine as a local AI companion that turns past work into future-ready behavior.
It is designed to be beyond a learning loop.

`You do work` -> `Spark captures memory` -> `Spark distills and transforms it` -> `Spark delivers advisory context` -> `You act with better context` -> `Outcomes re-enter the loop`

## What is Spark?

Spark Intelligence is a self-evolving AI companion designed to grow smarter through use.

It is:
- Not a chatbot.
- Not a fixed rule set.
- A living intelligence runtime that continuously converts experience into adaptive operational behavior, not just stored memory.

The goal is to keep context, patterns, and practical lessons in a form that your agent can actually use at the right moment.

## Beyond a Learning Loop: Intelligence Operating Flow

- Capture: hooks and events from your agent sessions are converted into structured memories.
- Distill: noisy data is filtered into reliable, action-oriented insights.
- Transform: high-value items are shaped for practical reuse (prioritized by reliability, context match, and usefulness).
- Store: distilled wisdom is persisted and versioned in local memory stores.
- Act: advisory and context updates are prepared for the right point in workflow.
- Guard: gating layers check quality, authority, cooldown, and dedupe before any advisory is surfaced.
- Learn: outcomes and follow-through are fed back to refine future recommendations.

## Install

```bash
git clone https://github.com/vibeforge1111/vibeship-spark-intelligence
cd vibeship-spark-intelligence
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .[services]
```

If your system uses PEP 668 / external package management, this avoids the
`externally-managed-environment` error:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[services]
```

Or run directly with editable install:

```bash
python -m pip install vibeship-spark-intelligence[services]
spark up
```

## Quick Start

```bash
# Check health
spark health

# View what Spark has learned
spark learnings
```

Windows: run `start_spark.bat` from the repo root.

Lightweight mode (core only, no dashboards): `spark up --lite`

## Connect Your Agent

Spark works with any coding agent that supports hooks or event capture.

| Agent | Integration | Guide |
|-------|------------|-------|
| **Claude Code** | Hooks (PreToolUse, PostToolUse, UserPromptSubmit) | `docs/claude_code.md` |
| **Cursor / VS Code** | tasks.json + emit_event | `docs/cursor.md` |
| **OpenClaw** | Session JSONL tailer | `docs/openclaw/` |

## What You Get

- **Self-evolving companion behavior** — adapts from your sessions instead of staying static.
- **Signal capture** — hooks + event ingestion for tool actions, prompts, and outcomes.
- **Distillation pipeline** — low-quality/raw observations are filtered out before storage.
- **Transformation layer** — converts insight candidates into actionable advisory-ready forms.
- **Advisory delivery** — pre-tool guidance ranked across retrieval sources with cool-down and dedupe.
- **EIDOS loop** — prediction → outcome → evaluation for continuous quality updates.
- **Domain chips** — pluggable expertise modules that can specialize behavior.
- **Dashboards** — Spark Pulse and Meta-Ralph for observability and tuning.
- **CLI** — `spark status`, `spark learnings`, `spark promote`, `spark up/down`, and more.
- **Hot-reloadable config** — tuneables with schema checks and live behavior shifts.

## Architecture

```
Your Agent (Claude Code / Cursor / OpenClaw)
  -> hooks capture events
  -> queue -> bridge worker -> pipeline
  -> quality gate (Meta-Ralph) -> cognitive learner
  -> distillation -> transformation -> advisory packaging
  -> pre-tool advisory surfaced + context files refreshed
```

## Obsidian Observatory

Spark ships with an [Obsidian](https://obsidian.md) integration that turns the entire intelligence pipeline into a human-readable vault you can browse, search, and query.

### What you get

- **Flow Dashboard** — Mermaid diagram of all 12 pipeline stages with live metrics
- **Stage Detail Pages** — per-stage health, recent activity, upstream/downstream links
- **Explorer** — browse individual cognitive insights, EIDOS episodes, distillations, Meta-Ralph verdicts, promotions, advisory decisions, feedback signals, routing, and tuneable evolution
- **Canvas View** — spatial layout of the full pipeline (Obsidian Canvas)
- **Dataview Dashboard** — pre-built queries for daily monitoring (requires Dataview plugin)
- **Tuneable Impact Analysis** — cross-references parameter changes with follow-rate outcomes

### Quick start

```bash
# Generate the observatory (creates ~465 markdown files in < 1 second)
python scripts/generate_observatory.py --force --verbose

# Open the vault in Obsidian:
# File > Open vault > Open folder as vault > select the generated vault directory
```

The observatory auto-syncs every 120 seconds when the pipeline is running. No manual regeneration needed.

### What's inside

```
Spark-Intelligence-Observatory/
  _observatory/
    flow.md              # Main dashboard + Mermaid pipeline diagram
    flow.canvas          # Spatial Canvas view
    stages/              # 12 stage detail pages
    explore/             # 10 browsable data stores
      cognitive/         # Individual insights (with detail pages)
      distillations/     # EIDOS distillations (with detail pages)
      episodes/          # EIDOS episodes + steps (with detail pages)
      verdicts/          # Meta-Ralph verdicts (with detail pages)
      decisions/         # Advisory emit/suppress/block decisions
      feedback/          # Implicit feedback (followed/ignored signals)
      routing/           # Retrieval router decisions
      tuning/            # Tuneable evolution + impact analysis
      promotions/        # Promotion log
      advisory/          # Advisory effectiveness
  Dashboard.md           # Dataview dashboard (safe to customize)
  packets/               # Advisory packets (existing)
  watchtower.md          # Advisory watchtower (existing)
```

### Configuration

All observatory settings are in the `observatory` section of `tuneables.json`:

```json
{
  "observatory": {
    "enabled": true,
    "auto_sync": true,
    "sync_cooldown_s": 120,
    "vault_dir": "path/to/your/vault",
    "generate_canvas": true,
    "max_recent_items": 20,
    "explore_cognitive_max": 200,
    "explore_episodes_max": 100
  }
}
```

Full guide: `docs/OBSIDIAN_OBSERVATORY_GUIDE.md`

## Documentation

- **5-minute start**: `docs/GETTING_STARTED_5_MIN.md`
- **Full setup**: `docs/QUICKSTART.md`
- **Obsidian Observatory**: `docs/OBSIDIAN_OBSERVATORY_GUIDE.md`
- **Docs index**: `docs/DOCS_INDEX.md`
- **Website**: [spark.vibeship.co](https://spark.vibeship.co)
- **Contributing**: `CONTRIBUTING.md` (local setup, PR flow, and safety expectations)

## Responsible Use

This is a self-evolving system. If you are planning a public release or high-autonomy deployment:
- Read first: `docs/AI_MANIFESTO.md`
- Read first: https://aimanifesto.vibeship.co/
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- `docs/security/THREAT_MODEL.md`
- `SECURITY.md` for vulnerability reporting

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<p align="center">
  <sub>Built by <a href="https://vibeship.com">Vibeship</a></sub>
</p>
