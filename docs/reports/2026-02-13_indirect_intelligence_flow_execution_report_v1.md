# Indirect Intelligence Flow Optimization - Execution Report v1

Date: 2026-02-13

## What was executed

### Planning artifact
- `docs/reports/2026-02-13_indirect_intelligence_flow_matrix_plan_v1.md`

### Full A/B/C/D matrix run
- Runner: `scripts/run_indirect_intelligence_flow_matrix.py`
- Run id: `2026-02-13_indirect_intelligence_flow_matrix_v1b`
- Outputs:
  - `benchmarks/out/2026-02-13_indirect_intelligence_flow_matrix_v1b_results.json`
  - `docs/reports/2026-02-13_indirect_intelligence_flow_matrix_v1b_scorecard.md`

Matrices executed:
1. Distillation quality (`m1_distillation`)
2. Observer policy thresholds (`m2_observer`)
3. Retrieval gate stability (`m3_retrieval`)
4. Trace attribution integrity (`m4_trace`)

Result summary:
- Winner arm in all matrices: `A` (control)
- No arm in v1b outperformed control on realism objective.

### Detailed sensitivity follow-up

To find a more discriminative benchmark surface, additional multidomain runs were executed:
- Control:
  - `benchmarks/out/advisory_realism_domain_matrix_detail_control_v1_report.json`
  - weighted objective: `0.7153`
- Retrieval-v2 candidate profile:
  - `benchmarks/out/advisory_realism_domain_matrix_detail_retrieval_v2_report.json`
  - weighted objective: `0.7652`
- Chip-targeted profile:
  - `benchmarks/out/advisory_realism_domain_matrix_detail_chip_targeted_v1_report.json`
  - weighted objective: `0.7433`

Additional direct A/B/C/D follow-up profile pack:
- Profile file: `benchmarks/data/advisory_realism_profile_candidates_indirect_v1.json`
- Run output: `benchmarks/out/advisory_realism_domain_matrix_indirect_abcd_v1_report.json`
- Outcome in that run: all domain winners were `A_control`.

## Interpretation

1. The full indirect matrix v1b did not produce a clear global winner beyond control.
2. The multidomain surface is sensitive (it showed meaningful objective movement in separate control/retrieval/chip runs), unlike some flat signals from the first matrix pass.
3. The strongest positive signal observed was retrieval-policy candidate (`retrieval_v2`) in standalone multidomain comparison.
4. Chip-targeted profile improved over control in standalone multidomain comparison, but did not consistently beat control in direct A/B/C/D follow-up run.
5. This indicates high variance/order effects; we need matched, repeated, deterministic comparisons for promotion decisions.

## Current state safety check

Tuneables were restored to baseline after matrix runner completion:
- advisory cooldowns: `7200 / 120 / 3600`
- advisor: `max_items=4`, `min_rank=0.5`
- semantic: `min_similarity=0.58`, `min_fusion_score=0.5`
- meta_ralph: `attribution_window_s=1200`, `strict_attribution_require_trace=true`

## Next benchmark queue (v2)

### Stage 1: Deterministic matched repeats (same order each run)

Run 3 repeated cycles for each arm on multidomain matrix:
- A: control
- B: retrieval_v2
- C: chip_targeted
- D: combined

Required acceptance across repeats:
- objective mean gain >= +0.02 vs control
- no harmful regression (harmful_emit_rate not higher than control)
- critical_miss_rate not worse than control

### Stage 2: Contract confirmation for winner only

Take Stage-1 winner and run:
1. `scripts/run_advisory_realism_contract.py`
2. `benchmarks/memory_retrieval_ab.py` on real-user dataset
3. `scripts/advisory_controlled_delta.py` (fixed rounds)

Promote only if all pass.

### Stage 3: Observer window expansion before policy retune

Current diagnostics snapshots are low-row (`rows=9`) in active-only daily windows. Expand diagnostics windows first, then re-run observer policy A/B/C/D with richer evidence.

## Recommendation right now

- Keep production on current restored balanced defaults.
- Use multidomain matrix as the primary screening benchmark for indirect tuneables.
- Prioritize retrieval-policy tuning first, then chip-targeted tuning, then observer-policy thresholds.
