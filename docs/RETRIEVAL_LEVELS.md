# Retrieval Levels (Cost vs Quality)

Date: 2026-02-12

This defines a 3-level operating model for Spark/OpenClaw memory retrieval with the new auto-router in `lib/advisor.py`.

## Router Behavior (Now Implemented)

Advisor now routes retrieval like this:
- Start with primary semantic retrieval (embeddings path).
- In `auto` mode, escalate to hybrid-agentic only when needed:
  - query complexity is high,
  - high-risk terms appear (`auth`, `token`, `prod`, `session`, `bridge`, etc.),
  - trigger signal appears,
  - or primary retrieval is weak (low count/low top score).
- Hybrid rerank now uses a blended lexical score:
  - normalized BM25 (default 75%)
  - token overlap (default 25%)
- Route decisions are logged to `~/.spark/advisor/retrieval_router.jsonl`.

Controls:
- Env:
  - `SPARK_RETRIEVAL_LEVEL=1|2|3`
  - `SPARK_RETRIEVAL_MODE=auto|embeddings_only|hybrid_agentic`
- Tuneables: `~/.spark/tuneables.json` -> `retrieval` section.

## Level 1: Local-Free (No Spend)

Use when cost must be near zero.

Setup:
- Spark embeddings backend: `tfidf` (default) or `fastembed` only if RAM allows.
- Retrieval mode: `auto` with conservative escalation.
- OpenClaw memorySearch: `local` provider (or `off` if you only want Spark-side memory for now).

Suggested config:

```json
{
  "retrieval": {
    "level": "1",
    "overrides": {
      "mode": "auto",
      "max_queries": 2,
      "agentic_query_limit": 2,
      "complexity_threshold": 3
    }
  }
}
```

## Level 2: Balanced Spend (Low Cost, Better Recall)

Use when you can spend a bit for higher retrieval quality.

Setup:
- Keep `auto` routing.
- Use stronger remote embeddings for OpenClaw memorySearch via OpenAI-compatible remote endpoint.
- Keep `Codex` as main reasoning model; only embeddings path changes.

Suggested config:

```json
{
  "retrieval": {
    "level": "2",
    "overrides": {
      "mode": "auto",
      "max_queries": 3,
      "agentic_query_limit": 3,
      "bm25_k1": 1.2,
      "bm25_b": 0.75,
      "bm25_mix": 0.75,
      "complexity_threshold": 2
    }
  }
}
```

## Level 3: Quality-Max (Best Retrieval)

Use when quality matters more than latency/cost.

Setup:
- Default route: `hybrid_agentic`.
- Larger candidate sets and more facet queries.
- Strongest embedding model available for your OpenClaw memorySearch backend.

Suggested config:

```json
{
  "retrieval": {
    "level": "3",
    "overrides": {
      "mode": "hybrid_agentic",
      "max_queries": 4,
      "agentic_query_limit": 4,
      "complexity_threshold": 1
    }
  }
}
```

## Kimi Usage Guidance

- Keep `Codex` as primary model for execution/planning.
- Use Kimi only on the memory embedding path if your configured provider exposes an embeddings endpoint compatible with OpenClaw memorySearch.
- If Kimi embeddings are not available/reliable in your endpoint, use OpenAI-compatible embeddings endpoint for memory and keep Kimi/Codex for generation separately.

## Upgrade Sequence for Current Architecture

1. Pick a level (`1/2/3`) and apply `SPARK_RETRIEVAL_LEVEL`.
2. Confirm route logs are being written (`~/.spark/advisor/retrieval_router.jsonl`).
3. Run tuned A/B on your live query set (`embeddings_only` vs `hybrid_agentic`).
4. Set default mode from benchmark winner; keep `auto` as fallback for mixed workloads.
