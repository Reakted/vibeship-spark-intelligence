# Dashboard TODOs

Last updated: 2026-02-05

Purpose:
- Track dashboard additions without touching UI during core system stabilization.
- Treat this as the single source of truth for future dashboard work.

Guiding rule:
- Do not change dashboards while core intelligence is stabilizing.
- Add items here instead. Implement later in one focused sweep.

## Semantic Retrieval (Advisor)
- Add a "Semantic Retrieval" panel that shows:
  - intent (cleaned query)
  - semantic_candidates_count
  - trigger_hits
  - final top-N results with fusion/sim/outcome/recency/why
- Source: `~/.spark/logs/semantic_retrieval.jsonl`
- Display last N events with filters: tool, context keyword, trigger presence

## Advisor Metrics (Cognitive Surface + Helpful)
- Add a small KPI strip:
  - cognitive_surface_rate
  - cognitive_helpful_rate (when feedback exists)
- Source: `~/.spark/advisor/metrics.json`
- Include last_updated timestamp

## Semantic Index Health
- Add a health card:
  - index exists? path: `~/.spark/semantic/insights_vec.sqlite`
  - estimated vector count
  - last backfill run time (if tracked later)
- Source: SQLite table `insights_vec`

## Trigger Rules (Visibility)
- Add a panel listing active trigger rules + last match count
- Source: `~/.spark/trigger_rules.yaml` and semantic retrieval logs

## Embeddings Status
- Surface embeddings availability and model:
  - SPARK_EMBEDDINGS enabled/disabled
  - SPARK_EMBED_MODEL value
- Source: environment + runtime settings

## Quality Gate (Meta-Ralph) Link
- Add a "Quality Gate" section linking:
  - retrieval outcomes by insight key
  - pass rate over time
- Source: Meta-Ralph storage + advice feedback summary

## Future Additions (After Release)
- “Top helpful insights” leaderboard
- “Worst performing insights” (needs outcome data)
- “Cold start health” (seed pack coverage vs user insights)
