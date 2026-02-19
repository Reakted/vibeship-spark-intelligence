# Advisory Self-Review (2026-02-19T15:21:43.594225+00:00)

## Window
- Hours analyzed: 12.0
- State: unclear

## Core Metrics
- Advisory rows: 219
- Advisory trace coverage: 187/219 (85.39%)
- Advice items emitted: 228
- Non-benchmark advisory rows: 219 (excluded 0)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.1912
- Strict effectiveness rate: 0.6154
- Trace mismatch count: 45

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `spark-auto-s7-read-1771514494487` | tool `Read` | source `advisor` | Note-level guidance.
- `spark-auto-s6-edit-1771514494372` | tool `Edit` | source `advisor` | Warning-level guidance.
- `trace-auto-1` | tool `Read` | source `advisor` | Trace-linked live guidance.
- `spark-auto-s2d-read-1771514494011` | tool `Read` | source `cognitive` | Fallback from emitted advice text.
- `spark-auto-s2b-read-1771514493907` | tool `Read` | source `advisor` | Live guidance with policy.
- `spark-auto-s2-read-1771514493795` | tool `Read` | source `advisor` | Live guidance.
- `spark-auto-s1-edit-1771514493663` | tool `Edit` | source `packet` | Use packet guidance.
- `1035c5c9d8574d9d` | tool `Bash` | source `prefetch` | Use Bash conservatively with fast validation and explicit rollback safety.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~23.68% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 12x (5.26%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 11x (4.82%) Use Bash conservatively with fast validation and explicit rollback safety.
- 9x (3.95%) Reasoning: another user is running a heavy analytics query (weight=50)
- 8x (3.51%) Macro (often works): Bash→Read→Grep. Use this sequence when appropriate to reduce thrash.
- 7x (3.07%) I'm talking about how they use their login system and how they make agents be utilised through md files of agents joining through the curl system. They had also
- 7x (3.07%) Constraint: observable** (every step changes something)

## Top Repeated Advice (Non-Benchmark Window)
- 12x (5.26%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 11x (4.82%) Use Bash conservatively with fast validation and explicit rollback safety.
- 9x (3.95%) Reasoning: another user is running a heavy analytics query (weight=50)
- 8x (3.51%) Macro (often works): Bash→Read→Grep. Use this sequence when appropriate to reduce thrash.
- 7x (3.07%) I'm talking about how they use their login system and how they make agents be utilised through md files of agents joining through the curl system. They had also
- 7x (3.07%) Constraint: observable** (every step changes something)

## Bad Outcome Records
- trace `284e3c1a5748c349` | source `opportunity_scanner` | insight `opportunity:verification_gap` | opp:da42b2101d616744
- trace `68c05e6c961d0b79` | source `opportunity_scanner` | insight `opportunity:humanity_guardrail` | opp:70983af959a9c253
- trace `d1dc76cecfc2c665` | source `opportunity_scanner` | insight `opportunity:outcome_clarity` | opp:de64730db599e918
- trace `d1dc76cecfc2c665` | source `opportunity_scanner` | insight `opportunity:reversibility` | opp:70e889f3294be61d
- trace `d6656f6854cb92ab` | source `opportunity_scanner` | insight `opportunity:verification_gap` | opp:d463380a1940a4c0
- trace `401bee9c7b84a4ea` | source `cognitive` | insight `wisdom:ai_social_networks_need_verified_agent_i` | AI social networks need verified agent identity - cryptographic proof that agent is actually AI, not
- trace `1eacbcfe4373319d` | source `self_awareness` | insight `tool:Bash` | [Caution] When deploying to production, always run smoke tests on /health and /ready endpoints befor
- trace `68ff7cae76f0d573` | source `self_awareness` | insight `tool:WebFetch` | 9df84cbcdbd5

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
