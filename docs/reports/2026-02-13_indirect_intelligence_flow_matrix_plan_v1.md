# Indirect Intelligence Flow Matrix Plan v1

Date: 2026-02-13
Repo: `vibeship-spark-intelligence`
Mode: no new features, tuneables/process optimization only

## Objective

Improve advisory quality indirectly by improving upstream signal systems:
1. Distillation quality (`chip_merge`).
2. Observer telemetry policy quality.
3. Retrieval gate stability.
4. Trace attribution integrity.

All experiments are A/B/C/D with the current restored balanced profile as control.

## Baseline Guardrails

Any candidate arm is promotable only if all hold:
- advisory realism objective >= control - 0.02
- harmful_emit_rate <= 0.10
- critical_miss_rate <= 0.10
- trace_bound_rate >= 0.85
- no regression in memory retrieval non-empty rate

## Matrix 1: Distillation Quality

Tuneables section: `chip_merge`

Arms:
- A control:
  - current `chip_merge` values
- B quality_tight:
  - `min_cognitive_value=0.35`
  - `min_actionability=0.25`
  - `min_transferability=0.25`
  - `min_statement_len=30`
- C anti_churn:
  - `duplicate_churn_ratio=0.70`
  - `duplicate_churn_cooldown_s=3600`
- D balanced_tight:
  - combine B + C with `duplicate_churn_ratio=0.75`

Per-arm benchmarks:
- `scripts/run_chip_learning_diagnostics.py`
- `scripts/advisory_controlled_delta.py`
- `benchmarks/advisory_realism_bench.py` (baseline profile)

## Matrix 2: Observer Policy Thresholds

Policy file: `~/.spark/chip_observer_policy.json`

Arms:
- A control thresholds:
  - disable telemetry min `0.75`
  - keep schema statement min `0.20`
- B aggressive_disable:
  - disable telemetry min `0.65`
- C conservative_disable:
  - disable telemetry min `0.85`
- D stricter_keep_quality:
  - keep schema statement min `0.30`

Per-arm benchmarks:
- `scripts/run_chip_observer_policy.py --apply`
- `scripts/run_chip_learning_diagnostics.py`
- `benchmarks/advisory_realism_bench.py` (baseline profile)

## Matrix 3: Retrieval Gate Stability

Tuneables sections: `semantic`, `retrieval.overrides`

Arms:
- A control:
  - `min_similarity=0.58`
  - `min_fusion_score=0.50`
  - `retrieval.overrides.lexical_weight=0.30`
- B mild_relax:
  - `min_similarity=0.55`
  - `min_fusion_score=0.45`
- C medium_relax:
  - `min_similarity=0.52`
  - `min_fusion_score=0.40`
- D mild_relax_plus_lexical:
  - B + `retrieval.overrides.lexical_weight=0.35`

Per-arm benchmarks:
- `benchmarks/memory_retrieval_ab.py`
- `benchmarks/advisory_realism_bench.py` (baseline profile)

## Matrix 4: Trace Attribution Integrity

Tuneables section: `meta_ralph`

Arms:
- A control:
  - `attribution_window_s=1200`
  - `strict_attribution_require_trace=true`
- B tighter_window:
  - `attribution_window_s=900`
  - `strict_attribution_require_trace=true`
- C wider_window:
  - `attribution_window_s=1800`
  - `strict_attribution_require_trace=true`
- D diagnostic_loose_trace:
  - `attribution_window_s=1200`
  - `strict_attribution_require_trace=false` (diagnostic arm only)

Per-arm benchmarks:
- `scripts/advisory_controlled_delta.py`
- `benchmarks/advisory_realism_bench.py` (baseline profile)

## Execution Notes

- Run all arms with tuneables backup+restore safety.
- Persist per-arm artifacts with unique prefixes.
- Generate machine-readable summary JSON and final markdown scorecard.
- Restore baseline tuneables and baseline observer policy after matrix run.
