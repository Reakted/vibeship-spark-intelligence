# Spark Intelligence Dashboard Playbook

Purpose: keep the control layer visible, enforceable, and traceable.

## Core rule
Every metric must drill down to `trace_id` -> steps -> evidence -> validation.

**Start Services**
Recommended (all services + dashboards):
1. `python -m spark.cli up`
2. Or `spark up`

Repo shortcuts:
1. `./scripts/run_local.sh`
2. Windows: `start_spark.bat`

Dashboard only (no background workers):
1. `python dashboard.py`

Stop services:
1. `python -m spark.cli down`
2. Or `spark down`

Ports:
1. Spark Lab dashboard: `http://localhost:8585`
2. Spark Pulse (chips/tuneables): `http://localhost:8765`
3. sparkd health: `http://127.0.0.1:8787/health`
4. Mind server health (if running): `http://127.0.0.1:8080/health`

**Dashboards (Spark Lab)**
Mission Control (default):
1. `/` or `/mission`
2. Health, queues, watchers, run KPIs, trace/run drilldowns.

Learning Factory:
1. `/learning`
2. Funnel metrics and distillation lifecycle.

Rabbit Hole Recovery:
1. `/rabbit`
2. Repeat failures, thrash, and recovery signals.

Acceptance & Validation Board:
1. `/acceptance`
2. Acceptance plans, deferrals, validation gaps, evidence stats.

Ops Console:
1. `/ops`
2. Skills, orchestration, and operational stats.

**Daily operator loop (10 minutes)**
1. Open Mission Control and confirm green status for services, queue, and EIDOS activity.
2. Scan Watchers feed for new red/yellow alerts and click into the triggering episode.
3. Check Learning Factory funnel. If retrieved >> used or helped drops, investigate top ignored items.
4. Check Acceptance Board for pending critical tests or expired deferrals.

**Per-change checklist (before and after edits)**
1. Run pipeline health check: `python tests/test_pipeline_health.py`
2. Verify trace_id is present on new steps, evidence, and outcomes.
3. Validate that the dashboard drilldown shows evidence for the change.
4. If validation is missing, add a test or explicit evidence link.

**Trace-first drilldown**
1. Start from a metric or alert.
2. Open the `trace_id` for that event.
3. Review steps in order and confirm evidence exists for each step.
4. If evidence is missing, log a validation gap and block promotion.

URL shortcuts:
1. `/mission?trace_id=<trace_id>`
2. `/mission?episode_id=<episode_id>`

CLI helpers:
1. `python scripts/trace_query.py --trace-id <trace_id>`
2. `python scripts/trace_backfill.py --dry-run`
3. `python scripts/trace_backfill.py --apply`

**Trace binding enforcement**
Default: TRACE_GAP is warning-only.
Strict mode: set `SPARK_TRACE_STRICT=1` to block actions on trace gaps.

**Mission Control usage**
Goal: answer "Are we stable and learning?"
1. If any service is stale or down, fix ops first.
2. If queue oldest event age spikes, inspect bridge cycle health.
3. If EIDOS activity is zero, check EIDOS enabled flag and bridge cycle errors.
4. Use trace_id drilldown to see the latest active episode timeline.

**Rabbit Hole Recovery usage**
Goal: detect and exit loops.
1. Use the repeat failure scoreboard to identify top error signatures.
2. Open the offending trace_id and confirm if evidence is missing.
3. Trigger Escape Protocol if the same signature repeats 2+ times.
4. After escape, ensure a learning artifact was created and linked.

**Learning Factory usage**
Goal: compound intelligence, not just store it.
1. Follow the funnel: retrieved -> cited -> used -> helped -> promoted.
2. If retrieved is high but helped is low, demote or refine the top offenders.
3. If promoted is zero, check validation counts and outcome links.
4. Review contradicted items weekly and schedule revalidation.

**Acceptance and Validation Board usage**
Goal: turn "done" into a contract.
1. Ensure every active episode has an approved acceptance plan.
2. Prioritize P1 tests and close validation gaps before new work.
3. If deferrals are expiring, resolve or explicitly re-defer.

**APIs (JSON)**
1. `/api/mission`
2. `/api/learning`
3. `/api/rabbit`
4. `/api/acceptance`
5. `/api/ops`
6. `/api/trace?trace_id=<trace_id>`
7. `/api/run?episode_id=<episode_id>`
8. `/api/status/stream` (SSE)
9. `/api/ops/stream` (SSE)

**Weekly maintenance**
1. Review top repeated failures and add a distillation or guardrail.
2. Review top contradicted insights and downgrade reliability.
3. Audit evidence store for expiring high-value artifacts and extend retention.
