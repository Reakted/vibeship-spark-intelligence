# Advisory Tuning Delta (2026-02-12)

## Scope
- Objective: improve advisory quality by reducing repetition/noise while preserving actionable emissions.
- Method: controlled synthetic workload on `advisory_engine.on_pre_tool/on_post_tool`, trace-bound, with direct pre/post tuneable comparison.
- Date: February 12, 2026.

## Live Tuneables Applied
- `advisory_engine.advisory_text_repeat_cooldown_s`: `1800 -> 7200`
- `advisory_gate.tool_cooldown_s`: `90 -> 120`
- `advisory_gate.advice_repeat_cooldown_s`: `1800 -> 3600`
- `advisor.max_items`: `5 -> 4`
- `advisor.max_advice_items`: `5 -> 4`
- `advisor.min_rank_score`: `0.45 -> 0.50`

Current live state in `~/.spark/tuneables.json` was verified after the run (`updated_at`: `2026-02-12T15:15:53Z`).

## Important Fix During This Pass
- Fixed advisor tuneable loader to support UTF-8 BOM files in `lib/advisor.py`.
- Before this fix, `advisor` could silently fall back to defaults and ignore updated tuneables when the JSON had BOM.
- Regression test added: `tests/test_advisor_config_loader.py`.

## Controlled A/B Results (Force-Live Path)
Inputs:
- Baseline snapshot: `docs/reports/advisory_delta_baseline_live.json`
- Tuned snapshot: `docs/reports/advisory_delta_post_live.json`
- Both runs: 24 rounds, forced live path (`force_live=true`), unique trace/session prefixes.

Results:
- `engine.rows`: `48 -> 48` (same workload volume)
- `engine.trace_rows`: `24 -> 24`
- `engine.trace_coverage_pct`: `50.0 -> 50.0`
- `engine.events.emitted`: `12 -> 12`
- `engine.events.no_emit`: `12 -> 12`
- `emitted_returns`: `10 -> 12` (slight improvement in returned advisory text)
- `fallback_share_pct`: `0.0 -> 0.0`

## 24h Reality Check
From `scripts/advisory_self_review.py --window-hours 24` after changes:
- Repetition remains high in historical window (`WebFetch`/`Glob` caution variants still dominate).
- Engine now has substantial trace presence in recent events, but mixed event types keep overall coverage at `~50%`.

## Honest Assessment
- The tuning changes are now **definitely applied** (loader bug fixed, live values verified).
- In controlled live-path A/B, the new profile is **not worse** and slightly better on returned advisory output.
- The pass **did not yet materially reduce no-emit rate** in this synthetic pattern.
- Largest remaining gap is still **high historical repetition in self-awareness cautions** and partial trace gaps outside pre/post tool events.

## Recommendation for Next Iteration
1. Add reason-level breakdown in controlled KPI output (`error_code` distribution for `no_emit`) to tune gate thresholds with higher precision.
2. Add targeted dedupe normalization for top repeated caution families (`WebFetch fails with other tasks`, recovered variants) before ranking.
3. Re-run the same A/B harness every few hours using this report pair format to track trend, not just single-run snapshots.
