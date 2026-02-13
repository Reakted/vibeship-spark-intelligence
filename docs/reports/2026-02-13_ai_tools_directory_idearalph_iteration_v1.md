# IdeaRalph Iteration v1: Spark As A Story-First AI Tools Directory

## One-liner
Build a directory of best AI tools where each tool page is a user-centric storytelling experience backed by timestamped benchmark charts, and keep it continuously updated by Spark (with strict evidence + freshness rules).

## Why This Matters
Most "AI tool directories" are link lists or SEO pages. Users don't need more links; they need:
- the right tool for their job-to-be-done
- the tradeoffs and "gotchas" up front
- proof (benchmarks, capability deltas, reliability notes) with dates and sources
- a way to stay current as the space changes weekly

If Spark can do this well, it becomes less "prompt-based search" and more like a living, trustworthy guide.

## Target Audience (JTBD)
- Builders: "I need to ship X (video, image, code) and I need the best tool today."
- Creators: "I want a workflow that gets me consistent quality without deep ML knowledge."
- Teams: "I need a defensible recommendation with evidence, cost, and risk."

## Initial Lanes (MVP Categories)
Start with 3 lanes where changes are rapid and benchmarks are meaningful:
1. Video coding / video generation tools
2. Image generation tools
3. Coding agents / IDE copilots

## The Page Experience (Storytelling Template)
Every tool page follows the same shape so users can skim, but the narrative feels human:

1. Cold open (the problem)
   - A short scenario: what the user is trying to do and what usually fails.

2. The "why this tool" moment
   - 3-5 bullets: what it is uniquely good at, in plain language.

3. Fit map
   - "Best for", "Not for", "If you care about X, choose Y instead"

4. The workflow
   - A minimal workflow (3-7 steps) with the tool in context.
   - Include concrete outputs: what to expect after each step.

5. Benchmarks + charts (with timestamps)
   - Show the latest known benchmark snapshots we have.
   - Explicitly show "Last updated: YYYY-MM-DD" and cite sources.
   - If a benchmark is missing or stale, say so.

6. Cost + constraints
   - Pricing model summary, rate limits, caps, or reliability notes.

7. Risks + guardrails
   - Safety constraints, misuse risk, privacy posture, policy constraints.

8. Decision
   - A simple final recommendation with alternatives.

## Data Model (So We Do Not Lie)
Split content into:
- Narrative content (handwritten or Spark-generated but reviewable): Markdown blocks.
- Evidence content: structured JSON with explicit source metadata.

Minimum evidence schema for any chart row:
- metric_name
- value
- dataset / benchmark name
- run_date (YYYY-MM-DD)
- source_url (or source_id + reference text)
- notes (what was measured, caveats)

Hard rule: no "latest" claim without a date.

## Update System (How Spark Keeps It Fresh)
Nightly or on-demand update job:
- Fetch benchmark sources (or ingest from curated feeds)
- Store snapshots with timestamps
- Recompute charts
- Flag pages with stale evidence (e.g., > 30 days for fast-moving categories)

Publish loop:
- If evidence changed materially, open a "page update" task with:
  - what changed
  - what assumptions are now wrong
  - what narrative sections need rewrite

## Opportunity Scanner Integration (Self-Evolution Loop)
Run Opportunity Scanner against:
- Spark's own build work (self-opportunities)
- Each tool page draft/update (content quality opportunities)

Key "Socratic" checks to enforce:
- verification_gap: Do we have proof for any performance claim?
- outcome_clarity: Is the page optimized for a user's decision outcome?
- assumption_audit: Are we assuming the benchmark generalizes?
- reversibility: Can we roll back a bad recommendation?
- humanity_guardrail: Are we encouraging harmful misuse?
- compounding_learning: Did we capture a reusable pattern for future pages?

Operational rule:
- If page context is thin, the scanner emits nothing (no spam).
- If context is rich, Minimax can propose 1-3 novel improvements (LLM cooldown enforced).

## Guardrails (Commercial Trust)
- No telemetry harvesting. No user tracking required for "recommendations".
- No affiliate bias by default. If affiliate links are ever added, disclose explicitly per page.
- No silent edits: every change ties back to evidence snapshots and a visible update date.
- Do not recommend tools for disallowed use cases (safety policy aligned with Spark Consciousness).

## Success Metrics (MVP)
User-facing:
- time-to-decision (how fast a user picks a tool)
- downstream success (self-reported: did the tool work for their use case)
- return rate (do they come back weekly)

System-facing:
- evidence freshness coverage (% pages with evidence updated in last N days)
- scanner novelty rate (unique opportunities / total)
- Minimax contribution SLO: >= 1 persisted LLM opportunity per 10 contextful cycles

## MVP Scope (2-week build)
- 3 categories, 5 tools each (15 pages)
- 1 benchmark chart per category (even if initially sparse, show timestamps + gaps)
- A simple navigation + search
- A single update pipeline stub that writes evidence snapshots and marks stale pages

## Open Questions
- Which benchmark sources are "trusted enough" for each category?
- Do we want separate "lab tests" vs "real-world workflow" evidence tracks?
- What is the review workflow (human approvals) before publishing updates?

## Next Build Steps (If Approved)
1. Create content/evidence file structure and page renderer.
2. Implement benchmark snapshot ingestion (start with 1-2 sources per category).
3. Wire Opportunity Scanner into content update flow (quality gates + novelty).
4. Add a public "Last updated" and "Evidence sources" section on every page.
