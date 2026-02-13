# R3 Tuning Matrix Benchmark v1

Date: 2026-02-13

## Objective

Test whether a near-R3 variant can outperform current `R3` and become the new primary profile.

## Plan + Commands

Plan file:
- `benchmarks/data/chip_schema_r3_tuning_matrix_v1.json`

Arms included:
- `R3_ref` (current promoted profile)
- `R3_runtime_tight`
- `R3_runtime_loose`
- `R3_merge_tight`
- `R3_merge_loose`
- `R3_evidence3` (stress test)
- Anchors: `R2_relaxed_runtime_merge`, `R0_baseline_safe`

Execution:
1. `python scripts/run_chip_schema_multiseed.py --plan benchmarks/data/chip_schema_r3_tuning_matrix_v1.json --chips social-convo,engagement-pulse,x_social --events-per-chip 24 --seed-start 20260224 --seed-count 7 --promotion-baseline-id R0_baseline_safe --promotion-candidate-id R3_ref --min-candidate-non-telemetry 0.95 --min-candidate-schema-statement 0.90 --min-candidate-merge-eligible 0.05 --out-prefix chip_schema_r3_tuning_matrix_v1`
2. Same command with `--out-prefix chip_schema_r3_tuning_matrix_v2` (determinism recheck)
3. Head-to-head:
   - `R2` vs `R3_ref`: `chip_schema_r3_tuning_h2h_r2_vs_r3_v1`
   - `R3_evidence3` vs `R3_ref`: `chip_schema_r3_tuning_h2h_e3_vs_r3_v1`
4. Fresh diagnostics snapshot:
   - `python scripts/run_chip_learning_diagnostics.py --limit-per-chip 220 --active-only --project-path "C:\Users\USER\Desktop\vibeship-spark-intelligence" --max-age-days 14 --observer-limit 25 --out-prefix chip_learning_diagnostics_active_observer_r3_tuning_matrix_v1`

## Key Results

Determinism:
- `chip_schema_r3_tuning_matrix_v1_report.json` vs `chip_schema_r3_tuning_matrix_v2_report.json`
- Exact match when ignoring `generated_at`.

Promotion gate:
- `R3_ref` vs `R0_baseline_safe`: pass rate `100%` (7/7).

Top matrix ranking:

| Rank | Arm | Objective Mean | Coverage Mean | Merge Eligible Mean | Win Rate |
|---|---|---:|---:|---:|---:|
| 1 | `R3_ref` | 0.9286 | 100.00% | 64.29% | 28.57% |
| 2 | `R2_relaxed_runtime_merge` | 0.9282 | 100.00% | 64.09% | 28.57% |
| 3 | `R3_evidence3` | 0.9282 | 100.00% | 64.09% | 28.57% |
| 4 | `R3_runtime_loose` | 0.9278 | 100.00% | 63.89% | 0.00% |
| 5 | `R3_merge_loose` | 0.9278 | 100.00% | 63.89% | 0.00% |
| 6 | `R3_merge_tight` | 0.9266 | 100.00% | 63.29% | 14.29% |
| 7 | `R3_runtime_tight` | 0.9262 | 100.00% | 63.10% | 0.00% |
| 8 | `R0_baseline_safe` | 0.9047 | 62.10% | 99.71% | 0.00% |

Head-to-head promotion vs `R3_ref`:
- `R2_relaxed_runtime_merge` candidate: pass rate `0%` (0/7), mean objective delta `-0.0004`, coverage delta `0.0`.
- `R3_evidence3` candidate: pass rate `0%` (0/7), mean objective delta `-0.0004`, coverage delta `0.0`.
- Failure reason in all windows: candidate did not beat baseline on objective+coverage simultaneously.

Diagnostics (real-history bottleneck check):
- `rows=513`, `merge_eligible=2`, `telemetry_rate=97.86%`, `statement_yield=21.05%`.

## Decision

Primary profile:
- Keep `R3` (`R3_ref`) as the active methodology.

Fallback profile:
- Keep `R2_relaxed_runtime_merge` as fallback.

Reason:
1. No tested variant beat `R3_ref` under promotion semantics.
2. `R3` remains deterministic and stable.
3. Head-to-head checks against closest alternatives both failed.

## Where To Tune Next

`R3` gates are close to local optimum on synthetic schema benchmarks.
The remaining performance ceiling is observer/input quality, not threshold tuning.

Highest-value next tuning track:
1. Reduce telemetry-heavy observer output (especially `*/chip_level` and `unknown`-heavy paths).
2. Increase semantic evidence richness per event (so `min_learning_evidence=2` carries stronger signal in real history).
3. Re-run this exact matrix after observer upgrades; only then revisit gate thresholds.

