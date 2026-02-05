# EIDOS Architecture Additions

**Supplements to EIDOS_ARCHITECTURE.md** — fills gaps identified in architecture review.

---

## 1. Guardrail 6: Evidence Before Modification

After 2 failed fix attempts on the same issue, the agent is **FORBIDDEN** to edit code.

### Required Before Resuming Edits

| Requirement | Description |
|-------------|-------------|
| **Reproduce Reliably** | Can trigger the issue consistently |
| **Narrow Scope** | Isolated to specific module/file/function |
| **Discriminating Signal** | Identified a test, log, or output that distinguishes success/failure |
| **Minimal Reproduction** | Created smallest code/config that triggers issue |

### Implementation

```python
class EvidenceBeforeModificationGuard:
    def check(self, episode: Episode, step: Step) -> GuardrailResult:
        if step.action_type != 'TOOL_CALL':
            return GuardrailResult(passed=True)

        if step.action_details.get('tool') not in ['Edit', 'Write']:
            return GuardrailResult(passed=True)

        # Count failed edit attempts on same target
        failed_edits = self._count_failed_edits(
            episode,
            step.action_details.get('file_path')
        )

        if failed_edits >= 2:
            if not self._has_evidence(episode):
                return GuardrailResult(
                    passed=False,
                    violation="EVIDENCE_BEFORE_MODIFICATION",
                    message="2+ failed edits. Must gather evidence before modifying.",
                    required_actions=[
                        "reproduce_reliably",
                        "narrow_scope",
                        "identify_discriminating_signal",
                        "create_minimal_reproduction"
                    ]
                )

        return GuardrailResult(passed=True)

    def _has_evidence(self, episode: Episode) -> bool:
        """Check if diagnostic evidence exists"""
        diagnostic_steps = [
            s for s in episode.steps
            if s.action_type == 'REASONING'
            and s.intent in ['diagnose', 'reproduce', 'isolate', 'narrow']
        ]
        return len(diagnostic_steps) >= 1
```

### Why This Matters

This guardrail forces the agent out of "random walk" editing into scientific debugging:

1. **Observe** (gather evidence)
2. **Hypothesize** (form theory)
3. **Predict** (what should change)
4. **Test** (make one change)
5. **Evaluate** (did prediction match?)

Without this, agents thrash by making random edits hoping something works.

---

## 2. Layer 0: Ephemeral Evidence Store

Tool logs are NOT memory. They are temporary proof artifacts.

### Purpose

- Provide audit trail for recent actions
- Enable debugging of "what exactly happened"
- Support validation of steps
- Auto-expire to prevent bloat

### Storage

```
~/.spark/evidence/
├── current.jsonl       # Active session
├── archive/
│   ├── 2026-02-01.jsonl
│   └── 2026-02-02.jsonl
└── high_stakes/        # Retained longer (deploys, security, funds)
```

### Retention Policy

| Evidence Type | Retention | Reason |
|---------------|-----------|--------|
| Standard tool output | 72 hours | Recent debugging only |
| Build/test results | 7 days | May need for validation |
| Deploy artifacts | 30 days | Audit trail |
| Security-related | 90 days | Compliance |
| User-flagged | Permanent | Explicit importance |

### Schema

```sql
CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    step_id TEXT REFERENCES steps(step_id),

    type TEXT NOT NULL,  -- TOOL_OUTPUT, DIFF, TEST_RESULT, BUILD_LOG, ERROR_TRACE
    tool_name TEXT,

    -- Content (compressed if large)
    content TEXT,
    content_hash TEXT,  -- For deduplication
    byte_size INTEGER,

    -- Metadata
    exit_code INTEGER,
    duration_ms INTEGER,

    -- Lifecycle
    created_at REAL DEFAULT (unixepoch()),
    expires_at REAL,  -- NULL = permanent
    retention_reason TEXT,  -- Why kept longer than default

    -- Indexes
    FOREIGN KEY (step_id) REFERENCES steps(step_id)
);

CREATE INDEX idx_evidence_step ON evidence(step_id);
CREATE INDEX idx_evidence_expires ON evidence(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_evidence_type ON evidence(type);
```

### Evidence Types

| Type | Description | Default Retention |
|------|-------------|-------------------|
| `TOOL_OUTPUT` | stdout/stderr from tool | 72 hours |
| `DIFF` | File changes made | 7 days |
| `TEST_RESULT` | Test pass/fail details | 7 days |
| `BUILD_LOG` | Compile/build output | 7 days |
| `ERROR_TRACE` | Stack traces, errors | 7 days |
| `DEPLOY_ARTIFACT` | Deployment logs | 30 days |
| `SECURITY_EVENT` | Auth, access, secrets | 90 days |

### Cleanup Job

```python
def cleanup_expired_evidence():
    """Run daily to remove expired evidence"""
    conn.execute("""
        DELETE FROM evidence
        WHERE expires_at IS NOT NULL
        AND expires_at < unixepoch()
    """)
```

### Link to Steps

Every step can reference its evidence:

```python
@dataclass
class Step:
    # ... existing fields ...

    # Evidence references (not the content itself)
    evidence_ids: List[str]  # Links to evidence table
```

This keeps the `steps` table lean while maintaining full audit trail.

---

## 3. Escalation Definition

Escalation is NOT failure. It's intelligent recognition of limits.

### When to Escalate

| Trigger | Condition |
|---------|-----------|
| Budget Exhausted | `step_count >= budget_steps` or `elapsed >= budget_seconds` |
| Loop Detected | Same error 3x, same file edited 4x, no progress 5 steps |
| Confidence Collapsed | Confidence dropped below 0.2 |
| Explicit Block | Guardrail returned blocking violation |
| Unknown Territory | No relevant memory AND high uncertainty |

### Escalation Output Structure

```yaml
escalation:
  episode_id: string
  escalation_type: BUDGET | LOOP | CONFIDENCE | BLOCKED | UNKNOWN

  summary:
    goal: string           # What we were trying to do
    progress: string       # How far we got
    blocker: string        # What stopped us

  attempts:
    - approach: string
      result: string
      why_failed: string

  evidence_gathered:
    - type: string
      finding: string

  current_hypothesis: string  # Best guess at root cause

  minimal_reproduction:       # If applicable
    description: string
    steps_to_reproduce: list[string]
    expected: string
    actual: string
    environment: dict

  request_type: INFO | DECISION | HELP | REVIEW
  specific_question: string   # What exactly do we need?

  suggested_options:          # If DECISION type
    - option: string
      tradeoff: string
```

### Escalation Actions by Type

| Request Type | What Agent Needs | Example |
|--------------|------------------|---------|
| `INFO` | Missing context or knowledge | "What authentication method does this API use?" |
| `DECISION` | Choice between valid approaches | "Should we fix the bug or work around it?" |
| `HELP` | Stuck, need human intervention | "I've tried X, Y, Z and none worked" |
| `REVIEW` | Uncertain about risky action | "This will delete 500 rows, please confirm" |

### Example Escalation

```yaml
escalation:
  episode_id: "ep_abc123"
  escalation_type: LOOP

  summary:
    goal: "Fix ImportError in auth module"
    progress: "Identified missing dependency, attempted 3 fixes"
    blocker: "Each fix introduces a new import error"

  attempts:
    - approach: "Added missing package to requirements.txt"
      result: "New error: version conflict with existing package"
      why_failed: "Dependency tree conflict"
    - approach: "Pinned specific version"
      result: "Different import error in test file"
      why_failed: "Test file has different requirements"
    - approach: "Updated all related packages"
      result: "Original error returned"
      why_failed: "Circular dependency issue"

  evidence_gathered:
    - type: "dependency_tree"
      finding: "Package A requires B>2.0, Package C requires B<2.0"

  current_hypothesis: "Fundamental version conflict between A and C"

  request_type: DECISION
  specific_question: "Should we (a) remove package A, (b) remove package C, or (c) fork one of them?"

  suggested_options:
    - option: "Remove package A, reimplement its functionality"
      tradeoff: "2-3 hours work, but clean dependency tree"
    - option: "Remove package C, find alternative"
      tradeoff: "Need to evaluate alternatives, unknown effort"
    - option: "Pin B at 1.9 and patch A"
      tradeoff: "Technical debt, may break in future"
```

---

## 4. Validation Methods

A step without validation is not a learning unit.

### Valid Validation Methods

| Method | Code | Description | Auto-Detectable |
|--------|------|-------------|-----------------|
| Test Passed | `test:passed` | Automated test ran and passed | Yes |
| Test Failed | `test:failed` | Automated test ran and failed | Yes |
| Build Success | `build:success` | Compile/build succeeded | Yes |
| Build Failed | `build:failed` | Compile/build failed | Yes |
| Lint Clean | `lint:clean` | Linter/formatter passed | Yes |
| Lint Errors | `lint:errors` | Linter found issues | Yes |
| Output Expected | `output:expected` | Output matched prediction | Partial |
| Output Unexpected | `output:unexpected` | Output differed from prediction | Partial |
| Error Resolved | `error:resolved` | Previous error no longer occurs | Yes |
| Error Persists | `error:persists` | Previous error still occurs | Yes |
| Manual Checked | `manual:checked` | Human verified the result | No |
| Manual Approved | `manual:approved` | Human approved the change | No |
| Deferred | `deferred:reason` | Cannot validate now | No |

### Validation Rules

```python
def validate_step(step: Step) -> ValidationResult:
    """Every step MUST have validation"""

    # Case 1: Explicit validation
    if step.validated and step.validation_method:
        return ValidationResult(valid=True, method=step.validation_method)

    # Case 2: Deferred with reason
    if step.validation_method and step.validation_method.startswith('deferred:'):
        reason = step.validation_method.split(':', 1)[1]
        if reason.strip():
            return ValidationResult(valid=True, method=step.validation_method, deferred=True)
        else:
            return ValidationResult(valid=False, error="Deferred validation requires reason")

    # Case 3: No validation = invalid step
    return ValidationResult(
        valid=False,
        error="Step must be validated or explicitly deferred with reason"
    )
```

### Deferred Validation

Sometimes validation must wait. Valid reasons:

| Reason | Example | Max Deferral |
|--------|---------|--------------|
| `deferred:needs_deploy` | "Can only verify in production" | 24 hours |
| `deferred:needs_data` | "Need real traffic to verify" | 48 hours |
| `deferred:needs_human` | "Requires manual review" | 72 hours |
| `deferred:async_process` | "Background job running" | 4 hours |

### Deferred Validation Tracking

```sql
CREATE TABLE deferred_validations (
    step_id TEXT PRIMARY KEY REFERENCES steps(step_id),
    reason TEXT NOT NULL,
    deferred_at REAL NOT NULL,
    max_wait_seconds INTEGER NOT NULL,
    reminder_sent INTEGER DEFAULT 0,
    resolved INTEGER DEFAULT 0,
    resolved_at REAL,
    resolution_method TEXT
);

-- Alert on overdue validations
CREATE VIEW overdue_validations AS
SELECT
    dv.step_id,
    dv.reason,
    dv.deferred_at,
    (unixepoch() - dv.deferred_at) as seconds_waiting,
    dv.max_wait_seconds
FROM deferred_validations dv
WHERE dv.resolved = 0
AND (unixepoch() - dv.deferred_at) > dv.max_wait_seconds;
```

---

## 5. Phase Transition Rules

Phases are NOT suggestions. Transitions are rule-driven.

### Phase Definitions

| Phase | Purpose | Allowed Actions |
|-------|---------|-----------------|
| `EXPLORE` | Understand the problem space | Read, Search, Ask, Hypothesize |
| `DIAGNOSE` | Isolate root cause | Read, Test, Log, Reproduce |
| `EXECUTE` | Implement the fix | Edit, Write, Run, Test |
| `CONSOLIDATE` | Extract learnings | Reflect, Distill, Document |
| `ESCALATE` | Request help | Summarize, Ask Human |

### Transition Matrix

```
                    ┌──────────────────────────────────────────────┐
                    │              PHASE TRANSITIONS                │
                    └──────────────────────────────────────────────┘

    FROM          TO              TRIGGER
    ─────────────────────────────────────────────────────────────
    EXPLORE   →   DIAGNOSE        Hypothesis formed
    EXPLORE   →   EXECUTE         Problem is trivial (confidence > 0.9)
    EXPLORE   →   ESCALATE        Budget 50% consumed, no hypothesis

    DIAGNOSE  →   EXECUTE         Root cause identified + plan formed
    DIAGNOSE  →   EXPLORE         Hypothesis invalidated, need new direction
    DIAGNOSE  →   ESCALATE        Cannot isolate after 5 diagnostic steps

    EXECUTE   →   CONSOLIDATE     Success criteria met
    EXECUTE   →   DIAGNOSE        Fix failed 2x (loop detected)
    EXECUTE   →   ESCALATE        Budget exhausted OR blocked by guardrail

    CONSOLIDATE → (episode ends)  Distillations generated
    CONSOLIDATE → EXECUTE         Validation revealed new issue

    ESCALATE  →   (waits)         Human input required
    ESCALATE  →   Any             Human provides direction
```

### Implementation

```python
class PhaseController:
    def evaluate_transition(self, episode: Episode, step: Step) -> Optional[Phase]:
        current = episode.phase

        # EXPLORE transitions
        if current == Phase.EXPLORE:
            if step.hypothesis and step.confidence_after > 0.6:
                return Phase.DIAGNOSE
            if step.confidence_after > 0.9 and self._is_trivial(step):
                return Phase.EXECUTE
            if self._budget_percent(episode) > 0.5 and not step.hypothesis:
                return Phase.ESCALATE

        # DIAGNOSE transitions
        elif current == Phase.DIAGNOSE:
            if step.evaluation == 'PASS' and step.lesson:
                return Phase.EXECUTE
            if self._hypothesis_invalidated(episode, step):
                return Phase.EXPLORE
            if self._diagnostic_steps_count(episode) >= 5 and not step.root_cause:
                return Phase.ESCALATE

        # EXECUTE transitions
        elif current == Phase.EXECUTE:
            if self._success_criteria_met(episode, step):
                return Phase.CONSOLIDATE
            if self._consecutive_failures(episode) >= 2:
                return Phase.DIAGNOSE
            if self._budget_exhausted(episode):
                return Phase.ESCALATE

        # CONSOLIDATE transitions
        elif current == Phase.CONSOLIDATE:
            if self._distillations_generated(episode):
                return None  # Episode complete
            if step.evaluation == 'FAIL':
                return Phase.EXECUTE

        return None  # No transition

    def _budget_percent(self, episode: Episode) -> float:
        return len(episode.steps) / episode.budget_steps

    def _budget_exhausted(self, episode: Episode) -> bool:
        return len(episode.steps) >= episode.budget_steps

    def _consecutive_failures(self, episode: Episode) -> int:
        count = 0
        for step in reversed(episode.steps):
            if step.evaluation == 'FAIL':
                count += 1
            else:
                break
        return count
```

### Phase Violation Handling

If an action is attempted that violates current phase:

```python
PHASE_ALLOWED_ACTIONS = {
    Phase.EXPLORE: {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch', 'AskUser'},
    Phase.DIAGNOSE: {'Read', 'Glob', 'Grep', 'Bash:read-only', 'Test'},
    Phase.EXECUTE: {'Read', 'Edit', 'Write', 'Bash', 'Test'},
    Phase.CONSOLIDATE: {'Read', 'Reflect', 'Distill'},
    Phase.ESCALATE: {'Summarize', 'AskUser'},
}

def check_phase_violation(episode: Episode, action: str) -> Optional[str]:
    allowed = PHASE_ALLOWED_ACTIONS.get(episode.phase, set())
    if action not in allowed:
        return f"Action '{action}' not allowed in phase '{episode.phase}'. Allowed: {allowed}"
    return None
```

---

## 6. Compounding Rate Query

The north star metric with concrete SQL.

### Primary Metric

```sql
-- COMPOUNDING RATE
-- (Episodes where reused memory led to success) / (Total completed episodes)

WITH episode_memory_usage AS (
    SELECT
        e.episode_id,
        e.outcome,
        -- Did this episode use any memory?
        COALESCE(SUM(s.memory_cited), 0) > 0 as used_memory,
        -- Was the memory useful?
        COALESCE(SUM(CASE WHEN s.memory_useful = 1 THEN 1 ELSE 0 END), 0) > 0 as memory_was_useful
    FROM episodes e
    LEFT JOIN steps s ON s.episode_id = e.episode_id
    WHERE e.outcome IS NOT NULL  -- Completed episodes only
    GROUP BY e.episode_id, e.outcome
)
SELECT
    COUNT(*) as total_episodes,
    SUM(CASE WHEN used_memory THEN 1 ELSE 0 END) as episodes_using_memory,
    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful_episodes,
    SUM(CASE WHEN used_memory AND memory_was_useful AND outcome = 'SUCCESS' THEN 1 ELSE 0 END) as memory_led_to_success,

    -- THE NORTH STAR
    ROUND(
        100.0 * SUM(CASE WHEN used_memory AND memory_was_useful AND outcome = 'SUCCESS' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0)
    , 1) as compounding_rate_pct
FROM episode_memory_usage;
```

### Supporting Metrics

```sql
-- REUSE RATE: % of steps that cited retrieved memory
SELECT
    COUNT(*) as total_steps,
    SUM(CASE WHEN retrieved_memories IS NOT NULL AND retrieved_memories != '[]' THEN 1 ELSE 0 END) as steps_with_retrieval,
    SUM(memory_cited) as steps_citing_memory,
    ROUND(100.0 * SUM(memory_cited) / NULLIF(COUNT(*), 0), 1) as reuse_rate_pct
FROM steps
WHERE episode_id IN (SELECT episode_id FROM episodes WHERE outcome IS NOT NULL);

-- MEMORY EFFECTIVENESS: Win rate with memory vs without
SELECT
    'With Memory' as condition,
    COUNT(*) as episodes,
    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as success_rate_pct
FROM episodes e
WHERE EXISTS (
    SELECT 1 FROM steps s
    WHERE s.episode_id = e.episode_id AND s.memory_cited = 1
)
AND e.outcome IS NOT NULL

UNION ALL

SELECT
    'Without Memory' as condition,
    COUNT(*) as episodes,
    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as success_rate_pct
FROM episodes e
WHERE NOT EXISTS (
    SELECT 1 FROM steps s
    WHERE s.episode_id = e.episode_id AND s.memory_cited = 1
)
AND e.outcome IS NOT NULL;

-- LOOP SUPPRESSION: Average retries before success
SELECT
    ROUND(AVG(retry_count), 1) as avg_retries,
    MAX(retry_count) as max_retries,
    COUNT(CASE WHEN retry_count > 3 THEN 1 END) as episodes_over_threshold
FROM (
    SELECT
        e.episode_id,
        COUNT(CASE WHEN s.evaluation = 'FAIL' THEN 1 END) as retry_count
    FROM episodes e
    JOIN steps s ON s.episode_id = e.episode_id
    WHERE e.outcome = 'SUCCESS'
    GROUP BY e.episode_id
);

-- DISTILLATION QUALITY: Rules that proved useful when reused
SELECT
    d.type,
    COUNT(*) as total_distillations,
    SUM(d.times_retrieved) as total_retrievals,
    SUM(d.times_used) as total_uses,
    SUM(d.times_helped) as total_helped,
    ROUND(100.0 * SUM(d.times_helped) / NULLIF(SUM(d.times_used), 0), 1) as effectiveness_pct
FROM distillations d
GROUP BY d.type;
```

### Weekly Intelligence Report Query

```sql
-- WEEKLY INTELLIGENCE REPORT
WITH this_week AS (
    SELECT
        date(start_ts, 'unixepoch') as day,
        COUNT(*) as episodes,
        SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successes
    FROM episodes
    WHERE start_ts > unixepoch() - 604800  -- Last 7 days
    GROUP BY date(start_ts, 'unixepoch')
),
new_distillations AS (
    SELECT
        type,
        COUNT(*) as count
    FROM distillations
    WHERE created_at > unixepoch() - 604800
    GROUP BY type
)
SELECT
    'Episodes' as metric,
    SUM(episodes) as value
FROM this_week
UNION ALL
SELECT 'Success Rate %', ROUND(100.0 * SUM(successes) / NULLIF(SUM(episodes), 0), 1) FROM this_week
UNION ALL
SELECT 'New Heuristics', COALESCE((SELECT count FROM new_distillations WHERE type = 'HEURISTIC'), 0)
UNION ALL
SELECT 'New Sharp Edges', COALESCE((SELECT count FROM new_distillations WHERE type = 'SHARP_EDGE'), 0)
UNION ALL
SELECT 'New Anti-Patterns', COALESCE((SELECT count FROM new_distillations WHERE type = 'ANTI_PATTERN'), 0)
UNION ALL
SELECT 'New Playbooks', COALESCE((SELECT count FROM new_distillations WHERE type = 'PLAYBOOK'), 0);
```

---

## 7. Migration Path

How to transition from current Spark to EIDOS.

### Phase 1: Schema Creation (Day 1)

```sql
-- Create new tables alongside existing system
-- Old system continues to work during migration

CREATE TABLE IF NOT EXISTS episodes (...);
CREATE TABLE IF NOT EXISTS steps (...);
CREATE TABLE IF NOT EXISTS distillations (...);
CREATE TABLE IF NOT EXISTS policies (...);
CREATE TABLE IF NOT EXISTS evidence (...);
```

### Phase 2: Data Migration (Days 2-3)

#### Migrate Cognitive Insights to Distillations

```python
import json
from pathlib import Path

def migrate_cognitive_insights():
    """Migrate cognitive_insights.json → distillations table"""

    insights_path = Path.home() / '.spark' / 'cognitive_insights.json'
    if not insights_path.exists():
        return

    with open(insights_path) as f:
        insights = json.load(f)

    # Category → Type mapping
    TYPE_MAP = {
        'SELF_AWARENESS': 'HEURISTIC',
        'USER_UNDERSTANDING': 'POLICY',
        'REASONING': 'HEURISTIC',
        'CONTEXT': 'SHARP_EDGE',
        'WISDOM': 'HEURISTIC',
        'META_LEARNING': 'HEURISTIC',
        'COMMUNICATION': 'POLICY',
        'CREATIVITY': 'PLAYBOOK',
    }

    for insight in insights:
        distillation = {
            'distillation_id': f"migrated_{insight.get('id', uuid4().hex[:8])}",
            'type': TYPE_MAP.get(insight.get('category'), 'HEURISTIC'),
            'statement': insight.get('insight'),
            'applicability': json.dumps({
                'context': insight.get('context'),
                'migrated_from': 'cognitive_insights'
            }),
            'source_steps': json.dumps([]),  # No step linkage for migrated
            'validation_count': insight.get('times_validated', 0),
            'confidence': insight.get('reliability', 0.5),
            'created_at': insight.get('created_at'),
        }

        # Insert into distillations table
        insert_distillation(distillation)
```

#### Archive Old Pattern Data

```python
def archive_patterns():
    """Move detected_patterns.jsonl to archive (informational only)"""

    patterns_path = Path.home() / '.spark' / 'detected_patterns.jsonl'
    archive_path = Path.home() / '.spark' / 'archive' / 'patterns_pre_eidos.jsonl'

    if patterns_path.exists():
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        patterns_path.rename(archive_path)
```

#### Link Existing Outcomes

```python
def link_outcomes_to_steps():
    """Best-effort link of outcome_log.jsonl to steps via timestamps"""

    # This is approximate - outcomes may not have direct step linkage
    # Keep outcome_log.jsonl as reference but don't migrate directly
    pass
```

### Phase 3: Code Migration (Days 4-7)

| Current Module | Migration Action |
|----------------|------------------|
| `lib/cognitive_learner.py` | Replace with `lib/distillation_engine.py` |
| `lib/importance_scorer.py` | Absorb into `lib/memory_gate.py` |
| `lib/validation_loop.py` | Absorb into `lib/control_plane.py` |
| `lib/prediction_loop.py` | Absorb into Step schema enforcement |
| `lib/pattern_detection/` | Simplify; becomes distillation triggers |
| `lib/outcome_log.py` | Replace with Step.evaluation flow |
| `lib/aha_tracker.py` | Replace with Step.surprise_level |
| `hooks/observe.py` | Extend to capture full Step envelope |

### Phase 4: Parallel Running (Week 2)

```python
# Run both systems in parallel for 1 week
# Compare outputs, validate EIDOS captures everything important

class DualModeCapture:
    def capture(self, event):
        # Old system (read-only after migration)
        old_result = self.old_system.capture(event)

        # New EIDOS system
        new_result = self.eidos_system.capture(event)

        # Log discrepancies for review
        if self._significant_difference(old_result, new_result):
            self.log_discrepancy(event, old_result, new_result)

        return new_result  # EIDOS is source of truth
```

### Phase 5: Cutover (Week 3)

1. Stop writing to old system
2. Archive old data files
3. Remove old code paths
4. Update CLI commands
5. Update dashboard

### Backward Compatibility Period

```python
# Keep read-only access to old data for 30 days

class LegacyReader:
    """Read-only access to pre-EIDOS data during transition"""

    def __init__(self):
        self.insights_path = Path.home() / '.spark' / 'cognitive_insights.json.backup'
        self.cutover_date = datetime(2026, 2, 15)

    def get_legacy_insight(self, query: str) -> Optional[dict]:
        if datetime.now() > self.cutover_date + timedelta(days=30):
            return None  # Legacy access expired

        # Search legacy data
        ...
```

### Rollback Plan

If EIDOS has critical issues:

```bash
# Restore old system
cp ~/.spark/archive/cognitive_insights.json.backup ~/.spark/cognitive_insights.json
git checkout pre-eidos -- lib/cognitive_learner.py lib/importance_scorer.py

# Disable EIDOS
export SPARK_EIDOS_ENABLED=false
```

### Migration Checklist

- [ ] Create EIDOS tables in SQLite
- [ ] Migrate cognitive_insights.json → distillations
- [ ] Archive detected_patterns.jsonl
- [ ] Archive outcome_log.jsonl
- [ ] Create new lib/episode.py
- [ ] Create new lib/step.py
- [ ] Create new lib/distillation_engine.py
- [ ] Create new lib/control_plane.py
- [ ] Create new lib/memory_gate.py
- [ ] Extend hooks/observe.py for Step capture
- [ ] Update CLI commands
- [ ] Update dashboard
- [ ] Run parallel for 1 week
- [ ] Validate compounding rate calculable
- [ ] Cutover to EIDOS-only
- [ ] Remove legacy code after 30 days

---

## Summary

These additions complete the EIDOS architecture:

| Addition | Purpose |
|----------|---------|
| Guardrail 6 | Prevents random-walk debugging |
| Layer 0 (Evidence) | Keeps audit trail without polluting memory |
| Escalation Definition | Makes "stuck" a structured, useful state |
| Validation Methods | Ensures every step is verifiable |
| Phase Transitions | Makes phases mechanical, not optional |
| Compounding Rate SQL | Makes the north star measurable |
| Migration Path | Gets from current Spark to EIDOS safely |

With these additions, EIDOS_ARCHITECTURE.md + EIDOS_ARCHITECTURE_ADDITIONS.md form a complete, implementable specification.
