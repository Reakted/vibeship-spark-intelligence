# OpenClaw Integration Changelog

This log tracks Spark x OpenClaw integration changes that should be easy to audit later.

## 2026-02-16

### Added

- Introduced canonical local path and sensitivity map:
  - `docs/OPENCLAW_PATHS_AND_DATA_BOUNDARIES.md`
- Introduced structured integration backlog:
  - `docs/openclaw/INTEGRATION_BACKLOG.md`
- Added OpenClaw config snippet/runbook reference:
  - `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`
- Added audit tooling + workflow docs:
  - `scripts/openclaw_integration_audit.py`
  - `docs/openclaw/OPERATIONS_WORKFLOW.md`

### Initial observed operational gaps

- OpenClaw `2026.2.15` is installed, but the active config does not explicitly set:
  - `agents.defaults.subagents.maxSpawnDepth`
  - `agents.defaults.subagents.maxChildrenPerAgent`
  - `cron.webhook` / `cron.webhookToken`
  - explicit `llm_input` / `llm_output` integration wiring
- Secrets are still present as plain values in local OpenClaw config and require hardening.

### Completed follow-up (same day)

- Hardened local OpenClaw config:
  - moved credential fields to env references,
  - set `cron.webhook` and `cron.webhookToken`,
  - set subagent policy (`maxSpawnDepth=2`, `maxChildrenPerAgent=3`).
- Added plugin-based hook telemetry capture:
  - `extensions/openclaw-spark-telemetry/`
  - captures `llm_input` + `llm_output` to redacted local spool JSONL.
- Added hook spool ingestion to Spark adapter:
  - `adapters/openclaw_tailer.py --hook-events-file ...`
- Updated integration audit detection to recognize plugin-based hook wiring.
- Added schema-transition KPI view:
  - quality GAUR now gated on `schema_version >= 2`,
  - side-by-side `gaur_all` and `feedback_schema_v2_ratio` for transition monitoring.

### Remaining next steps

1. Validate telemetry joins and strict attribution rates after sustained runtime traffic.
2. Add weekly strict-quality rollup report with lineage slices.
3. Keep each integration change as a separate commit for rollback clarity.

### Audit artifact

- Generated report:
  - `docs/reports/openclaw/2026-02-16_160848_openclaw_integration_audit.md`
  - `docs/reports/openclaw/2026-02-16_160848_openclaw_integration_audit.json`
  - `docs/reports/openclaw/2026-02-16_163115_openclaw_integration_audit.md`
  - `docs/reports/openclaw/2026-02-16_163115_openclaw_integration_audit.json`
