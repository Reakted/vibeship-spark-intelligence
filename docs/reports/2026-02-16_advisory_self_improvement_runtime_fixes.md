# Advisory + Self-Improvement Runtime Fixes (2026-02-16)

## Scope

This report documents the advisory and self-improvement improvements implemented on **February 16, 2026** in Spark, including code changes, rationale, and benchmarked runtime impact.

Primary goals:

1. Stop auto-tuner no-op run churn while preserving observability.
2. Reduce low-signal advisory noise (especially telemetry-style self-awareness cautions).
3. Make Meta-Ralph quality-band gating robust against benchmark/test artifact pollution.
4. Validate behavior with live runtime checks and focused regression tests.

## Summary of Improvements

### 1) Auto-Tuner: no-op cycles now persist `last_run`

Problem observed:

- `auto_tuner.last_run` was only updated when boost changes were written.
- In no-change cycles, bridge could repeatedly re-run tuner logic after interval expiry.

Implementation:

- In `AutoTuner.run()`, non-dry-run no-change paths now call `_record_noop_run(...)`.
- `_record_noop_run(...)` writes:
  - `auto_tuner.last_run`
  - refreshed `source_effectiveness`
  - bounded tuning log entry with action `auto_tune_noop`
- In-memory config cache is refreshed after writes (`self._tuneables`, `self._config`).

Files:

- `lib/auto_tuner.py`
- `tests/test_eidos.py` (new test: no-op cycle advances last_run and prevents immediate rerun)

### 2) Advisor: suppression and ranking hygiene for noisy advisories

Problem observed:

- High-volume low-signal advisories were recurring, including telemetry-like struggle labels (e.g. `*_error tasks`) and transcript artifacts.
- Generic cautions such as "Read before Edit" could leak onto unrelated tool contexts.

Implementation:

- Added low-signal struggle detection:
  - filters `i struggle with ... _error tasks` style text
  - filters known telemetry/error tokens (`_error`, `mcp__`, `command_not_found`, etc.)
- Added transcript artifact detection:
  - catches phrase patterns like `said it like this:`, `another reply is:`, `user wanted:` and markdown/script artifacts.
- Added centralized drop filter in advice pipeline:
  - `advise()` now applies `_should_drop_advice(...)` before ranking.
- Added routing-aware suppression in drop filter:
  - suppress "Read before Edit" on tools other than `Read/Edit/Write`.
  - suppress the "one state" planning constraint outside planning tools.
- Added rank penalties (defensive fallback):
  - severe penalty for telemetry-style struggle text
  - moderate penalty for transcript/metadata patterns

Files:

- `lib/advisor.py`
- `tests/test_advisor_tool_specific_matching.py` (added coverage for telemetry filtering, ranking penalties, tool-aware suppression)

### 3) Advisory Gate: explicit telemetry-struggle suppression

Problem observed:

- Even when retrieved, certain `tool_X_error` style cautions should not emit as runtime guidance.

Implementation:

- Extended `_check_obvious_suppression(...)` with hard suppression for telemetry-style struggle cautions.

Files:

- `lib/advisory_gate.py`
- `tests/test_advisory_gate_suppression.py` (new test file)

### 4) Meta-Ralph: quality window hygiene for production gates

Problem observed:

- `meta_ralph_quality_band` could fail due to benchmark/test-heavy roast history dominating the quality-rate window denominator.

Implementation:

- Added quality-window filtering tuneables/defaults:
  - `QUALITY_WINDOW_EXCLUDE_TRACE_PREFIXES`
  - `QUALITY_WINDOW_EXCLUDE_TEXT_PREFIXES`
  - `QUALITY_WINDOW_TRACE_REPEAT_CAP`
- Added config loading from tuneables:
  - `quality_rate_exclude_trace_prefixes`
  - `quality_rate_exclude_text_prefixes`
  - `quality_rate_trace_repeat_cap`
- Updated `get_stats()` quality-rate window logic:
  - excludes duplicate verdicts (existing behavior)
  - excludes configured benchmark-like trace prefixes
  - caps per-trace contribution (filters only overflow, not full trace)
  - excludes configured text-prefix artifacts
- Added extra diagnostics in stats payload:
  - `quality_rate_window_filtered_trace_prefix`
  - `quality_rate_window_filtered_trace_churn`
  - `quality_rate_window_filtered_text_artifacts`

Files:

- `lib/meta_ralph.py`
- `tests/test_meta_ralph.py` (added quality window filtration/churn test)

## Live Runtime Validation

All commands run on **2026-02-16**.

### Production loop gates

Command:

- `python scripts/production_loop_report.py`

Result after changes:

- **READY (13/13 passed)**
- Notable values:
  - `strict_effectiveness=79.7%`
  - `quality_rate=14.3%`
  - `quality_samples=28`
  - `meta_ralph_quality_band` passed because enforcement is deferred until >= 50 samples.

### Auto-tuner no-op persistence check

Commands:

- `python -m lib.auto_tuner --status`
- `python -m lib.auto_tuner --force`
- `python -m lib.auto_tuner --status`

Observed:

- `last_run` advanced from `2026-02-10T09:11:08+00:00` to `2026-02-16T09:44:04+00:00` despite no boost deltas.
- Confirms no-op run metadata persistence is working.

### Utilization quick check

Command:

- `python tests/test_learning_utilization.py quick`

Observed:

- `Stored=239`, `Retrieved=500`, `Acted On=499`, `Effectiveness=84.4%`, `Grade=A`.

### Pipeline health quick check

Command:

- `python tests/test_pipeline_health.py quick`

Observed:

- All checks passed.
- Bridge heartbeat fresh, queue active, Meta-Ralph and cognitive storage healthy.

### Integration status

Command:

- `python -m lib.integration_status`

Observed:

- Healthy system status.
- Advice tracking and follow/helpful counters present and consistent.

## Test Validation

Focused suites run after implementation:

- `python -m pytest -q tests/test_eidos.py::TestAutoTuner tests/test_advisor_tool_specific_matching.py tests/test_advisory_gate_suppression.py tests/test_meta_ralph.py`
- `python -m pytest -q tests/test_advice_id_stability.py tests/test_advisory_engine_dedupe.py tests/test_advisory_self_review.py tests/test_advisor_effectiveness.py tests/test_production_loop_gates.py`

Outcome:

- `32 passed` in focused change set.
- `24 passed` in advisory/regression gate suite.

## Caveats and Follow-ups

1. Quality-band enforcement currently deferred:
   - Current `quality_rate_window_samples=28` (< 50), so band check is non-enforced by design.
2. Existing historical advisory noise in logs remains:
   - Suppression/ranking changes improve new traffic; old rows remain in historical files unless cleaned separately.
3. Additional normalization opportunity:
   - If desired, legacy noisy self-awareness insights can be migrated/pruned in persisted cognitive stores.

## Operational Guidance

If you want stricter/looser Meta-Ralph quality-window filtering, tune:

- `meta_ralph.quality_rate_exclude_trace_prefixes`
- `meta_ralph.quality_rate_exclude_text_prefixes`
- `meta_ralph.quality_rate_trace_repeat_cap`

Recommended initial policy:

- Keep trace-prefix exclusions for benchmark/test traces.
- Keep per-trace cap low (e.g. 4-8) to prevent a single harness trace from dominating window quality.

## Changed Files

- `lib/auto_tuner.py`
- `lib/advisor.py`
- `lib/advisory_gate.py`
- `lib/meta_ralph.py`
- `tests/test_eidos.py`
- `tests/test_advisor_tool_specific_matching.py`
- `tests/test_advisory_gate_suppression.py`
- `tests/test_meta_ralph.py`

---

Prepared on: **2026-02-16**
