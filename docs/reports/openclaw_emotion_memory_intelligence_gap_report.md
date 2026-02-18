# OpenClaw Emotion-Memory-Intelligence Gap Report

Date: 2026-02-18  
Status: Not ready to ship (core bridge landed, signal density and governance still incomplete)

## Scope

- Intelligence repo: `C:\Users\USER\Desktop\vibeship-spark-intelligence`
- Consciousness repo: `C:\Users\USER\.openclaw\workspace-spark-speed`
- Integration surface: `openclaw -> sparkd -> advisory/emotion/memory -> consciousness bridge`

## What Is Already Implemented

1. OpenClaw runtime bridge wiring in `sparkd.py`.
- Event type mapping now supports `USER_PROMPT`, `PRE_TOOL`, `POST_TOOL`, `POST_TOOL_FAILURE`, `SESSION_START`.
- OpenClaw events dispatch into advisory callbacks and emotion trigger/recovery hooks.
- Runtime behavior is tuneable via `openclaw_runtime.*` and env overrides.

2. Cognitive emotion capture in `lib/cognitive_learner.py`.
- New insight writes snapshot emotion state into `emotion_state`.
- Serialization/deserialization preserves `emotion_state`.

3. Consciousness publish helper in `workspace-spark-speed/src/bridge-to-intelligence.ts`.
- Added `publishEmotionalContextContractV1(...)`.
- Default path aligns with intelligence reader: `~/.spark/bridges/consciousness/emotional_context.v1.json`.

## Validation Outputs

1. Python tests
- Command: `python -m pytest -q tests/test_sparkd_openclaw_runtime_bridge.py tests/test_cognitive_emotion_capture.py`
- Result: `5 passed in 0.34s`
- Note: non-fatal pytest temp cleanup permission warning on process exit.

2. Node tests
- Command: `node --test tests/bridge-to-intelligence.test.ts`
- Result: `2 passed, 0 failed`

## Runtime Coverage Snapshot (Current)

Source paths:
- `C:\Users\USER\.spark\cognitive_insights.json`
- `C:\Users\USER\.spark\memory_store.sqlite`
- `C:\Users\USER\.spark\advisor\retrieval_router.jsonl`

Metrics:
- Cognitive insights with `emotion_state`: `0/276` (`0.0`)
- Recent memories with `meta.emotion`: `1/500` (`0.002`)
- Retrieval router rows with emotion fields: `48/300` (`0.16`)

Interpretation:
- The architecture path is connected, but memory signal density is too low for strong emotion-aware retrieval gains.

## High-Impact Gaps

1. `G1` High: Emotion coverage is sparse in stored artifacts.
- Impact: rerank logic is active but mostly signal-starved.
- Required task: backfill legacy memory/cognitive entries and enforce tagging on all new high-value writes.

2. `G2` High: Post-tool outcomes are not fully reconsolidated into memory updates.
- Impact: failures/frustration are sensed but not consistently turned into stronger future priors.
- Required task: implement outcome-to-memory reconsolidation worker with confidence deltas.

3. `G3` Medium: Live OpenClaw rollout lacks fixed A/B promotion contract.
- Impact: safe behavior exists, but default weight/promotion can drift.
- Required task: run real-corpus sweep and lock promotion/rollback policy.

4. `G4` Medium: Bridge freshness health checks are missing.
- Impact: stale/missing bridge payloads silently degrade unity quality.
- Required task: add bridge heartbeat/freshness checks into Spark health reporting.

## Task System (Execution Order)

1. `T1` Signal Density
- Backfill emotion metadata into top cognitive insights and recent high-value memories.
- Enforce write-time emotion tags for all new insights/memories.
- Done when: cognitive ratio >= `0.35`, memory ratio >= `0.25` on rolling sample.

2. `T2` Outcome Reconsolidation
- Map `POST_TOOL`/`POST_TOOL_FAILURE` to reconsolidation updates.
- Persist `confidence_before`, `confidence_after`, and evidence trace.
- Done when: repeated failure scenarios show measurable retrieval rank shift toward successful repair memories.

3. `T3` Live A/B Governance
- Sweep `emotion_state_weight` across `0.0, 0.1, 0.2, 0.3, 0.4` on real OpenClaw corpus.
- Promote only if quality improves and latency/error gates pass.
- Done when: winning default is recorded with rollback path.

4. `T4` Bridge Observability
- Add stale/missing bridge payload checks and schema validity health checks.
- Done when: bridge outages appear in health reports within one cycle.
