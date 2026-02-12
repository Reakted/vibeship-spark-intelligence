# Memory Retrieval A/B Scorecard (Real User Queries)
Date: 2026-02-12  
Dataset: `benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json`  
Cases: 20 (real user prompts; role=`user`)

## Runs

### Run A: Default retrieval gates
Command:
```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 5 \
  --strict-labels \
  --out-prefix memory_retrieval_ab_real_user_2026_02_12_default
```

Result:
- Winner: `embeddings_only`
- Root issue: strict semantic gates produced zero retrieval output in `hybrid` and `hybrid_agentic` (`non_empty_rate=0.0` for both).

| System | P@5 | Recall@5 | MRR | Top1 Hit | Non-empty | p95 (ms) | Error Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| embeddings_only | 0.040 | 0.050 | 0.092 | 0.050 | 1.000 | 94 | 0.000 |
| hybrid | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 29 | 0.000 |
| hybrid_agentic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 75 | 0.000 |

Artifacts:
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_report.json`
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_report.md`

### Run B: Relaxed benchmark gates (comparison mode)
Command:
```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 5 \
  --strict-labels \
  --min-similarity 0.0 \
  --min-fusion-score 0.0 \
  --out-prefix memory_retrieval_ab_real_user_2026_02_12_relaxed
```

Result:
- Winner: `hybrid_agentic`
- MRR lift vs embeddings-only: `0.285 / 0.092 = 3.10x` (+210%).
- Latency tradeoff vs embeddings-only: p95 `229ms` vs `96ms`.

| System | P@5 | Recall@5 | MRR | Top1 Hit | Non-empty | p95 (ms) | Error Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| embeddings_only | 0.040 | 0.050 | 0.092 | 0.050 | 1.000 | 96 | 0.000 |
| hybrid | 0.075 | 0.075 | 0.102 | 0.000 | 1.000 | 69 | 0.000 |
| hybrid_agentic | 0.100 | 0.125 | 0.285 | 0.150 | 1.000 | 229 | 0.000 |

Artifacts:
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_relaxed_report.json`
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_relaxed_report.md`

## Recommendation
1. Keep `hybrid_agentic` as target default for quality, conditional on gate tuning.
2. Fix strict-gate collapse first (current default thresholds suppress hybrid outputs too aggressively on this dataset).
3. Re-run this same 20-case set after threshold tuning and record a final go/no-go.

## Kimi API note
- `KIMI_API_KEY` is present in local `.env`.
- It is not required for retrieval-only scoring above.
- It can be used next for answer-grounded quality judging (e.g., grounded answer score on top of retrieval candidates).
