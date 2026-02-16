# Memory Retrieval Domain Matrix (2026-02-16)

## Scope
- Implemented domain-aware retrieval policy overlays in runtime advisor.
- Added per-domain memory retrieval matrix benchmark with pass/fail gates.
- Ran live benchmark on `benchmarks/data/memory_retrieval_eval_live_2026_02_12.json`.

## Command
```bash
python benchmarks/memory_retrieval_domain_matrix.py \
  --cases benchmarks/data/memory_retrieval_eval_live_2026_02_12.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --min-cases-per-domain 2 \
  --out-prefix memory_retrieval_domain_matrix_live_2026_02_16
```

## Result Snapshot
- Domains detected: `1` (`memory`, 24 cases)
- Winner: `hybrid_agentic`
- Weighted metrics:
- MRR: `0.3438`
- Top1 hit rate: `0.2917`
- Non-empty rate: `1.0000`
- Error rate: `0.0000`
- Domain gate pass rate: `0.0000`

## Gate Outcome (memory domain)
- Gate thresholds:
- `mrr_min >= 0.42`
- `top1_hit_rate_min >= 0.25`
- `non_empty_rate_min >= 0.55`
- `error_rate_max <= 0.10`
- Status:
- `mrr_min`: fail (`0.3438`)
- `top1_hit_rate_min`: pass (`0.2917`)
- `non_empty_rate_min`: pass (`1.0000`)
- `error_rate_max`: pass (`0.0000`)

## Interpretation
- Retrieval reliability and recall are strong enough to keep outputs non-empty and stable.
- Quality still misses the stricter memory-domain MRR bar (`0.42`), so gate remains red.
- This establishes an objective, domain-specific quality target for subsequent tuning.
