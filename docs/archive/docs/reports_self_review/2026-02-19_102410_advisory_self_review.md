# Advisory Self-Review (2026-02-19T10:24:10.331089+00:00)

## Window
- Hours analyzed: 12.0
- State: unclear

## Core Metrics
- Advisory rows: 6
- Advisory trace coverage: 6/6 (100.0%)
- Advice items emitted: 6
- Non-benchmark advisory rows: 6 (excluded 0)
- Engine events: 124
- Engine trace coverage: 124/124 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.0
- Strict effectiveness rate: None
- Trace mismatch count: 6

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `268cb9967c49d561` | tool `Grep` | source `prefetch` | Before Grep, verify schema and contract compatibility to avoid breaking interfaces.
- `5a473afa82dafae5` | tool `Bash` | source `prefetch` | Use Bash conservatively with fast validation and explicit rollback safety.
- `7a5eb6bfc8675601` | tool `Read` | source `self_awareness` | [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- `e55b39047cffa447` | tool `Read` | source `prefetch` | Before Read, verify schema and contract compatibility to avoid breaking interfaces.
- `251f23ddecdbef16` | tool `WebFetch` | source `cognitive` | Hi Claude, we were doing certain upgrades on spawner UI so that spawner UI can actually orchestrate many LLM at the same time. Can you actually become the orche
- `c6e601d1a38cb4ed` | tool `Bash` | source `prefetch` | Use reversible steps for Bash and verify rollback conditions first.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~100.02% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 1x (16.67%) Use reversible steps for Bash and verify rollback conditions first.
- 1x (16.67%) Hi Claude, we were doing certain upgrades on spawner UI so that spawner UI can actually orchestrate many LLM at the same time. Can you actually become the orche
- 1x (16.67%) Before Read, verify schema and contract compatibility to avoid breaking interfaces.
- 1x (16.67%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 1x (16.67%) Use Bash conservatively with fast validation and explicit rollback safety.
- 1x (16.67%) Before Grep, verify schema and contract compatibility to avoid breaking interfaces.

## Top Repeated Advice (Non-Benchmark Window)
- 1x (16.67%) Use reversible steps for Bash and verify rollback conditions first.
- 1x (16.67%) Hi Claude, we were doing certain upgrades on spawner UI so that spawner UI can actually orchestrate many LLM at the same time. Can you actually become the orche
- 1x (16.67%) Before Read, verify schema and contract compatibility to avoid breaking interfaces.
- 1x (16.67%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 1x (16.67%) Use Bash conservatively with fast validation and explicit rollback safety.
- 1x (16.67%) Before Grep, verify schema and contract compatibility to avoid breaking interfaces.

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
