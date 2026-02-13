# Retrieval Routing A/B/C/D (Live) v1

Generated at: `2026-02-13 23:46:50Z`

## Purpose
- Verify the retrieval routing tuneables are actually active (they must live under `~/.spark/tuneables.json` -> `retrieval.overrides.*`).
- Benchmark A/B/C/D variants to pick a routing profile that improves advisory realism (primary) without destabilizing other KPIs.

## Key Finding
- Retrieval routing is configured in one place:
  - `~/.spark/tuneables.json` -> `retrieval.overrides.*` (live)
  - benchmark profile overlays -> `retrieval.overrides.*` (same schema)

## Arms
| Arm | semantic_context_min | semantic_lexical_min | semantic_strong_override | lexical_weight |
| --- | --- | --- | --- | --- |
| A_baseline_current | 0.15 | 0.03 | 0.90 | 0.30 |
| B_retrieval_v2_active | 0.18 | 0.05 | 0.92 | 0.32 |
| C_retrieval_v2_lexical_0p28 | 0.18 | 0.05 | 0.92 | 0.28 |
| D_retrieval_v2_override_0p90 | 0.18 | 0.05 | 0.90 | 0.32 |

## Controlled Delta (20 rounds, force-live)
| Arm | emitted | no_emit | engine_error | feedback_items | top_repeat_share | unique_ratio | trace_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_baseline_current | 18 | 24 | 0 | 6 | 33.33% | 83.33% | 57.53% |
| B_retrieval_v2_active | 18 | 16 | 1 | 5 | 40.00% | 80.00% | 53.03% |
| C_retrieval_v2_lexical_0p28 | 16 | 15 | 0 | 5 | 40.00% | 80.00% | 50.00% |
| D_retrieval_v2_override_0p90 | 16 | 14 | 0 | 5 | 40.00% | 80.00% | 49.18% |

## Advisory Realism Contract (primary + shadow, repeats=1, force-live)
| Arm | PRIMARY winner | PRIMARY objective | PRIMARY high_value | PRIMARY critical_miss | PRIMARY theory_disc | PRIMARY trace | SHADOW objective | SHADOW high_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_baseline_current | baseline | 0.8099 | 61.11% | 6.67% | 88.89% | 94.44% | 0.6999 | 38.89% |
| B_retrieval_v2_active | balanced | 0.8081 | 61.11% | 6.67% | 88.89% | 94.44% | 0.6780 | 33.33% |
| C_retrieval_v2_lexical_0p28 | baseline | 0.8452 | 72.22% | 6.67% | 94.44% | 94.44% | 0.7127 | 44.44% |
| D_retrieval_v2_override_0p90 | baseline | 0.7834 | 55.56% | 6.67% | 83.33% | 94.44% | 0.6853 | 33.33% |

## Decision
- Winner for routing: **C (`lexical_weight=0.28`)**.

## Live State
- Applied Arm C to `~/.spark/tuneables.json` -> `retrieval.overrides.*`.

