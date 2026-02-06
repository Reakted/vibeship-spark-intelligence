# Spark Intelligence v1 - Production Readiness Report
**Date:** 2026-02-06
**Overall Rating:** 2.5/5 - Not Ready to Ship Yet

The architecture is genuinely excellent - well-designed modules, clear separation of concerns, thoughtful state machines. But the implementation has 3 systemic problems that must be solved before v1.

---

## THE 3 SYSTEMIC PROBLEMS

### Problem 1: The Feedback Loop is Broken (CRITICAL)
Spark captures insights but never learns from outcomes.

- Advisor generates advice but doesn't track which advice led to which result
- 5 outcomes tracked out of 355 items = 1.4% action rate
- EIDOS distillation: 7 saved from 1,564 insights = 0.4% (persistence calls missing)
- Steps created in memory but `save_step()` never called - lost on restart
- `process_outcome_validation()` exists with correct logic but never called in any pipeline
- Promoter has no unpromote - bad insights stay in CLAUDE.md forever

**Without this fix, Spark is an advice dispenser, not a learning system.**

### Problem 2: Quality Gates Leak in Both Directions
Noise gets through AND valuable insights get dropped.

- Promoter fast-track allows insights with 1 validation + 1 contradiction (50% reliable)
- scoring.py dedup hash bug: hash stored as string, checked with isinstance(int) - dedup never fires
- Chip insights defensively filtered by promoter (treated as operational noise) - never promoted
- Advisor filters out principles without action verbs ("Remember: X" gets dropped)
- context_sync includes insights with 50+ validations at 40% reliability (frequently contradicted)
- No text truncation detection - "Prefer 'aking them..." gets promoted

### Problem 3: Operational Fragility
The system works when set up perfectly but breaks for new users.

- pyproject.toml declares only `requests` - fastapi/uvicorn/streamlit undeclared
- External pulse required but undocumented - fails silently with 1-hour cooldown
- 46/127 modules have zero tests (EIDOS, Outcomes, Chips schema, Pattern detection)
- No startup validation - services report "started" before they're ready
- Queue rotation uses truncating open("w") not atomic temp+rename - data loss risk

---

## PRIORITIZED FIX LIST

### TIER 1: Ship Blockers (1-2 weeks)

| # | Fix | Why | Effort |
|---|-----|-----|--------|
| 1 | Wire outcome tracking end-to-end | Unblocks the entire learning system. Add trace_id threading from advice -> tool execution -> outcome -> insight reliability update | 3 days |
| 2 | Add EIDOS persistence calls | save_step() after completion, save_distillation() after distill. Currently 0.4% save rate | 1 day |
| 3 | Call process_outcome_validation() in bridge_cycle | Logic exists but never invoked. Closing this loop makes predictions validate insights | 1 day |
| 4 | Fix promoter fast-track | Require min_validations >= 2 even on confidence path. Prevents 50%-reliable insights in CLAUDE.md | 2 hours |
| 5 | Add unpromote logic | If insight reliability drops below threshold post-promotion, remove from CLAUDE.md | 1 day |
| 6 | Fix scoring.py hash dedup bug | Line 219: isinstance(b, int) should check str. Currently zero dedup happening | 1 hour |
| 7 | Fix queue rotation to use atomic writes | open("w") truncates immediately - crash between open and write = entire queue lost. Use temp+rename | 2 hours |
| 8 | Declare dependencies in pyproject.toml | Add fastapi, uvicorn, pydantic. Optional: streamlit, fastembed | 30 min |

### TIER 2: Reliability (1-2 weeks after Tier 1)

| # | Fix | Why | Effort |
|---|-----|-----|--------|
| 9 | Align promotion criteria | cognitive_learner says min_reliability=0.7, min_validations=3; promoter uses 0.65, 2. Use single source in tuneables.json | 2 hours |
| 10 | Fix context_sync high-validation override | 50+ validations at 40% reliability = frequently contradicted. Should still require min reliability | 1 hour |
| 11 | Add domain keywords for all chips in scoring.py | market-intel, bench-core, spark-core, moltbook missing - scored as generic | 1 hour |
| 12 | Make chip_merger category mapping extensible | Hard-coded for 8 chips, no fallback for new ones. Add default category + chip-defined override | 1 hour |
| 13 | Fix signal key normalization | "Heavy Bash (42 calls)" and "Heavy Bash (5 calls)" stored as separate signals. Normalize before keying | 1 hour |
| 14 | Add timeouts to all blocking calls in bridge_cycle | update_spark_context(), prediction_cycle etc. can hang indefinitely | 2 hours |
| 15 | Write EIDOS unit tests | 10 modules, 0 tests. Focus on models.py, store.py, distillation_engine.py | 3 days |

### TIER 3: Polish Before Ship (1 week)

| # | Fix | Why | Effort |
|---|-----|-----|--------|
| 16 | Document startup in README | Zero lines on starting Spark currently | 2 hours |
| 17 | Add startup health validation | Services report "started" before ready. Add readiness checks | 4 hours |
| 18 | Wire chips into advisor | Advisor has zero chip integration - domain knowledge never consulted for advice | 1 day |
| 19 | Stop promoter from defensively filtering all chip insights | High-value chip insights should be promotable like any other learning | 2 hours |
| 20 | Add structured JSON logging | Currently plain text only - can't aggregate or search in production | 1 day |

---

## THINGS THAT ARE FINE (Don't Rethink)

- Core pipeline architecture (observe -> queue -> pipeline -> bridge_cycle)
- Batch save pattern (66x speedup, working well)
- Meta-Ralph quality scoring (multi-dimensional, configurable, sound)
- Chip system architecture (router/runtime/store/evolution well-designed)
- Service management (watchdog, PID files, health checks)
- Queue system (adaptive batching, priority ordering, overflow handling)
- Cognitive learner (41 noise patterns, dual-layer filtering, decay)

---

## SUBSYSTEM RATINGS

### Core Pipeline
| Component | Rating | Top Issue |
|-----------|--------|-----------|
| hooks/observe.py | 2/5 | Unbounded files, silent exceptions |
| lib/queue.py | 3/5 | Queue rotation truncates, data loss risk |
| lib/pipeline.py | 3/5 | Unbounded memory in batch processing |
| lib/bridge_cycle.py | 2/5 | Events consumed before verification |
| sparkd.py | 3/5 | No rate limiting, unbounded quarantine |
| bridge_worker.py | 2/5 | No timeout protection, respawn loop risk |

### Learning Pipeline
| Component | Rating | Top Issue |
|-----------|--------|-----------|
| cognitive_learner.py | 3.5/5 | Promotion criteria mismatch with promoter |
| meta_ralph.py | 3/5 | Outcome feedback loop broken (1.4%) |
| promoter.py | 2.5/5 | Fast-track leaky, no unpromote |
| advisor.py | 2/5 | Advice not tracked, semantic retrieval optional |
| context_sync.py | 2/5 | High-validation override broken |
| chips/scoring.py | 2.5/5 | Hash dedup bug, missing domain keywords |

### EIDOS & Storage
| Component | Rating | Top Issue |
|-----------|--------|-----------|
| EIDOS persistence | 1/5 | save_step() and save_distillation() never called |
| Prediction/Validation loops | 1.5/5 | Validation logic exists but never invoked |
| Pattern detection | 3/5 | Memory unbounded, 11 modules with 0 tests |
| Content learner | 3/5 | Patterns extracted but never validated |
| Tastebank | 2/5 | Captures preferences but nothing consults them |

### Operations
| Dimension | Score |
|-----------|-------|
| Architecture | 8/10 |
| Code Quality | 7/10 |
| Test Coverage | 5/10 (109 tests, but 46 modules untested) |
| Dependency Management | 2/10 (1 declared, 4+ used, no lock file) |
| Operational Setup | 4/10 |
| Documentation | 5/10 |
| First-Time User Experience | 3/10 |

---

## RECOMMENDED TIMELINE

**Week 1-2:** Tier 1 (feedback loop + quality gates + atomic writes + deps)
**Week 3:** Tier 2 (alignment + scoring + tests)
**Week 4:** Tier 3 (docs + advisor integration + logging)

After 4 weeks: system that actually learns from outcomes, self-corrects bad promotions, doesn't lose data on crash, installs cleanly, has test coverage on critical paths.

That's v1.
