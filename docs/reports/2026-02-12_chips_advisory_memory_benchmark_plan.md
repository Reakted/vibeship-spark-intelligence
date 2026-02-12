# Chips x Advisory x Memory Plan (2026-02-12)

## Why this now

Current advisory quality improved, but chip utilization is effectively absent in realism runs.

Observed on latest multidomain runs:
- `chip_hit_rate`: `0.00%`
- `mind_hit_rate`: `0.00%`
- `semantic_hit_rate`: `0.00%`

This means our advisory loop is still mostly `cognitive + outcomes` driven, with chips not materially contributing yet.

## Key questions to answer

1. When chips are relevant, do they get retrieved at the right time?
2. If retrieved, do they improve advisory quality or add noise?
3. Which domains benefit from chips vs should avoid chip influence?
4. Can chips improve memory freshness/distillation quality, not just advisory wording?

## New capabilities added for this loop

- `benchmarks/advisory_quality_ab.py` profile overlays can now tune:
  - retrieval policy (`advisor.retrieval_policy.*`)
  - chip retrieval pressure (`chip_advice_limit`, `chip_advice_min_score`, `chip_advice_max_files`, `chip_advice_file_tail`)
  - chip ranking influence (`chip_source_boost`)

This enables chip A/B without changing core code each iteration.

## Benchmark strategy

### Stage 1: Chip-off vs Chip-on A/B

Run the same multidomain matrix with two profiles:

- Chip-off control:
  - `chip_advice_limit=1`
  - `chip_source_boost=0.8`
  - `chip_advice_min_score=0.85`

- Chip-on treatment:
  - `chip_advice_limit=6`
  - `chip_source_boost=1.35`
  - `chip_advice_min_score=0.60`

Compare deltas on:
- `high_value_rate`
- `harmful_emit_rate`
- `source_alignment_rate`
- `theory_discrimination_rate`
- domain-level objective

Accept chip treatment only if:
- high-value improves materially,
- harmful stays stable (or lower),
- source alignment improves in chip-expected domains.

### Stage 2: Domain-scoped chip activation

Prioritize chip experiments in domains where chips should help:
- `ui_design`
- `social`
- `marketing`
- `strategy`

Keep chip pressure low in domains where generic chip carryover can add noise:
- `coding`
- `debugging`
- `testing`

### Stage 3: Chip-to-memory distillation validation

For each accepted chip profile:
1. run realism matrix,
2. run `scripts/advisory_self_review.py --hours 24`,
3. inspect whether chip-backed advisories produce better outcomes and less repetition in follow-up sessions.

Promote only if it improves both advisory and post-outcome quality signals.

## Practical command sequence

1. Baseline:
```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --out-prefix advisory_realism_domain_matrix_control \
  --save-domain-reports
```

2. Chip treatment:
```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --profile-file benchmarks/data/advisory_realism_profile_candidates_v2.json \
  --out-prefix advisory_realism_domain_matrix_chip_treatment \
  --save-domain-reports
```

3. Compare:
- weighted metrics
- domain objective deltas
- chip/mind/semantic hit rates from per-domain winner case source counts

## Current status snapshot

Latest measured full-run pair:
- baseline: `benchmarks/out/advisory_realism_domain_matrix_baseline_v3_report.json`
- candidate: `benchmarks/out/advisory_realism_domain_matrix_candidate_v4_report.json`

Observed weighted delta (candidate - baseline):
- objective: `+0.0095`
- high-value: `+4.35pp`
- harmful: `0.00pp`

Interpretation:
- improvement exists but is modest and not yet chip-driven.
- we still need explicit chip pressure experiments and domain-scoped validation.

## Decision rule

Do not globally raise chip influence until at least two consecutive multidomain runs show:
1. positive weighted objective delta,
2. positive high-value delta,
3. non-regressing harmful rate,
4. measurable chip hit-rate increase in chip-expected domains.
