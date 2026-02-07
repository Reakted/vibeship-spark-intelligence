# V1 Control Daily Checklist (2026-02-08)

Date: 2026-02-08 (Sunday)
Scope: Controlled V1 production hardening for advisory path

## 1) Morning Startup (8:30-9:00)

1. Pull latest for both repos.
   - `git -C C:\Users\USER\Desktop\vibeship-spark-intelligence pull --ff-only`
   - `git -C C:\Users\USER\Desktop\vibeship-spark-pulse pull --ff-only`
2. Start intelligence + pulse services.
3. Confirm health endpoints respond.
   - `/api/advisory`
   - `/api/tuneables`
   - `/api/tuneables/status`
4. Verify tuneables runtime apply status is clean.
   - `warnings` should be empty or understood.
   - `restart_required` should only include `scheduler` if scheduler keys changed.

Pass/Fail gate:
- Pass only if all endpoints are healthy and no unknown tune apply warning exists.

## 2) Baseline Capture (9:00-9:30)

1. Run advisory-focused tests.
   - `python -m pytest -q tests/test_advisory_packet_store.py tests/test_advisory_intent_taxonomy.py tests/test_advisory_memory_fusion.py tests/test_advisory_dual_path_router.py`
2. Snapshot advisory metrics from Pulse Advisory tab:
   - emission rate
   - route split (`packet_exact`, `packet_relaxed`, `live`)
   - packet hit rate
   - feedback helpful rate
   - prefetch queue depth + worker status
3. Save baseline to daily notes doc with timestamp.

Pass/Fail gate:
- Pass if tests are green and baseline metrics were captured with timestamp.

## 3) Window A: Route Coverage Tuning (9:30-11:00)

Objective: Increase packet route share before touching model/provider knobs.

1. Tune only these families:
   - `advisory_engine.*`
   - `advisory_prefetch.*`
   - `advisory_packet_store.packet_ttl_s`
2. Run 15-20 representative sessions (security, testing, deployment, orchestration).
3. Record:
   - packet-route share
   - live-route share
   - queue depth behavior
4. Keep/rollback decision (single decision for entire window).

Target gate:
- packet-route >= 70%
- live-route <= 10%

Rollback rule:
- If packet-route drops >= 10 points from baseline, rollback entire window.

## 4) Window B: Latency Tail Tuning (11:30-13:00)

Objective: Reduce p95/p99 without collapsing usefulness.

1. Tune only these families:
   - `synthesizer.mode`
   - `synthesizer.ai_timeout_s`
   - `advisory_engine.max_ms`
2. Re-run same scenario pack.
3. Compare p50/p95/p99 and emission rate vs Window A.

Target gate:
- p95 <= 1200ms
- p99 <= 1800ms

Rollback rule:
- If emission rate drops >= 15% with no latency win, rollback.

## 5) Window C: Usefulness and Noise Tuning (14:00-15:30)

Objective: Improve utility while avoiding advisory spam.

1. Tune only these families:
   - `advisory_gate.max_emit_per_call`
   - `advisory_gate.warning_threshold`
   - `advisory_gate.note_threshold`
   - `advisory_gate.whisper_threshold`
   - `advisory_gate.tool_cooldown_s`
2. Run scenario pack with explicit feedback actions in Pulse.
3. Check:
   - helpful rate
   - not-helpful rate
   - too-noisy rate

Target gate:
- helpful (or acted-on) >= 50%
- too-noisy trending down day-over-day

Rollback rule:
- If too-noisy increases by >= 20% from baseline, rollback window.

## 6) Packet Quality Hardening (16:00-16:45)

1. Validate packet effectiveness rerank is active.
   - check `advisory_packet_store.config` in advisory payload
   - check `avg_effectiveness_score` trend
2. Confirm feedback loop updates packet metrics.
   - submit one `helpful` and one `not_helpful` sample
   - verify packet feedback counters move

Pass/Fail gate:
- Pass only if packet feedback updates are visible in metrics.

## 7) End-of-Day Release Decision (17:00)

All must be true to keep forward config:

1. Tests green.
2. packet-route >= 70%.
3. live-route <= 10%.
4. p95 <= 1200ms and p99 <= 1800ms.
5. helpful/acted-on >= 50%.
6. No critical runtime warnings.

If any fail:

1. Rollback last window.
2. Keep service in controlled mode.
3. Carry forward only proven-safe settings.

## 8) What To Build Next (after checklist stabilizes)

Priority 1:
1. Queue backpressure controls in tuneables (`queue.max_events`, `queue.tail_chunk_bytes`) plus dashboard visibility.
2. Memory capture/request tracker tuneables in Pulse with runtime status cards.

Priority 2:
1. Advisory scenario replay button in Pulse to run fixed probe pack and show before/after deltas.
2. Daily auto-generated advisory quality digest card for operators.

## 9) Operating Rules (non-negotiable)

1. One parameter family per window.
2. No mixed tuning across route + latency + usefulness in same window.
3. No broad rollout while any gate is failing.
4. Every change must have a measured keep/rollback decision recorded with timestamp.
