# Advisory Emotion Weight Sweep v1

Date: 2026-02-17  
Scope: live advisory integration + real-corpus A/B sweep (`0.0, 0.1, 0.2, 0.3, 0.4`)

## Step 1: Live Advisory Integration

Implemented in `lib/advisor.py`:
- `memory_emotion.enabled` gate for live semantic advisory rerank.
- `memory_emotion.advisory_rerank_weight` default `0.15` (low-risk canary default).
- `memory_emotion.advisory_min_state_similarity` default `0.30`.
- Route telemetry fields:
  - `emotion_state_enabled`
  - `emotion_state_weight`
  - `emotion_min_state_similarity`
  - `emotion_state_active`
  - `emotion_state_match_count`

Validation:
- New test `tests/test_advisor_retrieval_routing.py::test_semantic_rerank_boosts_emotion_state_match` passed.

## Step 2: Real-Corpus Sweep

Corpus:
- `benchmarks/data/memory_retrieval_eval_multidomain_real_user_2026_02_16.json` (91 labeled cases)

Command pattern:

```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_multidomain_real_user_2026_02_16.json \
  --systems hybrid_agentic \
  --top-k 5 \
  --emotion-state-weight <weight> \
  --out-prefix emotion_weight_sweep_<tag>
```

### Results

| weight | precision@5 | mrr | top1_hit_rate | p95_latency_ms | error_rate |
|---|---:|---:|---:|---:|---:|
| 0.0 | 0.1165 | 0.2568 | 0.1868 | 257 | 0.0 |
| 0.1 | 0.1165 | 0.2568 | 0.1868 | 260 | 0.0 |
| 0.2 | 0.1165 | 0.2568 | 0.1868 | 260 | 0.0 |
| 0.3 | 0.1165 | 0.2568 | 0.1868 | 239 | 0.0 |
| 0.4 | 0.1165 | 0.2568 | 0.1868 | 261 | 0.0 |

Gate policy used:
- Quality improvement required over baseline (`mrr`, `top1`, `precision` non-decreasing; `mrr` strictly higher).
- Latency regression guard: `p95 <= baseline * 1.15`.
- Error regression guard: `error_rate <= baseline`.

Decision:
- **No promotion winner** (no weight produced quality uplift).
- Keep rollout in safe canary mode (low default weight, quick rollback available via `memory_emotion.enabled=false`).

## Why No Uplift Yet

Observed in runtime snapshot:
- Cognitive insight store currently has `0` entries with `meta.emotion`.
- Without emotion-tagged cognitive insights, live advisory semantic rerank has little signal to exploit.

Next bridge gap to unlock measurable uplift:
1. Backfill emotion metadata into cognitive insights (or attach lookup bridge from memory-store emotion snapshots to cognitive insight keys/text).
