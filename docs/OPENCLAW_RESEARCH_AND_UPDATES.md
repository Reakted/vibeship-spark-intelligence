# OpenClaw Research & Updates Log

Purpose: single place to track OpenClaw-related tuning changes, why they were made, and whether results improved or degraded.

## How to use this file

For each change:
1. Record **baseline** before changing anything
2. Record **exact parameter/code change**
3. Record **validation window** (time and cycles)
4. Record **outcome** (better/worse/neutral)
5. Keep or roll back explicitly

---

## Experiment Entry Template

### [YYYY-MM-DD HH:mm TZ] Experiment title
- **Owner:**
- **Goal:**
- **Hypothesis:**
- **Scope:** tuneables/code/cron/docs
- **Baseline:**
  - advisory relevance:
  - duplicate advice rate:
  - chips activated per cycle:
  - queue health:
- **Changes made:**
  - file/key:
  - old -> new:
- **Validation plan:**
  - cycles:
  - duration:
  - metrics:
- **Result:** better / worse / neutral
- **Evidence:**
- **Decision:** keep / rollback / iterate
- **Follow-up:**

---

## 2026-02-11 Active Worklog

### [2026-02-11 13:34 GMT+4] Sprint 1 — Redundant advisory pruning
- **Goal:** Stop advisories repeating commands already executed.
- **Changes made:**
  - `lib/bridge_cycle.py`
  - Added `_prune_redundant_advisory(...)` before writing `SPARK_ADVISORY.md`
  - Added command-backtick matching + session-status heuristic
- **Result:** better
- **Evidence:** immediate live behavior stopped obvious repeated `session-status` style advice.
- **Decision:** keep

### [2026-02-11 13:53 GMT+4] Sprint 2 — Chip fan-out relevance cap
- **Goal:** Reduce chip over-activation noise per cycle.
- **Changes made:**
  - `lib/chips/runtime.py`
  - Added `SPARK_CHIP_EVENT_ACTIVE_LIMIT` (default 6)
  - Event-level selection of most relevant chips by trigger matches
  - `process_chip_events` now reports chips actually used when available
- **Result:** better
- **Evidence:** validation cycle showed `chips 6 ...` with no errors (down from observed 13 active on tiny cycles).
- **Decision:** keep

### [2026-02-11 14:01 GMT+4] Advisory cadence + payload tuning
- **Goal:** Make advice more in-flow and less batch/noise heavy.
- **Changes made (tuneables):**
  - `~/.spark/tuneables.json`
  - `advisory_gate.max_emit_per_call`: `2 -> 1`
  - `advisory_gate.tool_cooldown_s`: `30 -> 90`
  - `advisory_gate.advice_repeat_cooldown_s`: `600 -> 1800`
  - `advisor.max_advice_items`: `10 -> 4`
  - `advisor.max_items`: `8 -> 5`
- **Changes made (cron behavior text):**
  - Job: `spark-context-refresh` (`56a7f5be-e734-47a7-a526-73c3dc9bde1a`)
  - Updated payload to checkpoint-style relevance checks (not broad batch strategy generation).
- **Validation status:** pending (next 3-6 cycles)
- **Initial decision:** keep for trial

---

## Metrics to watch each session

- Advisory relevance score (subjective 1-10)
- Repeated advice count per hour
- Actions actually taken from advisory
- Chips activated per cycle (median)
- `pattern_processed` + `chip_merge.merged`
- Queue depth before/after
- Heartbeat freshness and error count
