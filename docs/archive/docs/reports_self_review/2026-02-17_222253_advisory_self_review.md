# Advisory Self-Review (2026-02-17T22:22:53.597733+00:00)

## Window
- Hours analyzed: 12.0
- State: improving

## Core Metrics
- Advisory rows: 33
- Advisory trace coverage: 17/33 (51.52%)
- Advice items emitted: 33
- Non-benchmark advisory rows: 33 (excluded 0)
- Engine events: 304
- Engine trace coverage: 304/304 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.1429
- Strict effectiveness rate: 1.0
- Trace mismatch count: 11

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `bec8f5a424df0efb` | tool `Write` | source `prefetch` | Use Read conservatively with fast validation and explicit rollback safety.
- `937be51f4b8ae5e9` | tool `Edit` | source `prefetch` | Use Edit conservatively with fast validation and explicit rollback safety.
- `f38840a55f3956bc` | tool `Bash` | source `self_awareness` | [Caution] Using python -X utf8 flag on Windows prevents UnicodeEncodeError with non-ASCII output in 95% of cases
- `a777a346c067fa3b` | tool `Edit` | source `cognitive` | Applied advisory: Fix service_control.py edits (ensure changes do not break startup)
- `16289c6c85538084` | tool `TaskUpdate` | source `cognitive` | Emergent AI behavior fascinates AND frightens people - transparent evolution with auditable memory wins trust
- `93f65002fb660ce3` | tool `TaskUpdate` | source `cognitive` | Emergent AI behavior fascinates AND frightens people - transparent evolution with auditable memory wins trust
- `168c398a4fcbbf4b` | tool `Write` | source `cognitive` | Write tool blocked: Could not create config.json - tool requires reading file first even if it doesnt exist. Had to use Python workaround.
- `60caafd37bd001c9` | tool `Write` | source `semantic-agentic` | I'm talking about how they use their login system and how they make agents be utilised through md files of agents joining through the curl system. They had also

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~69.69% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 12x (36.36%) Macro (often works): Edit→Edit→Edit. Use this sequence when appropriate to reduce thrash.
- 3x (9.09%) Applied advisory: Fix service_control.py edits (ensure changes do not break startup)
- 2x (6.06%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 2x (6.06%) Use Bash conservatively with fast validation and explicit rollback safety.
- 2x (6.06%) Never log secrets or tokens; redact sensitive data in logs.
- 2x (6.06%) Use Edit conservatively with fast validation and explicit rollback safety.

## Top Repeated Advice (Non-Benchmark Window)
- 12x (36.36%) Macro (often works): Edit→Edit→Edit. Use this sequence when appropriate to reduce thrash.
- 3x (9.09%) Applied advisory: Fix service_control.py edits (ensure changes do not break startup)
- 2x (6.06%) [Caution] Reading files before editing consistently prevents data loss and reduces failed edits by 40% in observed sessions
- 2x (6.06%) Use Bash conservatively with fast validation and explicit rollback safety.
- 2x (6.06%) Never log secrets or tokens; redact sensitive data in logs.
- 2x (6.06%) Use Edit conservatively with fast validation and explicit rollback safety.

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
