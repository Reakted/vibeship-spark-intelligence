# Mind Retrieval Alignment Update (2026-02-12)

## Why This Change

We found policy drift and attribution drift in active retrieval:

1. `advisory_engine` memory fusion honored `include_mind`, but live advisor retrieval did not.
2. Advisor cache keys ignored `include_mind`, causing mixed-policy cache reuse.
3. `SPARK_CONTEXT` rendered non-cognitive contextual items as `mind:*` even when source was `bank` or `taste`.

These three issues reduced trust in retrieval consistency and made debugging harder.

## What Was Implemented

### Code changes
- `lib/advisory_engine.py`
  - Live fallback call now forwards `include_mind=INCLUDE_MIND_IN_MEMORY`.

- `lib/advisor.py`
  - `advise_on_tool(...)` now accepts `include_mind` and forwards it.
  - cache key now includes `include_mind` to prevent mixed retrieval-cache reuse.
  - added Mind freshness controls:
    - `MIND_MAX_STALE_SECONDS` (`SPARK_ADVISOR_MIND_MAX_STALE_S`)
    - `MIND_STALE_ALLOW_IF_EMPTY` (`SPARK_ADVISOR_MIND_STALE_ALLOW_IF_EMPTY`)
    - `MIND_MIN_SALIENCE` (`SPARK_ADVISOR_MIND_MIN_SALIENCE`)
  - stale Mind can be skipped when local evidence exists, while still allowed as fallback when local evidence is empty.

- `lib/bridge.py`
  - fixed contextual rendering to preserve real source labels:
    - now outputs `[bank:...]`, `[taste:...]`, `[mind:...]` etc.
    - no longer collapses all non-cognitive rows to `mind:*`.

### Tests added
- `tests/test_advisory_dual_path_router.py`
  - verifies live path receives `include_mind` policy from advisory engine.

- `tests/test_advisor_mind_gate.py`
  - verifies stale Mind skip when local advice exists.
  - verifies stale Mind fallback when local advice is empty.
  - verifies cache key differs by `include_mind`.

- `tests/test_bridge_context_sources.py`
  - verifies SPARK_CONTEXT source labels reflect true provenance.

## Current Runtime Snapshot (local)

- advisory engine config: `include_mind=false`
- advisor Mind gate defaults: `mind_max_stale_s=0`, `mind_stale_allow_if_empty=true`, `mind_min_salience=0.5`
- Mind bridge stats:
  - `mind_available=true`
  - `last_sync=2026-02-05T17:26:53.727815`

24h advisor source mix (`~/.spark/advisor/recent_advice.jsonl`):
- `self_awareness`: 1349
- `cognitive`: 1232
- `semantic`: 215
- `semantic-agentic`: 154
- `convo`: 103
- `mind`: 8
- `semantic-hybrid`: 5
- `bank`: 1

Mind is currently low-share in advisory output.

## Recommendation (Cross-Session First)

Use a controlled Mind-on profile instead of always-off or always-on:

```json
{
  "advisory_engine": {
    "include_mind": true
  },
  "advisor": {
    "mind_max_stale_s": 172800,
    "mind_stale_allow_if_empty": true,
    "mind_min_salience": 0.55
  }
}
```

Why this profile:
- keeps cross-session memory available,
- avoids stale-overriding local context,
- preserves fallback behavior when local evidence is thin.

## Documentation Updated

- `TUNEABLES.md`
  - added advisor tuneables for Mind freshness/fallback/salience.
  - updated section map and example tuneables block.

- `Intelligence_Flow.md`
  - documented include_mind policy alignment and cache key fix.
  - documented new advisor Mind gating controls and env vars.

- `Intelligence_Flow_Map.md`
  - updated overview to include policy alignment + source attribution fix.
