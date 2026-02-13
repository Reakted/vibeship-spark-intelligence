# Strict Canary vs Restored Optimization Pass v1

Date: 2026-02-13
Repo: `vibeship-spark-intelligence`

## Objective
Run both requested tracks end-to-end:
1. Noise/trace tuning sweep using existing knobs only.
2. Strict canary run and compare against restored baseline behavior.

## Commands Executed

### Track A: Noise/Trace Sweep
- `python benchmarks/advisory_realism_bench.py --cases benchmarks/data/advisory_realism_eval_v2.json --profile-file benchmarks/data/advisory_realism_profile_candidates_v2.json --repeats 1 --force-live --out-prefix advisory_realism_noise_trace_matrix_v1`

Artifacts:
- `benchmarks/out/advisory_realism_noise_trace_matrix_v1_report.json`
- `benchmarks/out/advisory_realism_noise_trace_matrix_v1_report.md`

Result:
- All three candidates tied (`baseline`, `balanced`, `strict`) with objective `0.4375`.
- This run did not discriminate profile quality (all failed core realism gates).

### Track B: Strict Canary Apply + Validation

Applied temporary strict canary tuneables (with backup):
- `advisory_engine.advisory_text_repeat_cooldown_s=12600`
- `advisory_gate.tool_cooldown_s=240`
- `advisory_gate.advice_repeat_cooldown_s=10800`
- `advisor.max_items=3`
- `advisor.max_advice_items=3`
- `advisor.min_rank_score=0.62`
- `advisor.retrieval_policy={semantic_context_min:0.22, semantic_lexical_min:0.07, semantic_strong_override:0.93, lexical_weight:0.38}`

Backup path:
- `C:\Users\USER\.spark\tuneables.json.canary_backup_20260213_152114`

Canary evaluation loop:
- `python scripts/advisory_controlled_delta.py --rounds 40 --label strict_canary_v1 --force-live --out docs/reports/advisory_delta_strict_canary_v1.json`
- `python scripts/run_advisory_realism_contract.py --primary-prefix advisory_realism_primary_canary_strict_v1 --shadow-prefix advisory_realism_shadow_canary_strict_v1 --run-timeout-s 1200`
- `python benchmarks/memory_retrieval_ab.py --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json --systems embeddings_only,hybrid,hybrid_agentic --top-k 5 --strict-labels --out-prefix memory_retrieval_ab_real_user_canary_strict_v1`
- `python scripts/advisory_self_review.py --window-hours 24`
- `python scripts/run_chip_learning_diagnostics.py --limit-per-chip 220 --active-only --project-path "C:\Users\USER\Desktop\vibeship-spark-intelligence" --max-age-days 14 --observer-limit 25 --out-prefix chip_learning_diagnostics_active_observer_canary_strict_v1`
- `python scripts/run_chip_observer_policy.py --report-glob "benchmarks/out/chip_learning_diagnostics_active_observer*_report.json" --windows 6 --min-windows 2 --min-rows-total 20 --disable-max-schema-statement-rate 0.03 --disable-min-telemetry-rate 0.75 --keep-min-schema-statement-rate 0.2 --keep-min-merge-eligible 1 --out-prefix chip_observer_policy_canary_strict_v1 --apply`

## Key Evidence

### 1) Canary caused major primary realism regression
Pre-canary primary contract (`benchmarks/out/advisory_realism_primary_contract_report.json`):
- objective `0.883`
- score `0.9296`
- high_value `0.7222`
- critical_miss `0.0`
- theory_disc `1.0`
- trace `1.0`

Canary primary contract (`benchmarks/out/advisory_realism_primary_canary_strict_v1_report.json`):
- objective `0.3981`
- score `0.4125`
- high_value `0.1667`
- critical_miss `0.6667`
- theory_disc `0.2778`
- trace `0.3889`

### 2) Apples-to-apples live delta also strongly negative under strict canary
- `docs/reports/advisory_delta_strict_canary_v1.json`: emitted `3/40` (7.5%)
- `docs/reports/advisory_delta_restored_balanced_v1.json`: emitted `19/40` (47.5%)
- delta (restored - strict): `+16` emitted, `+40.0pp` emission rate

### 3) Memory retrieval stayed stable (no advisory-canary side regression)
- `memory_retrieval_ab_real_user_daily_strict_report.json` vs `memory_retrieval_ab_real_user_canary_strict_v1_report.json`
- winner remained `hybrid_agentic`
- quality metrics unchanged; latency slightly improved in canary run

### 4) Observer telemetry cleanup state unchanged
- Diagnostics unchanged: rows `9`, merge_eligible `2`, telemetry `0.0`, statement_yield `0.7778`
- Policy unchanged: disable `4`, keep `4`, neutral `1`

## Decision
- Strict canary is rejected.
- Tuneables rolled back to backup:
  - `advisory_engine.advisory_text_repeat_cooldown_s=7200`
  - `advisory_gate.tool_cooldown_s=120`
  - `advisory_gate.advice_repeat_cooldown_s=3600`
  - `advisor.max_items=4`
  - `advisor.max_advice_items=4`
  - `advisor.min_rank_score=0.5`

## Optimization Focus (No New Features)
1. Keep current balanced profile; do not harden to strict globally.
2. Focus on evidence/trace quality and memory distillation quality (not tighter gates).
3. Keep observer-policy cleanup active and increase analysis windows for more than 9-row diagnostics snapshots.
4. Continue daily controlled delta + contract checks to detect regressions before applying stricter knobs.
