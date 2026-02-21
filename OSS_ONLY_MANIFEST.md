# OSS-only Manifest (Spark Public Launch)

Date: Saturday, 2026-02-21  
Branch context: `vibeship-spark-intelligence` public cleanup for Spark OSS launch

## 1) What is public in this repo

The repository now ships only the Spark OSS core needed for:
- local reasoning loops
- OpenClaw integration
- Claude/Cursor and compatible agent workflows
- developer experimentation and contribution

Included at a high level:
- Core runtime and orchestration modules under `spark/`, `lib/`, `scripts/`, `extensions/`, `hooks/`, `templates/`, `prompts/`, and `adapters/`
- Core execution entry points (`sparkd.py`, `spark_pulse.py`, `spark_watchdog.py`, `bridge_worker.py`, `mind_server.py`, `tracer_*`)
- Public docs and operating guides in `docs/` and repo root
- Public packaging metadata and tooling references (`pyproject.toml`, `package.json`, `package-lock.json`)
- Non-sensitive examples and tests

## 2) What is intentionally excluded or inert

Excluded from public OSS runtime:
- X/social/moltbook and other external social automations
- All benchmark/reporting outputs and tuning artifacts
- Trace HUD runtime and runtime-only instrumentation modules
- Ephemeral local state and runtime scratch directories
- Premium chip behavior is present as files but non-operational by default in OSS

## 3) Removed for launch hygiene

These paths are removed from the repo and should not be reintroduced:
- `benchmarks/`
- `trace_hud/`
- `logs/`
- `build/`
- `dist/`
- `docs/reports/`
- `__pycache__/` and language/runtime cache dirs
- `.pytest_cache/`
- `.spark/`
- `vibeship_spark.egg-info/`
- `CORE_SELF_EVOLUTION_PROMPT.md`
- `docs/security/SECRETS_AND_RELEASE_CHECKLIST.md`
- `docs/token/TOKEN_LAUNCH_COMMS_AND_RISK.md`
- `sandbox/spark_sandbox/report.json`
- `sandbox/spark_sandbox_baseline.json`
- `sandbox/spark_sandbox_diff.json`
- Any unmasked launch-risk docs and local diagnostics generated for private runs

## 4) Required launch docs (read-first)

Use this sequence first for release understanding:
- `README.md`
- `docs/LAUNCH_DOCUMENTATION_MAP.md`
- `docs/DOCS_INDEX.md`
- `docs/OSS_BOUNDARY.md`
- `Intelligence_Flow.md`
- `Intelligence_Flow_Map.md`
- `TUNEABLES.md`
- `OPENCLAW_IMPLEMENTATION_TASKS.md`
- `SPARK_LEARNING_GUIDE.md`
- `PRODUCTION_READINESS.md`

## 4.1) Agent-first docs map

The quickest OSS onboarding stack:
- `README.md` and `docs/OSS_BOUNDARY.md` for scope and limits
- `docs/LAUNCH_DOCUMENTATION_MAP.md` and `docs/DOCS_INDEX.md` for where each topic lives
- `Intelligence_Flow.md` and `Intelligence_Flow_Map.md` for inference/advisor wiring
- `TUNEABLES.md` for operational knobs and expected behaviors
- `OPENCLAW_IMPLEMENTATION_TASKS.md` + `docs/openclaw/` for OpenClaw bridge details
- `SPARK_LEARNING_GUIDE.md` for tuning and maintenance
- `PRODUCTION_READINESS.md` for hardening and launch checks

## 5) Premium-capability summary

- Chips module files are retained for architectural completeness.
- OSS launch keeps chip execution disabled/inert by default.
- Premium builds enable chip runtime with documented feature flags only.

## 6) Public-only policy for future contributors

- If a file references internal/private operations, personal reports, social automation, or live credentials, it should be moved under a premium/internal package or deleted before release.
- If in doubt, prefer deleting generated outputs and keeping source-only assets.
- Keep this manifest as the source of truth for what ships publicly.
