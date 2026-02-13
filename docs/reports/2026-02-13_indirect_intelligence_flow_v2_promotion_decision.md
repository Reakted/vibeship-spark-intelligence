# Indirect Intelligence Flow v2 Promotion Decision

Date: 2026-02-13

## Scope
Deterministic matched-repeat A/B/C/D plus tie-break confirmations.

## Stage 1: 3-cycle matched A/B/C/D (multidomain realism bench)

Command (per cycle):
- `python benchmarks/advisory_realism_bench.py --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json --profiles A_control,B_retrieval_v2,C_chip_targeted,D_combined --profile-file benchmarks/data/advisory_realism_profile_candidates_indirect_v1.json --repeats 1 --out-prefix advisory_realism_indirect_abcd_v2_cycleN`

Artifacts:
- `benchmarks/out/advisory_realism_indirect_abcd_v2_cycle1_report.json`
- `benchmarks/out/advisory_realism_indirect_abcd_v2_cycle2_report.json`
- `benchmarks/out/advisory_realism_indirect_abcd_v2_cycle3_report.json`

Per-cycle winners:
- cycle1: `A_control` objective `0.7365`
- cycle2: `A_control` objective `0.7261`
- cycle3: `A_control` objective `0.7261`

Cross-cycle mean objective:
- `A_control`: `0.729567`
- `B_retrieval_v2`: `0.729567` (exact tie vs A)
- `C_chip_targeted`: `0.706600`
- `D_combined`: `0.704167`

Interpretation:
- `C` and `D` are clear regressions.
- `A` and `B` are tied on Stage-1 aggregate.

## Stage 2: A vs B tie-break confirmations

### 2.1 Primary realism confirmation (v2 cases)
- `benchmarks/out/advisory_realism_indirect_ab_confirm_primary_v1_report.json`

Result:
- `B_retrieval_v2` objective `0.6547`
- `A_control` objective `0.6119`
- delta objective (B-A): `+0.0428`

### 2.2 Shadow realism confirmation (v1 cases)
- `benchmarks/out/advisory_realism_indirect_ab_confirm_shadow_v1_report.json`

Result:
- `B_retrieval_v2` objective `0.5304`
- `A_control` objective `0.5281`
- delta objective (B-A): `+0.0023`

### 2.3 Runtime controlled delta (A vs B live tuneables)
- `docs/reports/advisory_delta_indirect_v2_confirm_A_control.json`
- `docs/reports/advisory_delta_indirect_v2_confirm_B_retrieval_v2.json`

Result:
- emission rate: both `12/40` (`30%`)
- engine trace coverage: both `50.0%`
- fallback share: both `0.0%`
- no runtime emission regression for B.

### 2.4 Memory retrieval confirmation
- `benchmarks/out/memory_retrieval_ab_indirect_v2_confirm_v1_report.json`
- winner: `hybrid_agentic` (unchanged)
- no retrieval-quality regression introduced.

## Decision

Promote `B_retrieval_v2` as the preferred indirect tuning candidate for next iteration.

Reasoning:
1. It tied control in 3-cycle matched aggregate.
2. It won both A-vs-B realism tie-break checks (primary and shadow), with larger gain on primary.
3. It introduced no observed runtime emission degradation in controlled delta.
4. It did not disrupt memory retrieval outcomes.

## Safety note

`~/.spark/tuneables.json` was restored to baseline after B runtime check.
No persistent tuneable change was left active during this decision pass.

## Next step

Run a 24h canary with only `advisor.retrieval_policy` from `B_retrieval_v2` applied, then re-run:
1. `scripts/run_advisory_realism_contract.py`
2. `scripts/advisory_self_review.py --window-hours 24`
3. `benchmarks/memory_retrieval_ab.py` (same real-user set)

Promote to baseline only if objective delta remains positive without harmful/critical regressions.
