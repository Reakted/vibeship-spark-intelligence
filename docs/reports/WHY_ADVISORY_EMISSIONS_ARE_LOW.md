# Why Advisory Emissions Are So Low

**Date**: 2026-02-21
**Context**: Benchmark shows 67% advisory retrieval rate but only ~0.2% actual emission rate. This document traces every suppression point in the pipeline, explains why each exists, and identifies which ones are over-aggressive.

---

## The Funnel At A Glance

```
5000 memories
  │
  ▼ importance_score()                    ← ~6% pass (Layer A: 28%)
 ~300 survivors
  │
  ▼ Meta-Ralph roast()                    ← ~58% pass of survivors
 ~175 quality-gated
  │
  ▼ Cognitive noise filter                ← ~81% pass
 ~142 injected into store
  │
  ▼ advisor.advise() retrieval            ← 67% of queries get advice
 ~350 queries with advice items
  │
  ▼ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ← THE WALL
  │
  ▼ on_pre_tool() emission                ← ~0.2% of queries emit
 ~1 actual emission
```

The retrieval→emission gap is where 99.7% of advice dies. Here's every kill point.

---

## Layer 1: Distillation Transformer (7 suppression rules)

**File**: `lib/distillation_transformer.py` — `should_suppress()`

Before advice even enters the store for some paths, the transformer can flag it as `suppressed=True`:

| # | Rule | What it kills | Over-aggressive? |
|---|------|---------------|------------------|
| SP1 | Prefix match (`RT @`, `[DEPTH:`, `Strong Socratic...`) | Training artifacts, retweets | No — correct |
| SP2 | Verbatim quote starts (`Now, can we`, `Can you now`, `by the way`) | User transcript fragments | No — correct |
| SP3 | Regex patterns (`said it like this`, `another reply is`) | Conversation noise | No — correct |
| SP4 | `unified_score < 0.15` | Below quality floor | Borderline — floor is low |
| SP5 | `actionability == 0 AND reasoning == 0` | No verb, no why | **YES** — kills observations with data |
| SP6 | `len(text) < 20` | Too short | No — correct |
| SP7 | `len(text) > 800` | Too long | No — correct |

**SP5 is the worst offender.** A memory like "Redis caching reduced latency by 73%" has outcome_linked and specificity but zero actionability (no imperative verb) and zero reasoning (no "because"). The fix we applied (novelty >= 0.5 bypass) helps but doesn't fully solve it.

---

## Layer 2: Advisor Ranking (`_rank_score`) — Multiplicative Score Crushing

**File**: `lib/advisor.py:4605` — `_rank_score()`

This is where advice gets scored for the gate. The problem: **8 multiplicative factors** compound into extremely low scores.

```python
base_score = confidence * context_match          # starts at ~0.5 * 0.5 = 0.25

# Then MULTIPLIED by each factor:
base_score *= source_boost           # 0.5x - 1.5x
base_score *= (0.5 + actionability)  # 0.5x - 1.5x
base_score *= (0.5 + readiness)      # 0.5x - 1.0x (0.85 if unknown)
base_score *= effectiveness_mult     # 0.5x - 1.5x (skipped if no data)
base_score *= source_effectiveness   # 0.8x - 1.2x
base_score *= category_boost         # varies
base_score *= emotional_boost        # 1.0x - 1.15x
base_score *= freshness_decay        # 0.5x - 1.0x
```

**The math**: Even with decent values, 8 multipliers averaging 0.85x each produce: `0.25 * 0.85^8 = 0.068`. That's well below the NOTE threshold of 0.42.

**The compounding is the core problem.** Each factor is reasonable individually, but together they crush everything to SILENT range. A score needs to start at ~0.6+ AND get boosted at every step to clear 0.42.

**Fixes we applied (this session)**:
- MIN_RANK_SCORE 0.60 → 0.45 (floor)
- readiness default 0.50 → 0.85 (was the worst offender for new insights)
- Skip effectiveness penalty when no data (was 0.5x, now 1.0x)

These help but don't solve the fundamental multiplicative compounding.

---

## Layer 3: Advisory Gate — 5 Kill Points

**File**: `lib/advisory_gate.py` — `_evaluate_single()`

After ranking, the gate decides what to emit:

| # | Filter | What it does | Impact |
|---|--------|-------------|--------|
| G1 | `shown_advice_ids` | Already shown this session → SILENT | **Pool exhaustion** — grows forever within session, never resets. After ~50 tool calls, most advice is "already shown" |
| G2 | `is_tool_suppressed()` | Tool on cooldown → SILENT | 30s default cooldown per tool. Every Edit, Read, Bash creates a 30s blackout window |
| G3 | `_check_obvious_suppression()` | "Read before Edit" while Reading, etc. | Correct but broad |
| G4 | Authority threshold: NOTE ≥ 0.42 | Score must clear 0.42 to emit | Combined with Layer 2's score crushing, this kills nearly everything |
| G5 | `MAX_EMIT_PER_CALL = 2` | Budget cap per tool call | Rarely reached because G1-G4 kill first |

**G1 is devastating.** In a typical Claude Code session with 200+ tool calls, the `shown_advice_ids` list grows to contain every advice_id that was ever emitted. Since advice_ids are deterministic (derived from insight keys), once shown they're blocked for the ENTIRE session. With ~55 cognitive insights and ~20 EIDOS distillations, the pool is exhausted within the first 100 tool calls.

**G2 compounds with G1.** The 30s tool cooldown means if you do Edit → Read → Edit within 30 seconds (normal coding), the second Edit gets zero advice. Tool types repeat rapidly during coding.

---

## Layer 4: Advisory Engine — 4 Cross-Session Dedupe Layers

**File**: `lib/advisory_engine.py` — `on_pre_tool()`

Even after the gate says "emit", the engine applies 4 MORE suppression layers:

| # | Layer | Cooldown | What it does |
|---|-------|----------|-------------|
| E1 | `_global_recently_emitted()` by advice_id | 600s (10 min) | Same advice_id suppressed globally for 10 minutes |
| E2 | `_global_recently_emitted_text_sig()` | 600s (10 min) | Same text fingerprint suppressed for 10 minutes (catches rephrasings) |
| E3 | `_low_auth_recently_emitted()` | 600s (10 min) | WHISPER/NOTE advice suppressed globally (was 3600s / 1 hour before our fix) |
| E4 | `_duplicate_repeat_state()` | 300s (5 min) | Same text fingerprint suppressed per-session |

**These stack.** An advice item must survive ALL FOUR checks. If any one matches a previous emission within its cooldown window, the advice is killed.

**E1 + E2 together** mean that once an advice is emitted, that EXACT advice_id AND any advice with similar text are both blocked for 10 minutes. With a small pool of ~75 insights, this creates significant periods where nothing can be emitted.

**E3 (low-auth global dedupe)** is especially aggressive because NOTE-level advice (the most common authority for real advisory) is deduplicated globally with a 600s cooldown. Before our fix, this was 3600s (1 hour!), meaning a single NOTE emission would block that advice_id for an entire hour across all sessions.

---

## Layer 5: Packet Store Short-Circuit

**File**: `lib/advisory_engine.py:1325-1362`

Before any live retrieval happens, the engine first checks the **packet store** for cached advisory packets. If a packet is found:

- The packet's pre-computed advice is used instead of live retrieval
- If the packet is stale (`DELIVERY_STALE_SECONDS = 900s`), the advice may be weaker
- Packet advice doesn't benefit from real-time context matching

This means many tool calls never even reach the advisor — they get served stale, pre-cached advice that then fails the gate.

---

## Why It All Compounds: A Walkthrough

Let's trace a real scenario. User is coding, makes 10 tool calls in 5 minutes:

```
Call 1: Edit main.py        → advisor retrieves 3 items, gate emits 1 (NOTE)
                              advice_id "cog_123" added to shown_advice_ids
                              logged to global dedupe (600s cooldown)
                              logged to low-auth dedupe (600s cooldown)
                              tool "Edit" suppressed for 30s

Call 2: Read tests.py (5s)  → advisor retrieves 2 items
                              "cog_123" in shown_advice_ids → SILENT
                              other item scores 0.38 → below NOTE threshold
                              → NO EMISSION

Call 3: Edit main.py (20s)  → tool "Edit" still on 30s cooldown
                              → NO EMISSION (never even reaches advisor)

Call 4: Bash: pytest (35s)  → advisor retrieves 3 items
                              "cog_123" in shown_advice_ids → SILENT
                              "cog_456" scores 0.44 → NOTE
                              but "cog_456" text_sig matches global dedupe
                              → NO EMISSION

Call 5: Edit main.py (50s)  → advisor retrieves 2 items
                              both in shown_advice_ids → SILENT
                              → NO EMISSION

... calls 6-10 follow same pattern
```

Result: **1 emission out of 10 calls (10%)**. And this is GENEROUS — in longer sessions, `shown_advice_ids` exhausts the entire pool.

---

## The Root Causes (Ranked by Impact)

### 1. Multiplicative Score Compounding (Layer 2)
**Impact**: 8 multipliers reduce most scores to 0.05-0.15, well below the 0.42 NOTE threshold.
**Fix**: Switch from multiplicative to additive scoring, or use a weighted sum with floor.

### 2. `shown_advice_ids` Pool Exhaustion (Layer 3, G1)
**Impact**: After ~50 tool calls, most insights are permanently blocked for the session.
**Fix**: Use a sliding window (last N shown) instead of a growing list, or add a cooldown (re-eligible after 10 minutes) instead of permanent blocking.

### 3. Triple Dedupe Stack (Layer 4, E1+E2+E3)
**Impact**: 3 overlapping 600s cooldowns mean a single emission blocks the same advice_id for 10 minutes via 3 independent mechanisms.
**Fix**: Choose ONE dedupe strategy. Global by advice_id OR by text_sig, not both. Low-auth dedupe is redundant with global dedupe.

### 4. Tool Cooldown (Layer 3, G2)
**Impact**: 30s blackout per tool type. Coding involves rapid tool switching (Edit→Read→Edit every 10-15s), so many calls hit the cooldown.
**Fix**: Reduce to 10s, or make it per-file rather than per-tool-type.

### 5. Small Advisory Pool (Structural)
**Impact**: With only ~75 insights total (55 cognitive + 20 EIDOS), the entire pool is exhausted quickly by the shown_ids + dedupe layers.
**Fix**: Grow the pool (better importance_score pass rates), or rotate advice more aggressively (shorter dedupe windows).

### 6. Distillation Transformer SP5 (Layer 1)
**Impact**: Kills data-rich observations that lack imperative verbs.
**Fix**: Already partially fixed with novelty bypass. Could further relax to allow `outcome_linked >= 0.4`.

---

## What The System SHOULD Do

The current system treats advisory like a notification system with anti-spam. The problem: it's so anti-spam that it's anti-advice.

A healthy emission rate would be **5-15% of tool calls** (1 in 7 to 1 in 20). That means:
- ~50 emissions in a 500-call session
- Each insight shown 1-3 times max, at the right moment
- Fresh advice rotated in as old advice expires

To get there:
1. Replace multiplicative scoring with `0.3 * confidence + 0.3 * context_match + 0.2 * actionability + 0.2 * readiness` (additive, bounded 0-1)
2. Replace `shown_advice_ids` list with a TTL map (advice_id → timestamp, re-eligible after 600s)
3. Remove one of the three dedupe layers (E1/E2/E3) — pick the most effective and drop the others
4. Reduce tool cooldown from 30s to 10s
5. Improve importance_score pass rate for Layer A memories (currently 28%, should be 60%+)

---

## File Reference

| File | Lines | Role |
|------|-------|------|
| `lib/distillation_transformer.py` | 184-260 | should_suppress() — 7 rules |
| `lib/advisor.py` | 4605-4695 | _rank_score() — 8 multiplicative factors |
| `lib/advisory_gate.py` | 395-534 | _evaluate_single() — 5 filters |
| `lib/advisory_gate.py` | 40-45 | AUTHORITY_THRESHOLDS |
| `lib/advisory_gate.py` | 63 | TOOL_COOLDOWN_S = 30 |
| `lib/advisory_engine.py` | 78-113 | Cooldown constants (repeat, low-auth, global) |
| `lib/advisory_engine.py` | 1656-1835 | Triple dedupe stack (global + text_sig + low-auth) |
| `lib/advisory_state.py` | 250-273 | shown_advice_ids + tool suppression |

---

## Summary

The advisory system has **22 suppression points across 5 layers**, each added independently to solve a specific spam problem. Together they form a nearly impenetrable wall.

### Fixes Applied (2026-02-21)

| Fix | What Changed | Files |
|-----|-------------|-------|
| 1. Additive scoring | 8 multiplicative factors → 3-factor additive (`0.45*relevance + 0.30*quality + 0.25*trust`) | `advisor.py`, `advisory_gate.py` |
| 2. TTL on shown_advice_ids | Permanent blocking → 600s TTL (re-eligible after 10 min) | `advisory_state.py`, `advisory_gate.py`, `advisory_engine.py` |
| 3. Single dedupe | 3 overlapping layers → text_sig only | `advisory_engine.py` |
| 4. Tool cooldown reduced | 30s → 10s | `advisory_gate.py` |
| 5. **Packet store syntax fix** | **3 SyntaxErrors in advisory_packet_store.py caused TOTAL engine failure** | `advisory_packet_store.py` |
| 6. Gate score alignment | Gate used `confidence * context_match` (multiplicative) → aligned with additive model | `advisory_gate.py` |

### Results

- **Before**: 0.0% emission (engine completely broken by SyntaxError)
- **After**: 5.6% emission (29/520 queries), 0 garbage leakage
- **Advisory retrieval**: 100% (520/520 queries)
- **Precision**: 100% (0 garbage items emitted)
