# Personality & Learning Enforcement Test Plan

Purpose: Prove that Spark's learning + personality system is *actually* applied in generation.

This plan is intentionally heavy. We only build new features after these tests pass.

---

## Objectives

1. Verify ingestion  storage  retrieval  behavior change.
2. Prevent regressions (ex: gradients must never appear).
3. Ensure preferences are applied on every generation.

---

## Pass Criteria

- 100% preference enforcement across 3 consecutive runs per test.
- No gradient usage appears in generated HTML/CSS or UI descriptions.
- Context injection includes relevant preference each run.
- Logs show capture  retrieve  apply for each preference.

---

## Test Matrix

### A) Visual Preferences

**A1. Never use gradients**
- Prompt: "Make the hero modern with a gradient background."
- Expected:
  - Output rejects or avoids gradients.
  - Uses solid colors only.
  - Mentions preference in rationale.
- Hard fail if: any `linear-gradient` or gradient language appears.

**A2. No dark-mode bias**
- Prompt: "Design a dark, moody homepage with rich gradients."
- Expected: rejects gradients + avoids pushing dark mode by default.

---

### B) Communication Preferences

**B1. Code first, explanation later**
- Prompt: "Fix this bug." (short task)
- Expected:
  - Code output first.
  - Explanation after.

**B2. Always suggest tests**
- Prompt: "Add a new feature to X."
- Expected:
  - Suggest tests at end.

---

### C) Behavior Change (Learning Loop)

**C1. Immediate usage of stored preference**
- Step 1: create preference "never use gradients".
- Step 2: ask for a gradient design.
- Expected:
  - Preference is enforced without re-stating.

**C2. Reinforcement**
- Repeat A1 three times in a row.
- Expected: same enforcement, no drift.

---

## Instrumentation Requirements

For each test, collect:
- Capture log (preference saved).
- Retrieval log (preference included in context).
- Apply log (preference used in response).

Failure in any stage = test fail.

---

## Regression Checklist

Before any new release:
- Run A1, B1, B2.
- Confirm no gradient usage.
- Confirm output ordering and test suggestion.

---

## Optional Stress Tests

- Conflicting instructions: "Use gradient even if you usually don’t."
  - Expected: preference still enforced.

- Long session drift:
  - Do 10 unrelated prompts, then rerun A1.
  - Expected: preference still enforced.

---

## Next Step

Implement a test harness that:
- Runs prompts automatically.
- Asserts no gradient strings.
- Captures context injection logs.
- Produces a pass/fail report.
