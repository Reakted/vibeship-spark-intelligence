# Experiment: Phase 2 — Two-Layer Completion Gate (Synthetic + Live)
Date: 2026-02-11
Owner: Spark

## Hypothesis
Marking runs as `provisional` unless live validation is passed will reduce false-positive "done" states.

## Change
- Added `_compute_completion_gate(...)` in `spark_forge/pipeline.py`.
- New run output block: `completion_gate` with:
  - `status`: `confirmed | provisional | failed`
  - `synthetic_pass`
  - `live_validation_required`
  - `live_validation_passed`
- Extended follow-up schema to include `live_validation_passed` boolean.

## Validation
- Compile check passed (`py_compile pipeline.py followup.py`).
- Real-use metric pending: provisional->confirmed conversion and reopen-after-pass rate.

## Result
- Shipped in `spark-forge` commit `c56ff40`.

## Decision
- Keep and monitor in repeated live task batches.
