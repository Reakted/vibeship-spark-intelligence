# Report: Validation Batch Status + Blockers
Date: 2026-02-11
Owner: Spark

## Context
After shipping hybrid+agentic retrieval, we initiated immediate validation before resuming remaining backlog work.

## What was validated
1. Fixed follow-up prompt regression that broke pipeline execution:
   - `KeyError: 'decision, status, reason'` from unescaped braces in template.
   - Fix shipped in `spark-forge` commit `4ca3551`.
2. Added regression coverage to prevent repeat:
   - `tests/test_followup.py` new decision-contract prompt test.
   - Test run: `python -m pytest tests/test_followup.py -q` → `6 passed`.
   - Commit `7650046`.

## Runtime blockers during live batch
- Kimi path failed due missing API key (`KIMI_API_KEY`).
- Ollama fallback unavailable (`404` on local endpoint).
- Opus provider run path stalled in this environment (needs separate provider readiness check).

## Decision
- Keep current retrieval changes.
- Treat provider readiness as an operational blocker, not a design blocker.
- Next: run a provider-readiness micro-check (keys + reachable backends), then re-run short validation batch and compare trend metrics.

## Confidence
high
