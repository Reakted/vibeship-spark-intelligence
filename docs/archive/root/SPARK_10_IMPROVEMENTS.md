# Spark Intelligence: 10 High-Impact Improvements

Generated: 2026-02-03
Updated: 2026-02-03 (Session 2)
Based on: Meta-Ralph analysis, tuneable review, architecture gaps

---

## Progress Summary

| # | Improvement | Status | Commit |
|---|-------------|--------|--------|
| 1 | Outcome Tracking | **DONE** | ea43727 |
| 2 | Persistence Pipeline | **DONE** | 546c965 |
| 3 | Auto-Refinement | **DONE** | db56747 |
| 4 | Lower Promotion Threshold | **DONE** | 2b830c3 |
| 5 | Aggregator Integration | **DONE** | 8b3993d |
| 6 | Skill Domain Coverage | **DONE** | 8fc233a |
| 7 | Distillation Quality | **DONE** | 42b175b |
| 8 | Advisor Integration | **DONE** | 6710219 |
| 9 | Importance Scorer Domains | **DONE** | fdc8694 |
| 10 | Chips Auto-Activation | **DONE** | 3b824a2 |

**ALL 10 IMPROVEMENTS COMPLETE** (Session 3)

---

## Current State Summary

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Quality Rate | 39.4% | 39.4% | Good |
| Filter Accuracy | 100% | 100% | Optimal |
| Outcome Tracking | 0% | **Working** | FIXED |
| Learnings Stored | 0 | **1511+** | FIXED |
| Refinements Made | 0 | **Working** | FIXED |
| Promotion Threshold | 0.7/3 | 0.65/2 | Lowered |
| Aggregator Events | 0 | **Working** | FIXED |
| Domain Coverage | 3/10 | **10/10** | FIXED |
| Distillation Quality | WEAK | **Reasoned** | FIXED |
| Advisor Threshold | 0.6 | 0.5 | Lowered |
| Chip Activation | 0.7 | 0.5 | Lowered |

---

## The 10 Improvements (Priority Order)

### 1. OUTCOME TRACKING (Critical - Zero Usage)

**Problem:** `outcome_stats` shows all zeros. Spark predicts outcomes but never validates them. Without outcome tracking, we can't:
- Know if learnings actually help
- Demote bad learnings
- Improve prediction accuracy

**File:** `lib/meta_ralph.py` → `track_outcome()` method

**What to Fix:**
```python
# Current: track_outcome() exists but is never called
# Need: Hook into post-action results to call track_outcome()
```

**Test:**
```bash
python -c "
from lib.meta_ralph import get_meta_ralph
ralph = get_meta_ralph()

# Simulate tracking
ralph.track_outcome('learning_hash_123', good=True)
print(ralph.get_stats()['outcome_stats'])
"
```

**Expected Impact:** Enables data-driven learning quality improvement

---

### 2. PERSISTENCE PIPELINE (Critical - learnings_stored = 0)

**Problem:** Quality items pass Meta-Ralph but nothing is being persisted to cognitive storage. The pipeline is broken somewhere.

**Files to Check:**
- `lib/cognitive_learner.py` → Is it receiving passed items?
- `hooks/observe.py` → Is it forwarding to learner?
- `lib/pattern_detection/aggregator.py` → Is it calling store?

**Debug Steps:**
```bash
# Check if cognitive insights file exists and has content
dir %USERPROFILE%\.spark\cognitive_insights.json

# Check recent additions
python -c "
import json
from pathlib import Path
f = Path.home() / '.spark' / 'cognitive_insights.json'
if f.exists():
    data = json.loads(f.read_text())
    print(f'Total insights: {len(data.get(\"insights\", []))}')
    for i in data.get('insights', [])[-3:]:
        print(f'  - {i.get(\"text\", \"\")[:60]}...')
"
```

**Expected Impact:** Actually remember what we learn

---

### 3. AUTO-REFINEMENT ACTIVATION (refinements_made = 0)

**Problem:** 70 items sit in needs_work zone but `refinements_made = 0`. The refinement system exists but isn't being triggered.

**File:** `lib/meta_ralph.py` → `try_refine()` method

**What to Fix:**
```python
# After roast(), if verdict == NEEDS_WORK, try auto-refinement
def roast(...):
    result = self._score(...)
    if result.verdict == RoastVerdict.NEEDS_WORK:
        refined = self.try_refine(result)  # Currently not called
        if refined and refined.verdict == RoastVerdict.QUALITY:
            return refined
    return result
```

**Test:**
```python
python -c "
from lib.meta_ralph import get_meta_ralph
ralph = get_meta_ralph()

# Test refinement
result = ralph.roast('For auth, use OAuth', source='test')
if result.verdict.value == 'needs_work':
    refined = ralph.try_refine(result)
    print(f'Refined: {refined}')
"
```

**Expected Impact:** Convert 30-50% of needs_work → quality

---

### 4. SKILL DOMAIN COVERAGE (6 domains at zero)

**Problem:** Only product (32), debugging (1), ui_ux (1) have learnings. Missing:
- orchestration
- architecture
- agent_coordination
- team_management
- game_dev
- fintech

**Root Cause:** We don't ask domain-specific questions or detect domain context.

**Solutions:**

**A. Add Domain Detection to Observe Hook:**
```python
# hooks/observe.py
DOMAIN_TRIGGERS = {
    'game_dev': ['player', 'spawn', 'physics', 'collision', 'balance'],
    'fintech': ['payment', 'transaction', 'compliance', 'risk'],
    'architecture': ['pattern', 'interface', 'module', 'dependency'],
    # etc.
}

def detect_domain(text):
    for domain, triggers in DOMAIN_TRIGGERS.items():
        if any(t in text.lower() for t in triggers):
            return domain
    return None
```

**B. Add Project Onboarding Questions:**
At session start, ask: "What domain is this project? (game/fintech/marketing/etc.)"

**Expected Impact:** Capture domain-specific expertise

---

### 5. MEMORY GATE → EIDOS CONNECTION

**Problem:** Need to verify the pipeline from Memory Gate to EIDOS store is working.

**File:** `lib/pattern_detection/memory_gate.py` → `lib/eidos/store.py`

**Test:**
```bash
# Check EIDOS store stats
python -c "
from lib.eidos import get_store
import json
print(json.dumps(get_store().get_stats(), indent=2))
"

# Check if distillations are being created
python -c "
from lib.eidos import get_store
store = get_store()
distillations = store.get_all_distillations(limit=10)
print(f'Total distillations: {len(distillations)}')
for d in distillations:
    print(f'  [{d.type.value}] {d.statement[:50]}...')
"
```

**Expected Impact:** Ensure learned patterns are retrievable

---

### 6. PROMOTION TO CLAUDE.md

**Problem:** High-quality insights should be promoted to CLAUDE.md for persistence across sessions.

**File:** `lib/promoter.py`

**Current Thresholds:**
- `DEFAULT_PROMOTION_THRESHOLD` = 0.7
- `DEFAULT_MIN_VALIDATIONS` = 3

**Test:**
```bash
python -c "
from lib.promoter import get_promotion_status
print(get_promotion_status())
"

# Check what would be promoted
python -c "
from lib.promoter import get_promotable_insights
insights = get_promotable_insights()
print(f'Ready to promote: {len(insights)}')
for i in insights[:5]:
    print(f'  - {i}')
"
```

**Tuneable Adjustment:** Lower `DEFAULT_MIN_VALIDATIONS` to 2 for faster promotion

**Expected Impact:** Learnings persist across sessions

---

### 7. DISTILLATION QUALITY IMPROVEMENT

**Problem:** Check what distillations are being created and if they're actionable.

**File:** `lib/pattern_detection/distiller.py`

**Current Settings:**
- `min_occurrences` = 2
- `min_confidence` = 0.6

**Analysis:**
```bash
python -c "
from lib.pattern_detection import get_pattern_distiller
import json
distiller = get_pattern_distiller()
print(json.dumps(distiller.get_stats(), indent=2))
"
```

**Quality Check:**
```bash
python -c "
from lib.eidos import get_store
for d in get_store().get_all_distillations(limit=20):
    quality = 'GOOD' if len(d.statement) > 30 and 'because' in d.statement.lower() else 'WEAK'
    print(f'[{quality}] {d.statement[:70]}...')
"
```

**Expected Impact:** Higher quality reusable rules

---

### 8. ADVISOR INTEGRATION

**Problem:** Verify the Advisor is using stored learnings to guide decisions.

**File:** `lib/advisor.py`

**Test:**
```bash
python -c "
from lib.advisor import get_advisor
advisor = get_advisor()

# Query for advice on a topic
advice = advisor.get_advice(tool='Edit', context={'file': 'auth.py'})
print(f'Advice items: {len(advice)}')
for a in advice:
    print(f'  - {a}')
"
```

**Tuneable Adjustment:**
- `MIN_RELIABILITY_FOR_ADVICE` = 0.6 → Lower to 0.5 to get more advice
- `MAX_ADVICE_ITEMS` = 5 → Raise to 8 for complex tasks

**Expected Impact:** Learnings actively guide decisions

---

### 9. IMPORTANCE SCORER DOMAIN WEIGHTS

**Problem:** Domain weights were added but need real-world testing.

**File:** `lib/importance_scorer.py`

**Test Each Domain:**
```bash
# Test game_dev domain
spark importance --text "Player health should be 300 for better balance"
# Expected: HIGH tier (game_dev domain detected)

# Test fintech domain
spark importance --text "We need PCI compliance for payment processing"
# Expected: HIGH tier (fintech domain detected)

# Test architecture domain
spark importance --text "Use the adapter pattern for this interface"
# Expected: HIGH tier (architecture domain detected)
```

**Add Missing Domains if Needed:**
```python
DOMAIN_WEIGHTS["devops"] = {
    "deploy": 1.5,
    "pipeline": 1.4,
    "container": 1.3,
    "kubernetes": 1.4,
}
```

**Expected Impact:** Domain-specific insights scored correctly

---

### 10. CHIPS AUTO-ACTIVATION

**Problem:** Chips should auto-activate based on project context but may not be triggering.

**File:** `lib/chips/loader.py`, `lib/metalearning/strategist.py`

**Current Settings:**
- `auto_activate_threshold` = 0.7

**Test:**
```bash
# Check which chips are active
python -c "
from lib.chips import get_active_chips
chips = get_active_chips()
print(f'Active chips: {len(chips)}')
for c in chips:
    print(f'  - {c.name}: {c.triggers}')
"

# Check chip insights
dir %USERPROFILE%\.spark\chip_insights\
```

**Tuneable Adjustment:** Lower `auto_activate_threshold` to 0.5 for more proactive activation

**Expected Impact:** Domain expertise automatically loaded

---

## Implementation Priority

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| 1 | Outcome Tracking | Medium | CRITICAL |
| 2 | Persistence Pipeline | Low | CRITICAL |
| 3 | Auto-Refinement | Low | High |
| 4 | Skill Domain Coverage | Medium | High |
| 5 | Memory Gate → EIDOS | Low | High |
| 6 | Promotion to CLAUDE.md | Low | Medium |
| 7 | Distillation Quality | Medium | Medium |
| 8 | Advisor Integration | Low | Medium |
| 9 | Importance Scorer Domains | Low | Medium |
| 10 | Chips Auto-Activation | Low | Medium |

---

## Quick Wins (Do Tonight)

### Fix 1: Enable Auto-Refinement
In `lib/meta_ralph.py`, ensure `try_refine()` is called after needs_work verdict.

### Fix 2: Check Persistence Pipeline
Run the debug commands above to find where the pipeline breaks.

### Fix 3: Lower Promotion Threshold
In `lib/promoter.py`, change `DEFAULT_MIN_VALIDATIONS` from 3 to 2.

---

## Monitoring Commands

```bash
# Full health check
python -c "
from lib.meta_ralph import get_meta_ralph
from lib.eidos import get_store
import json

ralph = get_meta_ralph()
store = get_store()

print('=== META-RALPH ===')
print(json.dumps(ralph.get_stats(), indent=2))
print()
print('=== EIDOS STORE ===')
print(json.dumps(store.get_stats(), indent=2))
"

# Session summary
python -c "from lib.meta_ralph import get_meta_ralph; print(get_meta_ralph().print_session_summary())"

# Deep analysis
python tests/test_cognitive_capture.py deep
```

---

## Success Metrics

After implementing these improvements, target:

| Metric | Current | Target |
|--------|---------|--------|
| Outcome Tracking | 0% | 50%+ |
| Learnings Stored | 0 | 20+ per session |
| Refinement Rate | 0% | 30%+ of needs_work |
| Skill Domains | 3/9 | 6/9 |
| Promotion Rate | 0 | 5+ per session |

---

## Next Session Checklist

- [ ] Run improvement #1 (Outcome Tracking)
- [ ] Run improvement #2 (Persistence Pipeline)
- [ ] Run improvement #3 (Auto-Refinement)
- [ ] Validate with test commands
- [ ] Update this document with results
