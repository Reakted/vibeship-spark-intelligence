# Experiment: Phase 4b — Refinement Regression Guardrail + Best-Report Rollback
Date: 2026-02-11
Owner: Spark

## Hypothesis
If refinement quality regresses sharply (score drop or critical severity), stopping the loop and preserving best prior output will improve stability and prevent late-iteration collapse.

## Change
- Updated `spark-forge/src/spark_forge/cli.py` training/run loop:
  - Track `best_report` during iterative refinement.
  - Guardrail trigger when either:
    - severity becomes `critical`, or
    - score drops by >= 1.0 vs previous iteration.
  - On trigger:
    - stop further refinement iterations,
    - preserve best prior run as `forge_run_best_<session_id>.json`.

## Validation
- `python -m py_compile src/spark_forge/cli.py` passed.

## Result
- Shipped in `spark-forge` commit `1ce9d2b`.

## Decision
- Keep and verify in next measured batch for reduced collapse behavior.
