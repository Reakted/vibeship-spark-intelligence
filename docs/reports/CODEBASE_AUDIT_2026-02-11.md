# CODEBASE AUDIT — vibeship-spark-intelligence
**Date:** 2026-02-11  
**Scope:** Runtime paths only (excluded: `node_modules/`, `tmp/`, `sandbox/`, `benchmarks/`, build artifacts)  
**Focus:** Architecture quality, advisory flow issues, tunables wiring consistency, documentation drift

---

## Executive Summary
The runtime core is feature-rich and ambitious, but too much critical logic is concentrated in hook-time and monolithic orchestration paths. The most impactful risks are:
1) advisory packet lifecycle correctness gaps (feedback + invalidation),  
2) hook latency risk due to synchronous work,  
3) config/tuneables runtime inconsistency and docs drift.

The system is close to a strong v1.5 shape, but reliability and operability will improve sharply by hardening advisory packet semantics, decomposing the bridge cycle, and unifying config loading/hot-reload behavior.

---

## (1) Top 10 Issues by Impact

### 1) **Packet invalidation with `file_hint` is effectively broken for indexed metadata**
- **Where:** `lib/advisory_packet_store.py` (`save_packet`, `invalidate_packets`)
- **Impact:** stale packets remain active after edits; advisory relevance decays and user trust drops.
- **Why:** index metadata (`packet_meta`) does not store `advisory_text`/`advice_items`, but `invalidate_packets(..., file_hint=...)` checks only those fields in metadata.
- **Symptom:** file-scoped invalidation often no-ops for non-`*` packets.

### 2) **Implicit packet feedback does not affect effectiveness score**
- **Where:** `lib/advisory_engine.py` (`on_post_tool` → `record_packet_feedback(... followed=False ...)`) + `lib/advisory_packet_store.py`
- **Impact:** relaxed matching cannot learn from real outcomes; packet ranking stays near-prior.
- **Why:** feedback increments helpful/unhelpful only when `followed=True`; engine always sends `followed=False` for implicit post-tool feedback.

### 3) **Hook path still does significant synchronous work (latency risk)**
- **Where:** `hooks/observe.py` (`PreToolUse` path: prediction + advisory engine + EIDOS setup)
- **Impact:** potential UX slowdown during tool calls; risk increases under local I/O pressure.
- **Why:** hook process executes multiple read/write-heavy modules before returning.

### 4) **Monolithic bridge cycle creates blast radius and test friction**
- **Where:** `lib/bridge_cycle.py` (single large orchestration function)
- **Impact:** failures and regressions are harder to isolate; adding features increases coupling.
- **Why:** one function coordinates context, pipeline, learning, chips, sync, LLM advisory, EIDOS distillation, notifications.

### 5) **Tuneables hot-apply behavior is inconsistent across components**
- **Where:** multiple modules (e.g., `advisor.py`, `pipeline.py`, `eidos/models.py`, `queue.py` load-once; `advisory_synthesizer.py` reloads)
- **Impact:** operators expect runtime changes to apply but many require process restart.
- **Why:** mixed patterns (import-time load vs runtime apply hooks).

### 6) **Config/env naming drift for agent context injection**
- **Where:** `lib/orchestration.py` vs `TUNEABLES.md`
- **Impact:** operators set wrong knobs; hard-to-debug behavior.
- **Why:** code uses `SPARK_AGENT_CONTEXT_MAX_CHARS` default 1200; docs table advertises `SPARK_AGENT_CONTEXT_LIMIT` default 8000 (tokens).

### 7) **Advisory engine relies heavily on broad exception swallowing**
- **Where:** `lib/advisory_engine.py`, `hooks/observe.py`
- **Impact:** silent degradations (advice missing, no clear root cause), reduced observability.
- **Why:** many `except Exception: pass` blocks in core flow.

### 8) **Dependency drift: AI synthesis providers require libs not declared as core dependency**
- **Where:** `lib/advisory_synthesizer.py` (uses `httpx`), `pyproject.toml` (no `httpx` in core deps)
- **Impact:** synthesis path may silently degrade to programmatic mode.
- **Why:** dependency optionality undocumented/unenforced in packaging.

### 9) **In-memory/log file growth controls are uneven**
- **Where:** advisory state/logs, queue, bridge logs
- **Impact:** long-running sessions can accumulate hidden operational debt.
- **Why:** some files are bounded, some only best-effort pruned; policies differ by module.

### 10) **Documentation drift in tuneables “quick index” and defaults narrative**
- **Where:** `TUNEABLES.md` (several sections have stale summarized defaults)
- **Impact:** misconfiguration risk and low operator confidence.
- **Why:** narrative blocks lag behind current runtime defaults and compatibility mappings.

---

## (2) Top 10 Quick Wins

1. **Fix `file_hint` invalidation path** in `invalidate_packets()` to load full packet for content matching (or store searchable fields in index metadata).
2. **Count implicit packet feedback as followed-unknown** (or introduce `followed=None`) so effectiveness updates on post-tool outcome.
3. **Add per-stage timing metrics** in advisory engine (`lookup`, `gate`, `synth`, `emit`) to identify latency spikes.
4. **Add strict warning logs** for every swallowed exception in advisory/hook hot path with a compact error code.
5. **Create a shared config loader utility** (`lib/config_runtime.py`) and migrate modules to one pattern.
6. **Normalize env var names** for context injection and support aliases (`SPARK_AGENT_CONTEXT_LIMIT` + `SPARK_AGENT_CONTEXT_MAX_CHARS`).
7. **Declare `httpx` explicitly** in dependencies (or guard with explicit capability flag and startup warning).
8. **Refactor bridge cycle into stage functions** with typed stage result objects.
9. **Add one integration test** proving packet invalidation after `Edit` of referenced file.
10. **Add docs lint script** to verify defaults in `TUNEABLES.md` against module constants/`get_*_config()` outputs.

---

## (3) Recommended 7-Day Execution Plan

### Day 1 — Advisory correctness patch set
- Fix packet invalidation with file hints.
- Fix implicit packet feedback accounting.
- Add regression tests for both.

### Day 2 — Hook-path observability
- Add stage timing + outcome counters in advisory engine logs.
- Add structured error codes for previously silent exceptions.

### Day 3 — Config unification (phase 1)
- Introduce shared config utility.
- Migrate `advisory_engine`, `advisory_gate`, `advisory_packet_store`, `advisory_prefetch_worker`, `advisor`.

### Day 4 — Config unification (phase 2)
- Migrate `queue`, `pipeline`, `eidos/models`, `orchestration`.
- Add explicit “restart required vs hot-applied” metadata per section.

### Day 5 — Bridge decomposition
- Split `run_bridge_cycle()` into stage modules/functions (`context_stage`, `pipeline_stage`, `learning_stage`, `sync_stage`, `llm_stage`).
- Preserve behavior; no feature changes.

### Day 6 — Docs alignment and validation
- Reconcile `TUNEABLES.md` defaults/keys/env vars with runtime.
- Add generated config reference snippet from code.

### Day 7 — Stabilization + release gate
- Run full test suite and add targeted integration tests for advisory flow.
- Ship release notes with migration notes and runtime behavior changes.

---

## (4) Specific File-Level Changes

### High-priority code changes
1. **`lib/advisory_packet_store.py`**
   - In `invalidate_packets(... file_hint=...)`, inspect full packet via `get_packet(packet_id)` before matching advisory text/items.
   - Optionally store normalized searchable fields in `packet_meta` to avoid per-packet file reads.

2. **`lib/advisory_engine.py`**
   - In `on_post_tool`, adjust `record_packet_feedback` call semantics so implicit outcomes can update effectiveness.
   - Add stage timings and structured errors in `_log_engine_event` payload.

3. **`hooks/observe.py`**
   - Gate expensive pretool steps behind strict time budget and fail-open strategy with explicit telemetry.
   - Keep trace propagation deterministic (prefer incoming trace when present).

4. **`lib/bridge_cycle.py`**
   - Extract stage functions and reduce function length/side effects.
   - Convert mutable `stats` blob handling into typed stage outputs before merge.

5. **`lib/orchestration.py`**
   - Align env var handling (`SPARK_AGENT_CONTEXT_LIMIT` alias + max chars semantics).
   - Document and enforce one canonical variable.

6. **`lib/advisor.py`**
   - Move tuneables load to shared config utility and support runtime refresh hook.

7. **`lib/pipeline.py`**
   - Use shared config utility; clarify memory behavior around `processed_events` references.

8. **`lib/eidos/models.py`**
   - Load confidence stagnation threshold from tuneables via shared utility.

9. **`pyproject.toml`**
   - Add `httpx` to required deps or create a documented optional extra used by advisory synthesis.

### Tests to add/update
10. **`tests/test_advisory_packet_store.py`**
    - Add regression for file-hint invalidation against non-wildcard packets.

11. **`tests/test_advisory_dual_path_router.py`**
    - Add assertions that post-tool implicit feedback changes packet effectiveness.

12. **`tests/test_runtime_tuneable_sections.py`**
    - Expand to advisory engine/gate/packet store/prefetch/advisor/eidos config refresh behavior.

### Documentation changes
13. **`TUNEABLES.md`**
    - Correct env var names/defaults for agent context.
    - Mark each section as `hot-apply` or `restart-required`.
    - Update quick index values to match runtime.

14. **`README.md` + `docs/OPENCLAW_OPERATIONS.md`**
    - Add a short “config lifecycle” note: what applies live vs needs restart.

---

## Closing Note
Primary risk is not feature completeness; it is runtime correctness and operability under continuous use. Addressing the packet lifecycle + config consistency issues first will yield the highest reliability gain with minimal architectural churn.
