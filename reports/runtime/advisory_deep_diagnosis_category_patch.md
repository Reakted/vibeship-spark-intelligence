# Advisory Deep Diagnosis (Category Cooldown Patch)

Generated: 2026-02-22T22:20:12Z
Tuneables cutover unix: 1771798606

## Core Metrics
- Last hour outcomes: {'emitted': 7, 'blocked': 57}
- Last 24h outcomes: {'emitted': 780, 'blocked': 3395, 'error': 43}
- Post-cutover outcomes: {'emitted': 1, 'blocked': 6}
- Last 24h follow rate (followed/(followed+ignored)): 100.0%

## Suppression Drivers (24h)
- shown_ttl: 4012
- global_dedupe: 1363
- tool_cooldown: 513
- budget_exhausted: 470
- other: 160
- context_phase_guard: 37

## Top Suppression Reasons (24h)
- global_dedupe:text_sig: 1330
- budget exhausted (2 max): 470
- tool Bash on cooldown: 198
- tool Read on cooldown: 168
- test_suppressed: 74
- tool Edit on cooldown: 72
- shown 28s ago (TTL 600s): 57
- shown 54s ago (TTL 600s): 41
- shown 32s ago (TTL 600s): 39
- shown 12s ago (TTL 600s): 37
- deployment advice during exploration phase: 37
- shown 23s ago (TTL 600s): 36

## Budget Impact
- Suppressed items due to budget (24h): 470
- Suppressed items total (24h): 6555

## Global Dedupe Cooldown Observation
- cooldown=600.0s observed 3074 times

## New Cooldown Logic Verification
- Deterministic check reason: `shown 300s ago (TTL 756s, category=security)`

## High-Value Suppressed Samples
- No high-value sample list available (summary file missing or empty).

## Recommended Structure Upgrades
- Add a tuneable for global dedupe cooldown (currently appears fixed at 600s in runtime rows).
- Split emission budget into per-authority buckets (e.g., warning quota + note quota) so high-value warnings are not starved by low-priority notes.
- Add suppression reason telemetry with explicit category and cooldown scale to every blocked row for easier operator tuning.
- Introduce a deferred-emission queue: when budget blocks useful advice, carry top 1-2 into next tool boundary if still relevant.
- Add source-aware quotas (e.g., cap repeated baseline/eidos while reserving slots for security/mind/context when confidence is high).