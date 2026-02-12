# Chip Best-Use Findings and Outlook v1

Date: 2026-02-13

## Executive Finding

Chips are now most valuable as **upstream evidence extractors** for memory/distillation quality, not as direct high-volume advisory emitters.

Practical best-use path:
1. `chips -> schema payloads`
2. `schema payloads -> distilled learnings`
3. `distilled learnings -> advisory retrieval/selection`

## What We Changed in This Pass

1. Observer evidence robustness upgrades
- `lib/chips/runtime.py`
  - Numeric short-form evidence (for non-telemetry keys like `snapshot_age`, `likes`, `replies`) is now accepted.
- `chips/social-convo.chip.yaml`
  - Added extraction rules on `reply_effectiveness` for outcome + engagement counts.
- `chips/engagement-pulse.chip.yaml`
  - Added extraction for `engagement_snapshot` and `engagement_surprise` fields.
- `chips/x-social.chip.yaml`
  - Added extraction for `social_learning` confidence and sample-size signals.

2. Diagnostics observability upgrades
- `scripts/run_chip_learning_diagnostics.py`
  - Added `--active-only`, `--project-path`, `--max-age-days`, `--observer-limit`.
  - Added observer KPI section with per-observer:
    - schema payload rate
    - schema statement rate
    - statement yield
    - merge-eligible count
    - non-telemetry rate

3. Schema experiment scoring hardening
- `scripts/run_chip_schema_experiments.py`
  - Added `capture_coverage` (`insights_emitted / events_requested`) to objective.
- `benchmarks/data/chip_schema_experiment_plan_v1.json`
  - Reweighted objective to penalize under-emitting strict profiles.

## Current Results

### A/B/C/D schema matrix (`chip_schema_experiments_v4`)

Source: `benchmarks/out/chip_schema_experiments_v4_report.json`

- `A_schema_baseline`: objective `0.8125`, coverage `70.83%`
- `B_schema_evidence2`: objective `0.7917`, coverage `63.89%`
- `C_schema_strict_runtime`: objective `0.0500`, coverage `0.00%`
- `D_schema_strict_runtime_merge`: objective `0.0500`, coverage `0.00%`

Winner: `A_schema_baseline`

Interpretation:
- `B` is now viable (no longer collapsed), proving the system can move toward stricter evidence.
- `C/D` are currently over-strict for real operating coverage.

### Active-only observer diagnostics (`chip_learning_diagnostics_active_observer_v3`)

Source: `benchmarks/out/chip_learning_diagnostics_active_observer_v3_report.json`

- rows analyzed: `513`
- statement yield: `21.05%`
- schema payload rate: `0.58%`
- schema statement rate: `0.58%`

Top schema-producing observers in fresh window are explicit domain observers (not chip-level fallbacks).

## Best Use of Chips (Operational Rule)

Keep chips focused on:
- domain evidence capture
- observer-level schema quality
- distillation input quality

Do not optimize chips for:
- raw advisory volume
- telemetry-heavy broad triggers

Promotion criterion for chip changes:
- higher schema statement rate
- higher capture coverage
- stable or better advisory outcome metrics
- no harmful/noise regression

## Future Outlook

Near-term (next 1-2 passes):
1. Raise `B_schema_evidence2` coverage above baseline through targeted observer extraction improvements.
2. Reduce chip-level/unknown observer rows by tightening trigger specificity and observer routing.
3. Promote `min_learning_evidence=2` only when it wins on both objective and coverage.

Mid-term:
1. Add observer auto-pruning policy (disable observers that stay low schema-yield over multiple windows).
2. Use observer KPI deltas as auto-tuner inputs.
3. Feed only schema-valid chip learnings into high-priority memory slots.

Long-term:
- Chips become a domain-aware evidence substrate for advisory wisdom, with strict quality gates and low telemetry noise.

## Immediate Next Actions

1. Tighten chip-level fallback contribution by reducing generic trigger fan-in for active chips.
2. Add explicit allowlist/denylist per observer for evidence keys used in schema payloads.
3. Re-run matrix (`A/B/C/D`) after each observer update and only promote when coverage and objective both improve.
