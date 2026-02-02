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
```
