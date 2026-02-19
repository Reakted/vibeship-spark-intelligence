# Advisory Self-Review (2026-02-19T15:34:24.583699+00:00)

## Window
- Hours analyzed: 12.0
- State: unclear

## Core Metrics
- Advisory rows: 417
- Advisory trace coverage: 385/417 (92.33%)
- Advice items emitted: 426
- Non-benchmark advisory rows: 418 (excluded 0)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.17
- Strict effectiveness rate: 0.7059
- Trace mismatch count: 49

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `spark-auto-s1-edit-1771515264384` | tool `Edit` | source `packet` | Use packet guidance.
- `spark-auto-s7-read-1771515244165` | tool `Read` | source `advisor` | Note-level guidance.
- `spark-auto-s6-edit-1771515244051` | tool `Edit` | source `advisor` | Warning-level guidance.
- `trace-auto-1` | tool `Read` | source `advisor` | Trace-linked live guidance.
- `spark-auto-s2d-read-1771515243637` | tool `Read` | source `cognitive` | Fallback from emitted advice text.
- `spark-auto-s2b-read-1771515243521` | tool `Read` | source `advisor` | Live guidance with policy.
- `spark-auto-s2-read-1771515243388` | tool `Read` | source `advisor` | Live guidance.
- `spark-auto-s1-edit-1771515243226` | tool `Edit` | source `packet` | Use packet guidance.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~46.73% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 34x (7.98%) Use packet guidance.
- 33x (7.75%) Live guidance.
- 33x (7.75%) Live guidance with policy.
- 33x (7.75%) Fallback from emitted advice text.
- 33x (7.75%) Trace-linked live guidance.
- 33x (7.75%) Warning-level guidance.

## Top Repeated Advice (Non-Benchmark Window)
- 34x (7.96%) Use packet guidance.
- 34x (7.96%) Live guidance.
- 33x (7.73%) Live guidance with policy.
- 33x (7.73%) Fallback from emitted advice text.
- 33x (7.73%) Trace-linked live guidance.
- 33x (7.73%) Warning-level guidance.

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
