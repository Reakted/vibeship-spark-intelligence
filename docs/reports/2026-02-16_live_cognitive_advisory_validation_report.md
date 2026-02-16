# Live Cognitive Advisory Validation Report

Date: 2026-02-16
Scope: Real-time advisory demo + cognitive memory utilization + retrieval benchmark validation

## 1) Runtime Health (MiniMax)

Command:
- `python -m spark.cli advisory doctor --json`

Result:
- Advisory ON: `true`
- Runtime UP: `true`
- Replay ON: `true`
- Drift: `false`
- Synth tier: `AI-Enhanced`
- Preferred provider: `minimax`
- MiniMax model: `MiniMax-M2.5`
- MiniMax availability: `true`

Interpretation:
- Advisory engine/emitter/replay loop are active.
- AI synthesis path is live with MiniMax.

## 2) Real-Time Advisory Session Demo

Session:
- `rt_demo_1771240554`

Flow executed:
1. user prompt ingested
2. pre-tool `Read`
3. pre-tool `Edit`
4. pre-tool `Bash`
5. pre-tool `Read`

Observed advisory outputs:
- `Edit`: emitted actionable advisory (`python -m pytest -q` + reproducible checks guidance)
- `Bash`: emitted actionable advisory (`python scripts/status_local.py` + reproducible checks guidance)
- `Read` steps: no emit (gate/no_advice path)

Engine log confirmation for this session:
- matched events: `5`
- `user_prompt_prefetch`: `1`
- `emitted`: `2` (`Edit`, `Bash`)
- `no_emit`: `2` (`Read`, `Read`)

Interpretation:
- Real-time advisory is functioning and trace-linked.
- Emission is selective (not noisy every step), consistent with gate policy.

## 3) Cognitive Memory Snapshot

Commands:
- `python -m spark.cli learnings --limit 20`
- `python -m spark.cli bank-stats`

Key stats:
- Cognitive insights stored: `239`
- Memory bank global entries: `419`
- Project memory files: `2`

Notable observation:
- Memory includes a lot of high-volume low-signal struggle patterns; this can pollute retrieval quality for domain-specific queries.

## 4) Learning Utilization (Write/Retrieve/Outcome)

Commands:
- `python tests/test_learning_utilization.py quick`
- `python tests/test_learning_utilization.py analyze`

Results:
- Stored: `239`
- Retrieved: `500` (209.2% of stored, repeated retrievals over time)
- Acted on: `500` (100%)
- Effectiveness: `84.6%`
- Grade: `A`

Interpretation:
- End-to-end utilization loop is active (retrieve -> act -> outcome).
- Metrics are strong operationally, though retrieval quality still depends on memory hygiene.

## 5) Controlled Advisory Workload (Cognitive Focus)

Command:
- `python scripts/advisory_controlled_delta.py --rounds 30 --label cognitive_focus --force-live --prompt-mode vary --tool-input-mode repo --out docs/reports/2026-02-16_152043_advisory_controlled_delta.json`

Results (30 rounds):
- Engine rows: `60`
- Trace coverage: `100%`
- Events:
  - `user_prompt_prefetch`: `30`
  - `emitted`: `3`
  - `no_emit`: `12`
  - `no_advice`: `15`
- Route mix: `live` only
- Fallback share: `0%`
- Emitted latency (n=3):
  - p50: `9509.2 ms`
  - p90/p95/p99/max: `11844.7 ms`

Interpretation:
- Live path works, but emitted advisory latency is too high under this benchmark profile (networked AI synthesis + live retrieval path).

## 6) Advisory Self-Review (Last 2h)

Command:
- `python scripts/advisory_self_review.py --window-hours 2 --json`

Results:
- Recent advice rows: `44`
- Trace coverage: `84.09%`
- Source split:
  - advisor: `24`
  - cognitive: `11`
  - packet: `8`
  - prefetch: `2`
- Engine events:
  - emitted: `27`
  - no_emit: `14`
  - no_advice: `15`
  - user_prompt_prefetch: `31`
- Outcomes (strict):
  - action rate: `0.2857`
  - effectiveness rate: `1.0`

Interpretation:
- Advisory is producing measurable outcomes with strict trace attribution.

## 7) Retrieval Quality Benchmark (Memory)

Command:
- `python benchmarks/memory_retrieval_ab.py --case-limit 30 --systems embeddings_only,hybrid,hybrid_agentic --out-prefix memory_retrieval_ab_live_2026-02-16_152140 --out-dir benchmarks/out`

Benchmark metadata:
- Cases run: `5` labeled cases (seed file currently has 5 valid cases)
- Insight corpus: `239`
- Winner: `hybrid_agentic`

System summaries:
- embeddings_only:
  - precision@k: `0.04`
  - recall@k: `0.0667`
  - mrr: `0.1`
  - top1_hit_rate: `0.0`
- hybrid:
  - precision@k: `0.04`
  - recall@k: `0.0667`
  - mrr: `0.1`
  - top1_hit_rate: `0.0`
- hybrid_agentic:
  - precision@k: `0.08`
  - recall@k: `0.1333`
  - mrr: `0.2`
  - top1_hit_rate: `0.0`

Interpretation:
- Retrieval system ranking is working comparatively (hybrid_agentic wins), but absolute retrieval quality is still low for benchmark intent labels.

## 8) Focused Cognitive Retrieval Probe

Probe calls (tool+context):
- `Edit` context: advisory persistence/regressions -> `1` cognitive hit
- `Read` context: minimax config inspection -> `1` cognitive hit
- `Bash` context: focused tests -> `0` hits
- `Write` context: documentation changes -> `0` hits

Interpretation:
- Cognitive retrieval is active but sparse/uneven by tool/context.

## Bottom-Line Assessment

What is working now:
- MiniMax AI advisory path is live and healthy.
- Real-time advisory emits actionable guidance on relevant tool steps.
- Learnings are being written, retrieved, and outcome-tracked.
- Traceability is good in engine logs.

What still needs improvement for stronger cognitive advisory:
- Retrieval quality/precision is low on formal benchmark tasks.
- Memory corpus has noisy high-volume patterns that likely dilute relevance.
- Emitted advisory latency in force-live benchmark is high (seconds, not sub-second).

## Recommended Next Actions (Priority)

1. Memory hygiene pass for retrieval corpus
- Demote/filter repetitive low-signal struggle artifacts from retrieval candidates.
- Keep them for diagnostics, but reduce ranking influence for advisory retrieval.

2. Retrieval tuning for precision
- Tighten semantic gate + intent-weighting for benchmark-like queries.
- Re-run memory A/B with expanded labeled cases (>5).

3. Latency control profile for real-time
- Add fast-path synthesis policy (programmatic fallback threshold) when live emit exceeds target budget.

4. Benchmark expansion
- Increase labeled memory-retrieval cases to at least 30-50 to make metrics decision-grade.
