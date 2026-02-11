# Experiment: Phase 2d — Live Validation Fallback Heuristic
Date: 2026-02-11
Owner: Spark

## Hypothesis
When follow-up omits/underspecifies `live_validation_passed`, a conservative fallback can reduce noisy provisional statuses while preserving safety.

## Change
- Updated completion gate in `spark-forge/src/spark_forge/pipeline.py`.
- Added heuristic live-validation pass when ALL hold:
  - synthetic pass is true
  - overall score >= 8.0
  - severity in {none, minor}
  - no failure patterns
- Added `live_validation_source` field: `explicit | heuristic | none`.

## Validation
- `py_compile` passed for updated pipeline module.

## Result
- Shipped in `spark-forge` commit `14e8b27`.

## Decision
- Keep and monitor provisional->confirmed behavior trend.
