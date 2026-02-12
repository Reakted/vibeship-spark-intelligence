# Chip Observer Policy and Variation Pass v1

Date: 2026-02-13

## Scope

This pass executed three requested actions together:

1. Reduced `chip_level/unknown` dominance risk by tightening broad triggers in active chips.
2. Added a per-observer keep/disable policy loop using KPI trends across 2-3 windows.
3. Enforced schema benchmark promotion gate: candidate `B` only promotes if it beats `A` on both objective and coverage.

Also added schema mode variation testing so multiple chip methodologies can be compared honestly.

## Implemented Changes

### Trigger/observer tightening (active chips)

- `chips/social-convo.chip.yaml`
  - removed broad generic events (`post_tool`, `user_prompt`, etc.)
  - narrowed broad observer triggers (emotional/conversation psychology)
- `chips/engagement-pulse.chip.yaml`
  - removed broad generic events
- `chips/x-social.chip.yaml`
  - narrowed broad pattern triggers
  - removed broad generic events
  - replaced wildcard tool contexts with focused context terms

### Runtime observer policy support

- `lib/chips/runtime.py`
  - added observer policy file support: `~/.spark/chip_observer_policy.json`
  - supports block by `chip/observer` and by observer name
  - integrated into observer suppression path

### Observer policy generator

- New: `scripts/run_chip_observer_policy.py`
  - reads last N diagnostics windows
  - scores observer KPI trends
  - outputs keep/disable candidates
  - optional `--apply` writes runtime policy file

### Schema experiment promotion gate

- `scripts/run_chip_schema_experiments.py`
  - added promotion gate logic and report fields
  - gate condition: candidate beats baseline on both objective and coverage

## Test Validation

Executed:

```powershell
python -m pytest -q tests/test_run_chip_schema_experiments.py tests/test_run_chip_observer_policy.py tests/test_chips_runtime_filters.py tests/test_chip_merger.py tests/test_run_chip_learning_diagnostics.py tests/test_compact_chip_insights.py
```

Result: `23 passed` (known non-blocking pytest temp cleanup permission warning persists).

## Benchmark Runs

### A/B/C/D schema benchmark with promotion gate

Command:

```powershell
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_experiment_plan_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 24 \
  --random-seed 20260212 \
  --promotion-baseline-id A_schema_baseline \
  --promotion-candidate-id B_schema_evidence2 \
  --out-prefix chip_schema_experiments_v5
```

Result:
- Winner: `A_schema_baseline` (`objective=0.8083`)
- Promotion gate: `FAIL`
  - objective delta (`B-A`) = `-0.0125`
  - coverage delta (`B-A`) = `-0.0416`

Decision:
- keep `A` as operating profile.
- do not promote `B` yet.

### Schema mode variation matrix

Command:

```powershell
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_mode_variations_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 24 \
  --random-seed 20260212 \
  --promotion-baseline-id M0_baseline_schema_safe \
  --promotion-candidate-id M1_two_evidence_balanced \
  --out-prefix chip_schema_mode_variations_v1
```

Result:
- Winner: `M2_two_evidence_low_conf` (`objective=0.9000`)
- Gate (`M1` vs `M0`): `FAIL`

Interpretation:
- Variation testing found a potentially stronger mode (`M2`) worth targeted follow-up.
- The strict default candidate (`M1`) still does not beat baseline on both required axes.

## Observer Policy Rollout

Command:

```powershell
python scripts/run_chip_observer_policy.py \
  --report-glob "benchmarks/out/chip_learning_diagnostics_active_observer_v*_report.json" \
  --windows 3 \
  --min-windows 2 \
  --min-rows-total 50 \
  --disable-max-schema-statement-rate 0.02 \
  --disable-min-telemetry-rate 0.80 \
  --keep-min-schema-statement-rate 0.20 \
  --keep-min-merge-eligible 1 \
  --out-prefix chip_observer_policy_v1 \
  --apply
```

Applied policy summary:
- disable: `4`
- keep: `4`
- neutral: `1`

Disabled observers (policy):
- `engagement-pulse/chip_level`
- `engagement-pulse/unknown`
- `social-convo/chip_level`
- `x-social/chip_level`

Disabled observer names:
- `chip_level`
- `unknown`

Policy file:
- `~/.spark/chip_observer_policy.json`

Runtime reload:
- restarted `sparkd`, `bridge_worker`, `openclaw_tailer`
- health check: `sparkd /health = ok`

## Current Operating Decision

1. Keep baseline `A_schema_baseline` live.
2. Keep promotion gate strict: no promotion unless `B` beats `A` on both objective and coverage.
3. Keep observer policy loop active every 2-3 windows.
4. Continue variation matrix runs to discover better modes, then validate candidate against production gate.

## Next Iteration

1. Targeted observer extraction upgrades for the top neutral/weak observers from policy report.
2. Re-run diagnostics + policy + schema matrix.
3. If `M2` keeps outperforming, run `M2 vs A` directly under same gate criteria and promote only if it passes.
