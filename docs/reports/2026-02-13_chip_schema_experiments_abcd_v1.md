# Chip Schema Experiments A/B/C/D v1

Date: 2026-02-13

## Scope

This pass did two things:

1. Cleaned active chip historical noise in `~/.spark/chip_insights` using:

```powershell
python scripts/compact_chip_insights.py \
  --keep-lines 200 \
  --max-age-days 14 \
  --prefer-schema \
  --active-only \
  --project-path "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence" \
  --archive \
  --apply
```

2. Ran schema-capture A/B/C/D benchmark matrix:

```powershell
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_experiment_plan_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 24 \
  --random-seed 20260212 \
  --out-prefix chip_schema_experiments_v1
```

Source artifact:
- `benchmarks/out/chip_schema_experiments_v1_report.json`

## Cleanup Outcome

Active chip files:
- `engagement-pulse.jsonl`: `204 -> 200`
- `social-convo.jsonl`: `113 -> 113`
- `x_social.jsonl`: `1171 -> 200`

Total:
- `1488 -> 513` rows (schema rows preserved: `3 -> 3`)

Archive backup created at:
- `~/.spark/archive/chip_insights/20260212T225344Z`

## A/B/C/D Results

| Experiment | Objective | Schema Payload Rate | Schema Statement Rate | Merge Eligible Rate |
|---|---:|---:|---:|---:|
| `A_schema_baseline` | `0.8000` | `100.00%` | `100.00%` | `0.00%` |
| `B_schema_evidence2` | `0.1000` | `0.00%` | `0.00%` | `0.00%` |
| `C_schema_strict_runtime` | `0.1000` | `0.00%` | `0.00%` | `0.00%` |
| `D_schema_strict_runtime_merge` | `0.1000` | `0.00%` | `0.00%` | `0.00%` |

Winner:
- `A_schema_baseline`

## Honest Assessment

- Schema system is usable and functioning under baseline gates.
- Raising `min_learning_evidence` to `2` currently collapses capture to zero in this matrix.
- This indicates the bottleneck is observer field richness, not the schema pipeline itself.

## Decision

Keep runtime defaults at baseline for now:
- `SPARK_CHIP_REQUIRE_LEARNING_SCHEMA=1`
- `SPARK_CHIP_MIN_LEARNING_EVIDENCE=1`

Do not promote strict evidence profile until observers are upgraded to consistently extract 2+ non-telemetry evidence fields.

## Next Improvement Targets

1. Upgrade observer extraction on active chips to emit at least two semantic evidence fields per event.
2. Re-run this exact matrix after extraction upgrades.
3. Promote `B`/`C`/`D` only if schema rates remain high and merge-eligible rate improves.
