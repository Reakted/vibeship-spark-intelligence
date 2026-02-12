# Advisory Multidomain Tuning Pass v2 (2026-02-12)

## Scope

This pass targeted weak-domain advisory quality while preserving low harmful output:
- domains with prior gaps: `coding`, `conversation`, `marketing`
- cross-domain noise leak reduction
- benchmark realism methodology refinement for corrective emits

## Implemented changes

1. Advisor cross-domain filtering:
- `lib/advisor.py`
  - global non-social filter now removes X-social-specific advice across all sources (not only semantic route).

2. Actionability enforcement for synth-empty emissions:
- `lib/advisory_engine.py`
  - when emitted text is reconstructed from advice fragments, actionability (`Next check`) is now enforced on the effective text.

3. Multidomain case pack tuning:
- `benchmarks/data/advisory_realism_eval_multidomain_v1.json`
  - converted bad anti-pattern cases (`md10`, `md16`) to corrective-emission expectation.
  - kept one explicit suppression case (`md23`) for harmful/suppression coverage.

4. Realism metric refinement:
- `benchmarks/advisory_realism_bench.py`
  - `harmful_emit_rate` now counts suppression-case emits as harmful only when forbidden content is actually leaked.
  - added `unsolicited_emit_rate` to track suppression-case emits separately.

5. Benchmark tuning hooks:
- `benchmarks/advisory_quality_ab.py`
  - profile overlays now support retrieval-policy overrides and chip tuning controls:
    - `advisor.retrieval_policy.*`
    - `chip_advice_limit`, `chip_advice_min_score`, `chip_advice_max_files`, `chip_advice_file_tail`
    - `chip_source_boost`
- candidate profile overlay added:
  - `benchmarks/data/advisory_realism_profile_candidates_v2.json`

6. Domain-matrix improvements:
- `scripts/run_advisory_realism_domain_matrix.py`
  - added `--save-domain-reports`
  - added `unsolicited_emit_rate` in domain and weighted summaries

## Validation

Tests:
```bash
python -m pytest -q \
  tests/test_advisor_retrieval_routing.py \
  tests/test_advisory_realism_bench.py \
  tests/test_advisory_quality_ab.py \
  tests/test_run_advisory_realism_domain_matrix.py
```

Result: `28 passed` (non-blocking Windows temp cleanup warning persisted).

## Benchmark runs

### Baseline
```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --repeats 1 \
  --save-domain-reports \
  --out-prefix advisory_realism_domain_matrix_baseline_v3
```

Weighted:
- objective: `0.7301`
- score: `0.8924`
- high_value_rate: `43.48%`
- harmful_emit_rate: `0.00%`
- unsolicited_emit_rate: `4.35%`
- critical_miss_rate: `8.70%`
- source_alignment_rate: `44.93%`
- theory_discrimination_rate: `86.96%`
- trace_bound_rate: `100.00%`

### Candidate (retrieval/chip overlay)
```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --profile-file benchmarks/data/advisory_realism_profile_candidates_v2.json \
  --repeats 1 \
  --save-domain-reports \
  --out-prefix advisory_realism_domain_matrix_candidate_v4
```

Weighted:
- objective: `0.7396`
- score: `0.8924`
- high_value_rate: `47.83%`
- harmful_emit_rate: `0.00%`
- unsolicited_emit_rate: `4.35%`
- critical_miss_rate: `8.70%`
- source_alignment_rate: `44.93%`
- theory_discrimination_rate: `86.96%`
- trace_bound_rate: `100.00%`

Delta (candidate - baseline):
- objective: `+0.0095`
- high_value_rate: `+4.35pp`
- harmful_emit_rate: `+0.00pp`

## Honest assessment

- Advisory quality is improving and now measurably stronger on high-value rate with no harmful regression.
- Remaining major gap is source utilization quality:
  - chip/mind/semantic hit rates remain effectively absent in winner-case source counts.
- Noise is reduced but not solved; several generic “single-state / social-proof” patterns still appear in live emits.
- Candidate overlay helps, but gain is modest; this is not yet a decisive global retune.

## Next step

Proceed with chip-focused A/B loop from:
- `docs/reports/2026-02-12_chips_advisory_memory_benchmark_plan.md`

Do not globally raise chip influence until chip-expected domains show consistent source-hit and objective gains.
