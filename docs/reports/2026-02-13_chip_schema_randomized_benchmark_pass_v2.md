# Chip Schema Randomized Benchmark Pass v2

Date: 2026-02-13
Scope: trigger tightening + randomized schema benchmarking + merge-activation matrix.

## Changes Implemented

1. Reduced broad chip trigger surfaces on active X chips:
- `chips/social-convo.chip.yaml`
- `chips/engagement-pulse.chip.yaml`
- `chips/x-social.chip.yaml`

2. Added randomized robustness runner:
- `scripts/run_chip_schema_multiseed.py`
- reports winner stability and promotion pass rate over multiple seeds.

3. Strengthened promotion gate:
- `scripts/run_chip_schema_experiments.py`
- added optional candidate floors:
  - `min_candidate_non_telemetry`
  - `min_candidate_schema_statement`
  - `min_candidate_merge_eligible`

4. Added merge-activation benchmark plan:
- `benchmarks/data/chip_schema_merge_activation_plan_v1.json`
- plan-level `min_total_score=0.35` to avoid false zero-merge blind spot.

5. Added docs updates and tests:
- `tests/test_run_chip_schema_multiseed.py`
- expanded `tests/test_run_chip_schema_experiments.py`

## Validation

- `python -m pytest -q tests/test_run_chip_schema_experiments.py tests/test_run_chip_schema_multiseed.py tests/test_run_chip_observer_policy.py tests/test_chips_runtime_filters.py tests/test_chip_merger.py tests/test_run_chip_learning_diagnostics.py tests/test_compact_chip_insights.py`
- Result: `26 passed`

## Bench Results

### Observer-policy and diagnostics

- `chip_learning_diagnostics_active_observer_v5`: `rows=513`, `telemetry_rate=97.86%`, `merge_eligible=2`
- `chip_observer_policy_v2`: `disable=4`, `keep=4`, `neutral=1`

### Prior schema plans under strict merge threshold

- `chip_schema_experiments_multiseed_v3`: baseline `A` stable winner (`win_rate=85.71%`), promotion pass for `B` = `0%`.
- `chip_schema_mode_variations_multiseed_v2`: `M2` won objective/coverage but promotion for `M1` against `M0` remained `0%`.
- Root issue: `merge_eligible_mean` stayed `0.0` across arms under strict total-score threshold.

### Merge-activation matrix (new)

- `chip_schema_merge_activation_v1`: winner `R3_two_evidence_relaxed_merge` with high coverage and non-zero merge.
- `chip_schema_merge_activation_multiseed_v2`:
  - candidate `R3` vs baseline `R0` promotion pass rate: `100%` (7/7 seeds)
  - `R3`: objective mean `0.9274`, coverage mean `100%`, merge-eligible mean `0.6369`
  - `R0`: objective mean `0.9116`, coverage mean `64.88%`, merge-eligible mean `0.9971`

## Honest Assessment

1. Trigger tightening helped reduce obvious broad activations, but observer quality remains the main leverage point.
2. Single-seed ranking was not stable enough for promotion decisions; multi-seed was necessary.
3. Strict benchmark thresholds were masking merge dynamics (false zero-merge interpretation).
4. Merge-activation profile `R3` is currently the strongest promotable candidate by robust gate criteria.

## Promotion Decision

- Promote benchmark profile target: `R3_two_evidence_relaxed_merge` (against `R0_baseline_safe`) for chip schema/merge tuning track.
- Keep strict floor gate in place (`non_telemetry`, `schema_statement`, `merge_eligible`) for all future promotions.

## Next Pass

1. Apply `R3`-equivalent runtime + merge thresholds in controlled runtime window.
2. Run post-change 24h diagnostics window and compare:
- chip-level/unknown share
- schema statement rate
- merge eligible rate
- downstream advisory trace-bound actionability

