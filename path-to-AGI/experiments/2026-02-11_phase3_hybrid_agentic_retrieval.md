# Experiment: Phase 3 — Hybrid + Agentic Retrieval (Forge Advice)
Date: 2026-02-11
Owner: Spark

## Hypothesis
Embedding-style semantic retrieval alone is not enough for robust advice reuse. A hybrid strategy (semantic base + lexical rerank + lightweight agentic expansion) should improve relevance and reduce repeated failure patterns.

## Change
- Updated `spark-forge/src/spark_forge/spark_advisor.py`:
  - Hybrid rerank: lexical overlap + tag weighting + depth bonus
  - Lightweight agentic expansion: extracts prompt facets and probes adjacent KB topics
  - Unified dedupe + rerank before returning top advice

## Validation
- `py_compile` passed for updated modules.

## Result
- Shipped in `spark-forge` commit `4379e42`.

## Decision
- Keep and monitor recurrence and first-pass quality in repeated task families.
