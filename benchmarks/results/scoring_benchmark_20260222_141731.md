# Advisory Scoring Benchmark Results

Run: 2026-02-22 14:17:31
Cases: 50 (23 useful, 27 noise)

## Summary

| Variation | P@1 | P@2 | P@4 | Recall | Noise Rate | Score Gap | Above Gate (U/N) |
|-----------|-----|-----|-----|--------|-----------|-----------|------------------|
| a_baseline | 100% | 100% | 100% | 100% | 36% | +0.394 | 23/13 |
| b_feedback_loop | 100% | 100% | 100% | 100% | 39% | +0.375 | 23/15 |
| c_feedback_catboost | 100% | 100% | 100% | 100% | 39% | +0.375 | 23/15 |
| d_bank_quality_50 | 100% | 100% | 100% | 100% | 36% | +0.390 | 23/13 |
| e_bank_removed | 100% | 100% | 100% | 100% | 30% | +0.408 | 23/10 |
| f_bank_quality_30 | 100% | 100% | 100% | 100% | 32% | +0.398 | 23/11 |
| g_trust_default_70 | 100% | 100% | 100% | 100% | 36% | +0.394 | 23/13 |
| h_relevance_heavy | 100% | 100% | 100% | 100% | 26% | +0.413 | 23/8 |
| i_quality_heavy | 100% | 100% | 100% | 100% | 39% | +0.364 | 23/15 |
| j_lower_gate | 100% | 100% | 100% | 100% | 41% | +0.394 | 23/16 |
| k_higher_gate | 100% | 100% | 100% | 100% | 23% | +0.394 | 23/7 |
| l_combined_feedback_relevance | 100% | 100% | 100% | 100% | 32% | +0.398 | 23/11 |
| m_combined_feedback_quality | 100% | 100% | 100% | 100% | 42% | +0.346 | 23/17 |
| n_combined_best_candidate | 100% | 100% | 100% | 100% | 38% | +0.402 | 23/14 |

## Composite Ranking
Formula: `P@2 * Recall * (1 - NoiseRate)` (higher = better)

1. **k_higher_gate** (0.7667) — Gate threshold raised 0.42 -> 0.48
2. **h_relevance_heavy** (0.7419) — Relevance-heavy: 0.55*rel + 0.25*qual + 0.20*trust
3. **e_bank_removed** (0.6970) — Memory banks quality set to 0 (effectively removed)
4. **f_bank_quality_30** (0.6765) — Memory banks quality lowered 0.40 -> 0.30
5. **l_combined_feedback_relevance** (0.6765) — COMBINED: feedback loop + category boost + relevance-heavy (0.55/0.25/0.20)
6. **a_baseline** (0.6389) — Current formula: 0.45*rel + 0.30*qual + 0.25*trust, trust_default=0.50
7. **d_bank_quality_50** (0.6389) — Memory banks quality raised 0.40 -> 0.50
8. **g_trust_default_70** (0.6389) — Default trust raised 0.50 -> 0.70 (less penalty for new items)
9. **n_combined_best_candidate** (0.6216) — COMBINED: feedback + relevance-heavy + bank=0.30 + gate=0.38
10. **b_feedback_loop** (0.6053) — + feedback loop: trust boosted by source effectiveness from feedback data
11. **c_feedback_catboost** (0.6053) — + feedback + category boost: multiplicative 0.9-1.2 from feedback
12. **i_quality_heavy** (0.6053) — Quality-heavy: 0.35*rel + 0.40*qual + 0.25*trust
13. **j_lower_gate** (0.5897) — Gate threshold lowered 0.42 -> 0.38
14. **m_combined_feedback_quality** (0.5750) — COMBINED: feedback loop + category boost + quality-heavy (0.35/0.40/0.25)

## Per-Source Breakdown (Top 3 Variations)

### k_higher_gate
| Source | Useful | Noise | Mean U | Mean N | U>Gate | N>Gate | Precision |
|--------|--------|-------|--------|--------|--------|--------|-----------|
| bank | 3 | 7 | 0.631 | 0.333 | 3 | 1 | 75% |
| chip | 5 | 5 | 0.737 | 0.402 | 5 | 0 | 100% |
| cognitive | 5 | 5 | 0.676 | 0.113 | 5 | 0 | 100% |
| eidos | 5 | 5 | 0.784 | 0.314 | 5 | 2 | 71% |
| replay | 5 | 5 | 0.776 | 0.514 | 5 | 4 | 56% |

### h_relevance_heavy
| Source | Useful | Noise | Mean U | Mean N | U>Gate | N>Gate | Precision |
|--------|--------|-------|--------|--------|--------|--------|-----------|
| bank | 3 | 7 | 0.639 | 0.323 | 3 | 2 | 60% |
| chip | 5 | 5 | 0.734 | 0.360 | 5 | 0 | 100% |
| cognitive | 5 | 5 | 0.675 | 0.099 | 5 | 0 | 100% |
| eidos | 5 | 5 | 0.762 | 0.284 | 5 | 2 | 71% |
| replay | 5 | 5 | 0.763 | 0.469 | 5 | 4 | 56% |

### e_bank_removed
| Source | Useful | Noise | Mean U | Mean N | U>Gate | N>Gate | Precision |
|--------|--------|-------|--------|--------|--------|--------|-----------|
| bank | 3 | 7 | 0.603 | 0.262 | 3 | 0 | 100% |
| chip | 5 | 5 | 0.737 | 0.402 | 5 | 2 | 71% |
| cognitive | 5 | 5 | 0.676 | 0.113 | 5 | 1 | 83% |
| eidos | 5 | 5 | 0.784 | 0.314 | 5 | 2 | 71% |
| replay | 5 | 5 | 0.776 | 0.514 | 5 | 5 | 50% |

## Per-Tool Breakdown (Winner: k_higher_gate)
| Tool | Useful | Noise | Mean U | Mean N | U>Gate | N>Gate | Precision |
|------|--------|-------|--------|--------|--------|--------|-----------|
| Bash | 8 | 6 | 0.765 | 0.333 | 8 | 2 | 80% |
| Edit | 7 | 7 | 0.695 | 0.193 | 7 | 0 | 100% |
| Read | 3 | 9 | 0.631 | 0.347 | 3 | 1 | 75% |
| Write | 5 | 5 | 0.776 | 0.514 | 5 | 4 | 56% |

## Score Distribution (Winner: k_higher_gate)

### Top 10 Scored Items
| Rank | Score | Useful | Source | Text |
|------|-------|--------|--------|------|
| 1 | 0.8625 | YES | replay | Last time this file was written, the import order caused a circular dependency.  |
| 2 | 0.8350 | YES | replay | Writing to CLAUDE.md requires preserving the SPARK_LEARNINGS section markers. Pr |
| 3 | 0.8325 | YES | eidos | When running git push, verify remote branch exists first. Force-pushing to share |
| 4 | 0.8315 | YES | eidos | asyncio.create_subprocess_exec deadlocks after repeated calls on Windows — use s |
| 5 | 0.8050 | YES | eidos | Python subprocess on Windows: use CREATE_NEW_PROCESS_GROUP to prevent child proc |
| 6 | 0.7940 | YES | chip | Use tweet.py for posting (not MCP post_tweet which 403s). MCP tools work for rea |
| 7 | 0.7915 | YES | replay | JSON files must be valid after write. Previous attempt wrote trailing comma that |
| 8 | 0.7810 | YES | eidos | Before pip install, check if package is already installed with pip show. Avoids  |
| 9 | 0.7675 | YES | chip | X API tier is pay-per-usage. min_faves operator requires Pro tier ($5K/mo). Use  |
| 10 | 0.7525 | YES | chip | For X replies: all lowercase, no em dashes, 1-2 sentences max. Match the energy  |

### Bottom 10 Scored Items
| Rank | Score | Useful | Source | Text |
|------|-------|--------|--------|------|
| 41 | 0.3450 | no | bank | Multiple files may need to be read to understand the full context. |
| 42 | 0.2140 | no | eidos | Tool Bash was used successfully in this context. |
| 43 | 0.2000 | no | eidos | The command completed without errors. |
| 44 | 0.1250 | no | bank | The file was read successfully and contains relevant information. |
| 45 | 0.1240 | no | bank | Reading files is an important step in understanding code. |
| 46 | 0.0560 | no | eidos | When using Bash, remember: i meant is lets make those parts better |
| 47 | 0.0267 | no | cognitive | Cycle summary: Edit used 9 times (100% success); 17/17 Edits (100%) not preceded |
| 48 | 0.0263 | no | cognitive | Cycle summary: Edit used 4 times (100% success); 6/8 Edits (75%) not preceded by |
| 49 | 0.0222 | no | cognitive | User expressed satisfaction with the response |
| 50 | 0.0220 | no | cognitive | User expressed frustration with the response |

## Variation Descriptions
- **a_baseline**: Current formula: 0.45*rel + 0.30*qual + 0.25*trust, trust_default=0.50
- **b_feedback_loop**: + feedback loop: trust boosted by source effectiveness from feedback data
- **c_feedback_catboost**: + feedback + category boost: multiplicative 0.9-1.2 from feedback
- **d_bank_quality_50**: Memory banks quality raised 0.40 -> 0.50
- **e_bank_removed**: Memory banks quality set to 0 (effectively removed)
- **f_bank_quality_30**: Memory banks quality lowered 0.40 -> 0.30
- **g_trust_default_70**: Default trust raised 0.50 -> 0.70 (less penalty for new items)
- **h_relevance_heavy**: Relevance-heavy: 0.55*rel + 0.25*qual + 0.20*trust
- **i_quality_heavy**: Quality-heavy: 0.35*rel + 0.40*qual + 0.25*trust
- **j_lower_gate**: Gate threshold lowered 0.42 -> 0.38
- **k_higher_gate**: Gate threshold raised 0.42 -> 0.48
- **l_combined_feedback_relevance**: COMBINED: feedback loop + category boost + relevance-heavy (0.55/0.25/0.20)
- **m_combined_feedback_quality**: COMBINED: feedback loop + category boost + quality-heavy (0.35/0.40/0.25)
- **n_combined_best_candidate**: COMBINED: feedback + relevance-heavy + bank=0.30 + gate=0.38