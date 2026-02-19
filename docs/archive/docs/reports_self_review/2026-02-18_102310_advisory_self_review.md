# Advisory Self-Review (2026-02-18T10:23:10.284725+00:00)

## Window
- Hours analyzed: 12.0
- State: improving

## Core Metrics
- Advisory rows: 27
- Advisory trace coverage: 9/27 (33.33%)
- Advice items emitted: 38
- Non-benchmark advisory rows: 27 (excluded 0)
- Engine events: 179
- Engine trace coverage: 179/179 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.2857
- Strict effectiveness rate: 1.0
- Trace mismatch count: 4

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `direct-probe-in` | tool `OpenClawLLM` | source `trigger` | Validate authentication inputs server-side and avoid trusting client checks.
- `e71c4f840a2648e6` | tool `Read` | source `self_awareness` | [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- `7b25469ba78c9842` | tool `Bash` | source `prefetch` | Use Bash conservatively with fast validation and explicit rollback safety.
- `e7dc6d1643b7ab66` | tool `Bash` | source `prefetch` | Use Bash conservatively with fast validation and explicit rollback safety.
- `03c5b7a6e91e9d2a` | tool `Write` | source `prefetch` | Use Edit to align with existing project patterns before broad edits.
- `6f39c045b1bba4a5` | tool `Task` | source `prefetch` | Before Grep, verify schema and contract compatibility to avoid breaking interfaces.
- `openclaw-runtime-audit-1771371641515-t1` | tool `Edit` | source `prefetch` | Before Edit, verify schema and contract compatibility to avoid breaking interfaces.
- `openclaw-runtime-audit-1771371576951-t1` | tool `Edit` | source `semantic-agentic` | Remember this because it is critical: prefer rollback-safe integration first. I am confused about contract drift and this is not clear.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~84.2% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 9x (23.68%) Remember this because it is critical: I prefer rollback-safe minimal integration fixes first when incidents happen. I am confused when contracts drift unexpecte
- 8x (21.05%) Macro (often works): Edit→Edit→Edit. Use this sequence when appropriate to reduce thrash.
- 7x (18.42%) Remember this because it is critical: prefer rollback-safe integration first. I am confused about contract drift and this is not clear.
- 4x (10.53%) Macro (often works): Bash→Read→Grep. Use this sequence when appropriate to reduce thrash.
- 2x (5.26%) Consider skill [Team Communications]: Your team can't execute what they don't understand. And they won't buy in to what they don't feel part of. Internal comm
- 2x (5.26%) Use Bash conservatively with fast validation and explicit rollback safety.

## Top Repeated Advice (Non-Benchmark Window)
- 9x (23.68%) Remember this because it is critical: I prefer rollback-safe minimal integration fixes first when incidents happen. I am confused when contracts drift unexpecte
- 8x (21.05%) Macro (often works): Edit→Edit→Edit. Use this sequence when appropriate to reduce thrash.
- 7x (18.42%) Remember this because it is critical: prefer rollback-safe integration first. I am confused about contract drift and this is not clear.
- 4x (10.53%) Macro (often works): Bash→Read→Grep. Use this sequence when appropriate to reduce thrash.
- 2x (5.26%) Consider skill [Team Communications]: Your team can't execute what they don't understand. And they won't buy in to what they don't feel part of. Internal comm
- 2x (5.26%) Use Bash conservatively with fast validation and explicit rollback safety.

## Bad Outcome Records
- None in this window.

## Optimization (No New Features)
- Increase advisory repeat cooldowns and tool cooldowns to reduce duplicate cautions.
- Keep `include_mind=true` with stale gating and minimum salience to improve cross-session quality without flooding.
- Prefer fewer higher-rank items (`advisor.max_items` and `advisor.min_rank_score`) to improve signal density.
- Improve strict trace discipline in advisory engine events before trusting aggregate success counters.

## Questions To Ask Every Review
1. Which advisories changed a concrete decision, with trace IDs?
2. Which advisories repeated without adding new actionability?
3. Where did fallback dominate and why?
4. Which sources had strict-good outcomes vs non-strict optimism?
5. What is one simplification we can do before adding anything new?
