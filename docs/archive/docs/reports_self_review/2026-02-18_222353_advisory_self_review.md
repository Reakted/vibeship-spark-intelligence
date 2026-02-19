# Advisory Self-Review (2026-02-18T22:23:53.974694+00:00)

## Window
- Hours analyzed: 12.0
- State: unclear

## Core Metrics
- Advisory rows: 67
- Advisory trace coverage: 44/67 (65.67%)
- Advice items emitted: 72
- Non-benchmark advisory rows: 67 (excluded 0)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.3158
- Strict effectiveness rate: 0.75
- Trace mismatch count: 22

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `delta-run-20260218_212823-0008` | tool `Read` | source `self_awareness` | [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- `delta-run-20260218_212823-0004` | tool `Read` | source `self_awareness` | [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- `delta-run-20260218_212823-0000` | tool `Read` | source `self_awareness` | [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- `spark-auto-s7-read-1771442354148` | tool `Read` | source `advisor` | Note-level guidance.
- `spark-auto-s6-edit-1771442354049` | tool `Edit` | source `advisor` | Warning-level guidance.
- `trace-auto-1` | tool `Read` | source `advisor` | Trace-linked live guidance.
- `spark-auto-s2d-read-1771442353728` | tool `Read` | source `cognitive` | Fallback from emitted advice text.
- `spark-auto-s2b-read-1771442353603` | tool `Read` | source `advisor` | Live guidance with policy.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~41.67% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 10x (13.89%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 5x (6.94%) Macro (often works): Bash→Read→Grep. Use this sequence when appropriate to reduce thrash.
- 5x (6.94%) [Caution] When deploying to production, always run smoke tests on /health and /ready endpoints before enabling traffic because cold starts take 25s
- 4x (5.56%) Never log secrets or tokens; redact sensitive data in logs.
- 3x (4.17%) Validate authentication inputs server-side and avoid trusting client checks.
- 3x (4.17%) Assumption 'File exists at expected path' often wrong. Reality: Use Glob to search for files before operating on them

## Top Repeated Advice (Non-Benchmark Window)
- 10x (13.89%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 5x (6.94%) Macro (often works): Bash→Read→Grep. Use this sequence when appropriate to reduce thrash.
- 5x (6.94%) [Caution] When deploying to production, always run smoke tests on /health and /ready endpoints before enabling traffic because cold starts take 25s
- 4x (5.56%) Never log secrets or tokens; redact sensitive data in logs.
- 3x (4.17%) Validate authentication inputs server-side and avoid trusting client checks.
- 3x (4.17%) Assumption 'File exists at expected path' often wrong. Reality: Use Glob to search for files before operating on them

## Bad Outcome Records
- trace `962a1e3fc2cf6ce14e21` | source `opportunity_scanner` | insight `opportunity:verification_gap` | opp:0be624a4305d6a67
- trace `4095fb3cebea556b` | source `trigger` | insight `trigger:auth_security:25da832f` | Never log secrets or tokens; redact sensitive data in logs.
- trace `50fa9d249f3ae632` | source `opportunity_scanner` | insight `opportunity:outcome_clarity` | opp:399ab1975710a72c
- trace `50fa9d249f3ae632` | source `opportunity_scanner` | insight `opportunity:compounding_learning` | opp:edf3c8ac929ae100

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
