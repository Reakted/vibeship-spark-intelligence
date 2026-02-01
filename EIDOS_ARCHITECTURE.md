# EIDOS Architecture: Self-Evolving Intelligence System

**EIDOS** = Explicit Intelligence with Durable Outcomes & Semantics

This document defines the architecture for a system that **measurably improves decision-making quality over time**.

---

## The Core Problem We're Solving

Current Spark is stuck in a pattern:
1. It **thrashes** (fix loops, rabbit holes)
2. It **forgets to write** (stops storing)
3. It **doesn't read what it wrote** (retrieval isn't binding)
4. So intelligence **doesn't compound** — it plateaus

The fix is not "better memory" — it's **control loops + hard gates**.

---

## Success Metrics (Non-Negotiable)

If these don't move upward, the system is NOT learning:

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **Reuse Rate** | % of episodes that used prior distillations | >40% |
| **Outcome Improvement** | Time-to-success decreases for similar tasks | -20%/month |
| **Loop Suppression** | Fix-loop depth trends downward | <3 retries |
| **Policy Drift** | Explicit rules change behavior | >5 rules/week |
| **Distillation Quality** | Rules that proved useful when reused | >60% |

---

## Core Objects (The Intelligence Primitives)

### 1. Episode (Bounded Learning Unit)

```yaml
episode:
  episode_id: string
  goal: string                    # What we're trying to achieve
  constraints: list[string]       # What we must respect
  success_criteria: string        # How we know we're done
  budget:
    max_steps: int               # Hard limit
    max_time_seconds: int        # Hard limit
    max_retries_per_error: int   # Default 3
  phase: enum                     # EXPLORE | DIAGNOSE | EXECUTE | CONSOLIDATE | ESCALATE
  start_ts: timestamp
  end_ts: timestamp
  outcome: SUCCESS | FAILURE | PARTIAL | ESCALATED
  final_evaluation: string
```

### 2. Step (Atomic Intelligence Unit)

This is the **decision packet** — the core substrate for learning.

```yaml
step:
  step_id: string
  episode_id: string

  # BEFORE ACTION (mandatory)
  intent: string                  # What I'm trying to accomplish
  decision: string                # What I chose to do
  alternatives: list[string]      # What I considered but didn't do
  assumptions: list[string]       # What must be true for this to work
  prediction: string              # What I expect to happen
  confidence_before: float        # 0-1, how sure I am

  # THE ACTION
  action_type: string             # TOOL_CALL | REASONING | QUESTION | WAIT
  action_details: json            # Minimal provenance, not full logs

  # AFTER ACTION (mandatory)
  result: string                  # What actually happened
  evaluation: PASS | FAIL | PARTIAL | UNKNOWN
  surprise_level: float           # 0-1, how different from prediction
  lesson: string                  # 1-3 bullets, what we learned
  confidence_after: float         # Updated confidence

  # MEMORY BINDING (mandatory)
  retrieved_memories: list[string]  # What was retrieved before this step
  memory_cited: bool              # Did we actually use retrieved memory?
  memory_useful: bool             # Was the memory helpful?

  # VALIDATION (mandatory)
  validated: bool                 # Did we check the result?
  validation_method: string       # How we validated
```

### 3. Distillation (Where Intelligence Lives)

```yaml
distillation:
  distillation_id: string
  type: HEURISTIC | SHARP_EDGE | ANTI_PATTERN | PLAYBOOK | POLICY

  statement: string               # The rule itself
  applicability:
    domains: list[string]         # Where this applies
    triggers: list[string]        # When to retrieve this
    constraints: list[string]     # When NOT to apply

  evidence:
    source_steps: list[step_id]   # Steps that generated this
    validation_count: int         # Times this was validated
    contradiction_count: int      # Times this was wrong
    last_validated: timestamp

  confidence: float               # 0-1
  revalidate_by: timestamp        # When to re-check this

  # Usage tracking
  times_retrieved: int
  times_used: int                 # Actually influenced decision
  times_helped: int               # Led to success
```

### 4. Policy (Operating Constraints)

```yaml
policy:
  policy_id: string
  scope: GLOBAL | PROJECT | SESSION

  statement: string               # The constraint
  priority: int                   # Higher = more important
  source: USER | DISTILLED | INFERRED

  # Examples
  examples:
    - "Never commit without running tests"
    - "Ask before modifying .env files"
    - "User prefers minimal dependencies"
```

---

## The Five Layers

### Layer 1: Canonical Memory (SQLite)

**Source of truth. Simple. Inspectable. Debuggable.**

Tables:
- `episodes` - bounded learning units
- `steps` - decision packets
- `distillations` - extracted rules
- `policies` - operating constraints
- `entities` - projects, repos, services, people

This is NOT where tool logs go. Tool logs are ephemeral evidence.

### Layer 2: Semantic Index

Embeddings for retrieval:
- Steps (by intent, decision, lesson)
- Distillations (by statement, triggers)
- Policies (by statement)

Used ONLY for retrieval, never as truth.

### Layer 3: Control Plane (Critical)

This is NOT an LLM. This is deterministic enforcement.

```python
class ControlPlane:
    def enforce_budget(self, episode, step_count):
        if step_count >= episode.budget.max_steps:
            return PhaseChange.ESCALATE

    def detect_loop(self, episode, steps):
        # Same error signature 2+ times
        # Same file modified 3+ times
        # No new evidence in 5 steps
        # Confidence not improving
        return LoopDetected if triggered else None

    def require_memory_binding(self, step):
        if not step.retrieved_memories:
            return BlockAction("Must retrieve memory before acting")

    def enforce_validation(self, step):
        if not step.validated:
            return BlockCommit("Step must be validated")
```

### Layer 4: Reasoning Engine (LLM)

- Planning
- Hypothesis generation
- Reflection
- Summarization

**Constrained by the Control Plane.** The LLM proposes, the Control Plane disposes.

### Layer 5: Distillation Engine

Runs after every episode:

```python
class DistillationEngine:
    def post_episode_reflection(self, episode, steps):
        return {
            "bottleneck": "What was the real bottleneck?",
            "wrong_assumption": "Which assumption was wrong?",
            "preventive_check": "What check would have prevented this?",
            "new_rule": "What rule should we adopt permanently?",
            "stop_doing": "What should we stop doing?",
        }

    def generate_distillations(self, reflection, steps):
        # Create candidate rules
        # Link to evidence steps
        # Assign confidence
        # Set revalidation date
```

---

## Guardrails (Hard Gates)

### Guardrail 1: Progress Contract

Before any action, the agent must state:
- **Hypothesis**: What I think is wrong
- **Test**: What will confirm/deny
- **Expected Signal**: What changes if I'm right
- **Stop Condition**: What means "switch approach"
- **Max Attempts**: N

If it can't state these → **blocked from acting**.

### Guardrail 2: Memory Binding

**No action may execute without citing retrieved memory** (or explicitly stating none exists).

### Guardrail 3: Outcome Enforcement

Every step MUST end with:
- `result` filled
- `evaluation` filled
- `validated` = true OR `validation_method` = "deferred:reason"

No validation → step is invalid → doesn't count toward learning.

### Guardrail 4: Loop Watchers

| Watcher | Trigger | Action |
|---------|---------|--------|
| **Repeat Error** | Same failure signature 2x | Diagnostic phase + new hypothesis |
| **No-New-Info** | 5 steps without new evidence | Stop; create data-gather plan |
| **Diff Thrash** | Same file modified 3x | Freeze file, focus elsewhere |
| **Confidence Stagnation** | Confidence delta < 0.05 for 3 steps | Force alternative or escalate |
| **Memory Bypass** | Action without citing memory | Block action, require retrieval |

### Guardrail 5: Phase Control

Explicit modes (not LLM-decided):

```
EXPLORE → DIAGNOSE → EXECUTE → CONSOLIDATE → ESCALATE
```

Phase transitions are rule-driven:
- Budget hit → ESCALATE
- Loop detected → DIAGNOSE
- Success → CONSOLIDATE
- Stuck → ESCALATE

---

## Retrieval: Policy-First, Not Similarity-First

Stop searching by "similar text." Search by **usefulness**.

Retrieval order:
1. **Policies** - What must we respect here?
2. **Playbooks** - If task matches a known pattern
3. **Sharp Edges** - Stack/repo gotchas
4. **Relevant Episodes** - Only if needed

Retrieve by:
- Goal similarity
- Environment tags (repo/stack)
- Failure mode similarity ("timeout", "migration", "rate limit")

---

## Memory Gate: Earn the Right to Persist

Not everything becomes durable memory. Score a step:

| Signal | Weight |
|--------|--------|
| High impact (unblocked progress) | +0.3 |
| Novelty (new pattern) | +0.2 |
| Surprise (prediction ≠ outcome) | +0.3 |
| Recurrence (3+ times) | +0.2 |
| Irreversible (security, prod, funds) | +0.4 |

**Score > 0.5 → durable memory**
**Score < 0.5 → short-lived cache (24-72 hours)**

---

## Dashboard: See Intelligence Compounding

### 1. Progress Panel
- Active episode goal + success criteria
- Current phase
- Remaining budgets
- Latest hypothesis + test

### 2. Loop/Thrash Panel
- Repeat error count (top signatures)
- "No-new-info" streak
- Files most frequently edited
- Time without passing validation

### 3. Learning Panel (Most Important)
- New distillations this week
- Reused memories count
- Win rate: memory used vs not used
- Top memories by impact

### 4. Retrieval Quality Panel
- Hit rate (did we find anything?)
- Citation rate (did agent cite memory?)
- Precision (was it useful?)

### 5. Trust Panel
- % steps with validation evidence
- % steps with prediction → result filled
- Unvalidated claims waiting for re-check

---

## Implementation Priority

### Phase 1: Core Loop (Week 1)
- [ ] Step schema with mandatory fields
- [ ] Episode schema with budgets
- [ ] Basic control plane (budget enforcement)
- [ ] Mandatory prediction → result → evaluation

### Phase 2: Memory Binding (Week 2)
- [ ] Retrieval before action (mandatory)
- [ ] Memory citation tracking
- [ ] Memory usefulness tracking

### Phase 3: Distillation (Week 3)
- [ ] Post-episode reflection
- [ ] Distillation generation
- [ ] Evidence linking
- [ ] Revalidation scheduling

### Phase 4: Watchers (Week 4)
- [ ] Loop detection watchers
- [ ] Phase control automation
- [ ] Escalation triggers

### Phase 5: Dashboard (Week 5)
- [ ] Learning metrics
- [ ] Thrash detection
- [ ] Retrieval quality

---

## The North Star Metric

**Compounding Rate = (reused distillations that led to success) / (total episodes)**

If this number doesn't rise, we're not evolving.

---

## What This Replaces in Current Spark

| Current System | Replaced By |
|----------------|-------------|
| ImportanceScorer | Memory Gate |
| CognitiveLearner | Step + Distillation schema |
| ContradictionDetector | Distillation validation |
| CuriosityEngine | Reflection prompts |
| HypothesisTracker | Step.prediction → Step.result loop |
| Pattern detectors | Distillation triggers |

The new system is simpler in concept but more rigorous in enforcement.

---

## SQLite Schema (Minimal)

```sql
-- Episodes
CREATE TABLE episodes (
    episode_id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    constraints TEXT,  -- JSON
    success_criteria TEXT,
    budget_steps INTEGER DEFAULT 25,
    budget_seconds INTEGER DEFAULT 720,
    phase TEXT DEFAULT 'EXPLORE',
    outcome TEXT,
    start_ts REAL,
    end_ts REAL
);

-- Steps (the core intelligence unit)
CREATE TABLE steps (
    step_id TEXT PRIMARY KEY,
    episode_id TEXT REFERENCES episodes,

    -- Before action
    intent TEXT NOT NULL,
    decision TEXT NOT NULL,
    alternatives TEXT,  -- JSON
    assumptions TEXT,   -- JSON
    prediction TEXT NOT NULL,
    confidence_before REAL,

    -- Action
    action_type TEXT,
    action_details TEXT,  -- JSON (minimal)

    -- After action
    result TEXT,
    evaluation TEXT,
    surprise_level REAL,
    lesson TEXT,
    confidence_after REAL,

    -- Memory binding
    retrieved_memories TEXT,  -- JSON
    memory_cited INTEGER DEFAULT 0,
    memory_useful INTEGER,

    -- Validation
    validated INTEGER DEFAULT 0,
    validation_method TEXT,

    created_at REAL DEFAULT (unixepoch())
);

-- Distillations (where intelligence lives)
CREATE TABLE distillations (
    distillation_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- HEURISTIC, SHARP_EDGE, ANTI_PATTERN, PLAYBOOK, POLICY
    statement TEXT NOT NULL,
    applicability TEXT,  -- JSON

    source_steps TEXT,   -- JSON list of step_ids
    validation_count INTEGER DEFAULT 0,
    contradiction_count INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.5,

    times_retrieved INTEGER DEFAULT 0,
    times_used INTEGER DEFAULT 0,
    times_helped INTEGER DEFAULT 0,

    created_at REAL DEFAULT (unixepoch()),
    revalidate_by REAL
);

-- Policies (operating constraints)
CREATE TABLE policies (
    policy_id TEXT PRIMARY KEY,
    scope TEXT DEFAULT 'GLOBAL',
    statement TEXT NOT NULL,
    priority INTEGER DEFAULT 50,
    source TEXT DEFAULT 'INFERRED',
    created_at REAL DEFAULT (unixepoch())
);

-- Indexes for retrieval
CREATE INDEX idx_steps_episode ON steps(episode_id);
CREATE INDEX idx_distillations_type ON distillations(type);
CREATE INDEX idx_distillations_confidence ON distillations(confidence DESC);
```

---

## The Fundamental Shift

**Old thinking:** "How do we store more?"
**New thinking:** "How do we force learning?"

Intelligence = compression + reuse + behavior change.

Not storage. Not retrieval. **Enforcement.**
