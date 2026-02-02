# Spark Intelligence Tuneable Parameters

All configurable thresholds, limits, and weights across the system.
Use this to test and optimize learning quality.

---

## 1. Memory Gate (Pattern → EIDOS)

**File:** `lib/pattern_detection/memory_gate.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `threshold` | **0.5** | Minimum score to pass gate |
| `WEIGHTS["impact"]` | 0.30 | Weight for progress made |
| `WEIGHTS["novelty"]` | 0.20 | Weight for new patterns |
| `WEIGHTS["surprise"]` | 0.30 | Weight for prediction ≠ outcome |
| `WEIGHTS["recurrence"]` | 0.20 | Weight for 3+ occurrences |
| `WEIGHTS["irreversible"]` | 0.40 | Weight for high-stakes actions |
| `WEIGHTS["evidence"]` | 0.10 | Weight for validation |

**Tuning guidance:**
- Lower `threshold` → more permissive, more distillations saved
- Higher `threshold` → stricter, only high-signal items persist
- Adjust weights to prioritize different signals

---

## 2. Pattern Distiller

**File:** `lib/pattern_detection/distiller.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `min_occurrences` | **3** | Minimum pattern occurrences to distill |
| `min_confidence` | **0.6** | Minimum success rate for heuristic |
| `gate_threshold` | **0.5** | Memory gate threshold |

**Tuning guidance:**
- Lower `min_occurrences` → faster learning from fewer examples
- Higher `min_occurrences` → more evidence required before distillation

---

## 3. Request Tracker

**File:** `lib/pattern_detection/request_tracker.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_pending` | 50 | Maximum unresolved requests to track |
| `max_completed` | 200 | Maximum completed Steps to retain |
| `max_age_seconds` (timeout) | 3600 | Auto-timeout for pending requests |

---

## 4. Pattern Aggregator

**File:** `lib/pattern_detection/aggregator.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `CONFIDENCE_THRESHOLD` | **0.7** | Minimum confidence to trigger learning |
| `DEDUPE_TTL_SECONDS` | 600 | Deduplication window (10 min) |
| `DISTILLATION_INTERVAL` | **20** | Events between distillation runs |

**Tuning guidance:**
- Lower `CONFIDENCE_THRESHOLD` → more patterns trigger learning
- Lower `DISTILLATION_INTERVAL` → more frequent distillation

---

## 5. EIDOS Budget (Episode Limits)

**File:** `lib/eidos/models.py` → `Budget` class

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_steps` | **25** | Maximum steps per episode |
| `max_time_seconds` | **720** | Maximum time (12 minutes) |
| `max_retries_per_error` | **2** | Failures before forced diagnostic |
| `max_file_touches` | **2** | Max modifications to same file |
| `no_evidence_limit` | **5** | Steps without evidence before DIAGNOSE |

**Tuning guidance:**
- These are HARD GATES - when exceeded, episode transitions to HALT/DIAGNOSE
- Lower values = stricter enforcement, faster escalation
- Higher values = more freedom, risk of rabbit holes

---

## 6. EIDOS Watchers

**File:** `lib/eidos/control_plane.py`

| Watcher | Threshold | Trigger |
|---------|-----------|---------|
| Repeat Error | **2** | Same error signature twice |
| No New Info | **5** | Steps without new evidence |
| Diff Thrash | **3** | Same file modified 3x |
| Confidence Stagnation | **0.05** | Delta < 0.05 for 3 steps |

---

## 7. Cognitive Learner (Decay)

**File:** `lib/cognitive_learner.py`

### Half-Life by Category (days)

| Category | Half-Life | Notes |
|----------|-----------|-------|
| USER_UNDERSTANDING | **90** | Preferences decay slowly |
| COMMUNICATION | 90 | Style preferences |
| WISDOM | **180** | Principles last longest |
| META_LEARNING | 120 | How to learn |
| SELF_AWARENESS | 60 | Blind spots |
| REASONING | 60 | Assumptions |
| CONTEXT | **45** | Environment-specific |
| CREATIVITY | 60 | Novel approaches |

### Pruning Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_age_days` | 365 | Maximum age before pruning |
| `min_effective` | 0.2 | Minimum effective reliability |

---

## 8. Structural Retriever

**File:** `lib/eidos/retriever.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_results` | **10** | Maximum distillations returned |
| `min_overlap` (keyword) | 2 | Minimum keyword overlap for match |

---

## 9. Importance Scorer

**File:** `lib/importance_scorer.py`

| Tier | Score Range | Examples |
|------|-------------|----------|
| CRITICAL | 0.9+ | "Remember this", corrections, explicit decisions |
| HIGH | 0.7-0.9 | Preferences, principles, reasoned explanations |
| MEDIUM | 0.5-0.7 | Observations, context, weak preferences |
| LOW | 0.3-0.5 | Acknowledgments, trivial statements |
| IGNORE | <0.3 | Tool sequences, metrics, operational noise |

---

## 10. Context Sync Defaults

**File:** `lib/context_sync.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `DEFAULT_MIN_RELIABILITY` | 0.7 | Minimum reliability for sync |
| `DEFAULT_MIN_VALIDATIONS` | 3 | Minimum validations required |
| `DEFAULT_MAX_ITEMS` | 12 | Maximum items to sync |
| `DEFAULT_MAX_PROMOTED` | 6 | Maximum promoted items |

---

## Quick Reference: Most Important Tuneables

### For Learning Quality

```python
# Pattern detection
CONFIDENCE_THRESHOLD = 0.7        # lib/pattern_detection/aggregator.py
DISTILLATION_INTERVAL = 20        # lib/pattern_detection/aggregator.py

# Memory gate
threshold = 0.5                   # lib/pattern_detection/memory_gate.py
min_occurrences = 3               # lib/pattern_detection/distiller.py
min_confidence = 0.6              # lib/pattern_detection/distiller.py
```

### For Stuck Detection

```python
# EIDOS Budget
max_steps = 25                    # lib/eidos/models.py
max_retries_per_error = 2         # lib/eidos/models.py
no_evidence_limit = 5             # lib/eidos/models.py

# Watchers
repeat_error_threshold = 2        # lib/eidos/control_plane.py
diff_thrash_threshold = 3         # lib/eidos/control_plane.py
```

### For Memory Retention

```python
# Half-life (days)
WISDOM_HALF_LIFE = 180            # lib/cognitive_learner.py
CONTEXT_HALF_LIFE = 45            # lib/cognitive_learner.py
USER_UNDERSTANDING_HALF_LIFE = 90 # lib/cognitive_learner.py
```

---

## Testing Recommendations

1. **Memory Gate Testing**
   - Create test patterns with known quality
   - Verify gate passes/rejects correctly
   - Monitor `gate.get_stats()` for pass rate

2. **Distillation Quality Testing**
   - Process known patterns through distiller
   - Check distillation statement quality
   - Verify confidence scores match expectations

3. **Watcher Testing**
   - Simulate stuck scenarios
   - Verify watchers trigger at thresholds
   - Check phase transitions happen correctly

4. **Decay Testing**
   - Create old insights
   - Verify effective_reliability decays correctly
   - Check pruning removes stale items

---

---

## 11. Advisor (Action Guidance)

**File:** `lib/advisor.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `MIN_RELIABILITY_FOR_ADVICE` | **0.6** | Minimum reliability to include advice |
| `MIN_VALIDATIONS_FOR_STRONG_ADVICE` | **2** | Validations for strong advice |
| `MAX_ADVICE_ITEMS` | **5** | Maximum advice items per query |
| `ADVICE_CACHE_TTL_SECONDS` | **300** | Cache TTL (5 minutes) |

**Tuning guidance:**
- Lower `MIN_RELIABILITY_FOR_ADVICE` → more advice, lower quality
- Higher `MAX_ADVICE_ITEMS` → more context but slower

---

## 12. Memory Capture

**File:** `lib/memory_capture.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `AUTO_SAVE_THRESHOLD` | **0.82** | Score to auto-save (no confirmation) |
| `SUGGEST_THRESHOLD` | **0.55** | Score to suggest saving |
| `MAX_CAPTURE_CHARS` | **2000** | Maximum characters to capture |

### Hard Triggers (Score 0.85-1.0)

| Trigger | Score |
|---------|-------|
| "remember this" | 1.0 |
| "don't forget" | 0.95 |
| "lock this in" | 0.95 |
| "non-negotiable" | 0.95 |
| "hard rule" | 0.95 |
| "from now on" | 0.85 |

**Tuning guidance:**
- Lower `AUTO_SAVE_THRESHOLD` → more auto-saves, risk noise
- Lower `SUGGEST_THRESHOLD` → more suggestions to review

---

## 13. Event Queue

**File:** `lib/queue.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `MAX_EVENTS` | **10000** | Max events before rotation |
| `TAIL_CHUNK_BYTES` | **64KB** | Read chunk size for tail |

**Tuning guidance:**
- Lower `MAX_EVENTS` → more frequent rotation, less history
- Higher `MAX_EVENTS` → more history, larger files

---

## 14. Promoter (Insight → CLAUDE.md)

**File:** `lib/promoter.py`

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `DEFAULT_PROMOTION_THRESHOLD` | **0.7** | Minimum reliability to promote |
| `DEFAULT_MIN_VALIDATIONS` | **3** | Minimum validations to promote |

**Safety Filters:**
- Operational patterns filtered (tool sequences, telemetry)
- Safety-blocked patterns (deception, manipulation, etc.)

**Tuning guidance:**
- Lower thresholds → more promotions, more noise in CLAUDE.md
- Higher thresholds → fewer promotions, only high-confidence

---

## 15. Importance Scorer

**File:** `lib/importance_scorer.py`

### Importance Tiers

| Tier | Score Range | Action |
|------|-------------|--------|
| CRITICAL | 0.9+ | Must learn immediately |
| HIGH | 0.7-0.9 | Should learn |
| MEDIUM | 0.5-0.7 | Consider learning |
| LOW | 0.3-0.5 | Store but don't promote |
| IGNORE | <0.3 | Don't store |

### Default Keyword Weights

```python
DEFAULT_WEIGHTS = {
    "user": 1.3,
    "preference": 1.4,
    "decision": 1.3,
    "principle": 1.3,
    "style": 1.2,
}
```

### Domain-Specific Weights

| Domain | High-Value Keywords (Weight) |
|--------|------------------------------|
| game_dev | balance (1.5), feel (1.5), gameplay (1.4), physics (1.3) |
| fintech | compliance (1.5), security (1.5), transaction (1.4), risk (1.4) |
| marketing | audience (1.5), conversion (1.5), messaging (1.4), roi (1.4) |
| product | user (1.5), feature (1.4), feedback (1.4), priority (1.3) |

**Tuning guidance:**
- Adjust domain weights to prioritize domain-specific learning
- Add new domains to `DOMAIN_WEIGHTS` dict

---

## 16. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SPARK_NO_WATCHDOG` | false | Disable watchdog timers |
| `SPARK_OUTCOME_AUTO_LINK` | true | Auto-link outcomes to steps |
| `SPARK_AGENT_CONTEXT_LIMIT` | 8000 | Context token limit for agents |
| `SPARK_DEBUG` | false | Enable debug logging |
| `SPARK_MIND_URL` | localhost:8080 | Mind API endpoint |

---

## Monitoring Commands

```bash
# Check distillation stats
spark eidos --stats

# View recent distillations
spark eidos --distillations

# Check memory gate stats
python -c "from lib.pattern_detection import get_memory_gate; print(get_memory_gate().get_stats())"

# Check aggregator stats
python -c "from lib.pattern_detection import get_aggregator; print(get_aggregator().get_stats())"

# View EIDOS store stats
python -c "from lib.eidos import get_store; print(get_store().get_stats())"

# Check importance scorer stats
python -c "from lib.importance_scorer import get_importance_scorer; print(get_importance_scorer().get_feedback_stats())"

# Check advisor effectiveness
python -c "from lib.advisor import get_advisor; print(get_advisor().get_effectiveness_report())"

# Check promoter status
python -c "from lib.promoter import get_promotion_status; print(get_promotion_status())"

# Check queue stats
python -c "from lib.queue import get_queue_stats; print(get_queue_stats())"
```

---

## Quick Parameter Index

### Learning Quality Tuneables

| Parameter | File | Default | Impact |
|-----------|------|---------|--------|
| CONFIDENCE_THRESHOLD | aggregator.py | 0.7 | Patterns → learning |
| min_occurrences | distiller.py | 3 | Required evidence |
| gate threshold | memory_gate.py | 0.5 | Steps → persistence |
| AUTO_SAVE_THRESHOLD | memory_capture.py | 0.82 | User input → learning |
| PROMOTION_THRESHOLD | promoter.py | 0.7 | Learning → CLAUDE.md |

### Stuck Detection Tuneables

| Parameter | File | Default | Impact |
|-----------|------|---------|--------|
| max_steps | models.py | 25 | Episode length |
| max_retries_per_error | models.py | 2 | Error tolerance |
| no_evidence_limit | models.py | 5 | Evidence requirement |
| repeat_error_threshold | control_plane.py | 2 | Repeat detection |
| diff_thrash_threshold | control_plane.py | 3 | File edit detection |

### Memory Retention Tuneables

| Parameter | File | Default | Impact |
|-----------|------|---------|--------|
| WISDOM_HALF_LIFE | cognitive_learner.py | 180 days | Principle decay |
| USER_UNDERSTANDING_HALF_LIFE | cognitive_learner.py | 90 days | Preference decay |
| CONTEXT_HALF_LIFE | cognitive_learner.py | 45 days | Context decay |
| max_age_days | cognitive_learner.py | 365 | Prune threshold |

### System Limits

| Parameter | File | Default | Impact |
|-----------|------|---------|--------|
| MAX_EVENTS | queue.py | 10000 | Queue rotation |
| MAX_ADVICE_ITEMS | advisor.py | 5 | Advice per query |
| max_results | retriever.py | 10 | Retrieval limit |
| MAX_CAPTURE_CHARS | memory_capture.py | 2000 | Input truncation |
