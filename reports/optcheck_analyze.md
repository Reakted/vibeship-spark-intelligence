# Optimization Analysis Report

Generated: `2026-02-14T18:41:58Z`

## Key directory sizes

- `.`: 693965177 bytes
- `node_modules`: 154743546 bytes
- `lib`: 5812631 bytes
- `tests`: 2128893 bytes
- `docs`: 1332222 bytes
- `scripts`: 849956 bytes
- `build`: 418070 bytes

## Largest files (top)

- `tmp/agent-lightning/uv.lock`: 12904496 bytes
- `reports/advisory_auto_score_20260213_165323.json`: 3655466 bytes
- `visuals/out/funnel.mp4`: 2934845 bytes
- `visuals/out/FunnelStill.mp4`: 2934845 bytes
- `tmp/agent-lightning/docs/assets/readme-diff.svg`: 1999368 bytes
- `tmp/agent-lightning/tests/assets/chinook.db`: 913408 bytes
- `tmp/agent-lightning/docs/assets/store-api-visualized.svg`: 837381 bytes
- `tmp/agent-lightning/docs/assets/agentops-waterfall-visualization.jpg`: 548710 bytes
- `tmp/agent-lightning/docs/assets/readme-architecture.svg`: 541689 bytes
- `tmp/agent-lightning/docker/grafana/dashboards/1860_rev42.json`: 489629 bytes
- `tmp/agent-lightning/dashboard/package-lock.json`: 392625 bytes
- `tmp/agent-lightning/examples/azure/assets/aoai_finetune.svg`: 387967 bytes
- `tmp/local_model_compare_intel_speed_useful_r5_live12.json`: 352188 bytes
- `tmp/agent-lightning/docs/assets/sql-agent-diff.png`: 317493 bytes
- `tmp/agent-lightning/docs/assets/dashboard-page-rollouts.png`: 281932 bytes
- `sandbox/spark_sandbox/home/.spark/chip_insights/bench_core.jsonl`: 257328 bytes
- `tmp/agent-lightning/docs/assets/dashboard-page-traces.png`: 253099 bytes
- `benchmarks/out/advisory_realism_indirect_abcd_v2_cycle1_report.json`: 242637 bytes
- `benchmarks/out/advisory_realism_indirect_abcd_v2_cycle2_report.json`: 242087 bytes
- `benchmarks/out/advisory_realism_indirect_abcd_v2_cycle3_report.json`: 242085 bytes
- `tmp/agent-lightning/docs/assets/sql-agent-val-reward-curve.png`: 240347 bytes
- `benchmarks/out/memory_retrieval_ab_live_2026_02_12_relaxed_report.json`: 213212 bytes
- `tmp/agent-lightning/docs/assets/opentelemetry-trace.jpg`: 206614 bytes
- `benchmarks/out/memory_retrieval_ab_real_user_canary_strict_v1_report.json`: 190194 bytes
- `benchmarks/out/memory_retrieval_ab_canary_retrieval_v2_report.json`: 190177 bytes

## Optimization questions (guided)

Answer these with measurements or direct code evidence. Avoid guesses.

- [ ] **build.deps**: Do we have heavy or duplicate dependencies that can be removed or replaced with lighter ones?
- [ ] **disk.logs**: Are logs/JSONL/trace outputs bounded (rotation, sampling, caps) and are caps append-only?
- [ ] **mem.leaks**: Do we have memory growth over hours/days (leaks, caches without TTL/LRU, unbounded queues)?
- [ ] **node.bundle**: Node: are we shipping minimal bundles (tree-shaking, code splitting) and avoiding huge transitive deps?
- [ ] **perf.allocations**: Are we creating large intermediate objects/strings that can be streamed/chunked?
- [ ] **perf.concurrency**: Do we have lock contention or single-thread bottlenecks, and can we bound critical sections?
- [ ] **perf.hot_path**: What is the top hot-path (p95/p99) and do we have a profiler/trace proving it?
- [ ] **perf.io**: Are we doing unnecessary disk/network I/O on the hot path (full-file reads, chatty calls, unbounded logs)?
- [ ] **py.logging**: Python: are debug logs guarded and structured logging sampling/batching used where high volume?
- [ ] **reliability.fallbacks**: Do we have safe fallbacks when optional subsystems fail (cache miss, telemetry failure, slow dependency)?
- [ ] **reliability.timeouts**: Are external calls protected with timeouts, retries (bounded), and circuit breakers?
- [ ] **safety.flags**: Can the change be gated behind a flag/knob so it can be turned off without reverting?
- [ ] **safety.measure_before_after**: Do we have before/after snapshots for runtime, size, and health probes?
- [ ] **safety.one_change**: Are we doing one optimization per commit, with a clear rollback path (git revert)?
- [ ] **startup.lazy**: Can we lazy-load non-critical subsystems so first response is fast?

## Python: unused dependency hints (heuristic)

- dependencies: 2
- scanned_py_files: 619
- maybe_unused: 0

---

Raw JSON:

```json
{
  "schema": "optcheck.analyze.v1",
  "generated_at": "2026-02-14T18:41:58Z",
  "project_root": "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence",
  "languages_detected": [
    "node",
    "python"
  ],
  "intents": [
    "latency",
    "throughput",
    "memory",
    "disk",
    "reliability",
    "cost"
  ],
  "dir_sizes": [
    {
      "path": ".",
      "bytes": 693965177
    },
    {
      "path": "node_modules",
      "bytes": 154743546
    },
    {
      "path": "lib",
      "bytes": 5812631
    },
    {
      "path": "tests",
      "bytes": 2128893
    },
    {
      "path": "docs",
      "bytes": 1332222
    },
    {
      "path": "scripts",
      "bytes": 849956
    },
    {
      "path": "build",
      "bytes": 418070
    }
  ],
  "largest_files": [
    {
      "path": "tmp/agent-lightning/uv.lock",
      "bytes": 12904496
    },
    {
      "path": "reports/advisory_auto_score_20260213_165323.json",
      "bytes": 3655466
    },
    {
      "path": "visuals/out/funnel.mp4",
      "bytes": 2934845
    },
    {
      "path": "visuals/out/FunnelStill.mp4",
      "bytes": 2934845
    },
    {
      "path": "tmp/agent-lightning/docs/assets/readme-diff.svg",
      "bytes": 1999368
    },
    {
      "path": "tmp/agent-lightning/tests/assets/chinook.db",
      "bytes": 913408
    },
    {
      "path": "tmp/agent-lightning/docs/assets/store-api-visualized.svg",
      "bytes": 837381
    },
    {
      "path": "tmp/agent-lightning/docs/assets/agentops-waterfall-visualization.jpg",
      "bytes": 548710
    },
    {
      "path": "tmp/agent-lightning/docs/assets/readme-architecture.svg",
      "bytes": 541689
    },
    {
      "path": "tmp/agent-lightning/docker/grafana/dashboards/1860_rev42.json",
      "bytes": 489629
    },
    {
      "path": "tmp/agent-lightning/dashboard/package-lock.json",
      "bytes": 392625
    },
    {
      "path": "tmp/agent-lightning/examples/azure/assets/aoai_finetune.svg",
      "bytes": 387967
    },
    {
      "path": "tmp/local_model_compare_intel_speed_useful_r5_live12.json",
      "bytes": 352188
    },
    {
      "path": "tmp/agent-lightning/docs/assets/sql-agent-diff.png",
      "bytes": 317493
    },
    {
      "path": "tmp/agent-lightning/docs/assets/dashboard-page-rollouts.png",
      "bytes": 281932
    },
    {
      "path": "sandbox/spark_sandbox/home/.spark/chip_insights/bench_core.jsonl",
      "bytes": 257328
    },
    {
      "path": "tmp/agent-lightning/docs/assets/dashboard-page-traces.png",
      "bytes": 253099
    },
    {
      "path": "benchmarks/out/advisory_realism_indirect_abcd_v2_cycle1_report.json",
      "bytes": 242637
    },
    {
      "path": "benchmarks/out/advisory_realism_indirect_abcd_v2_cycle2_report.json",
      "bytes": 242087
    },
    {
      "path": "benchmarks/out/advisory_realism_indirect_abcd_v2_cycle3_report.json",
      "bytes": 242085
    },
    {
      "path": "tmp/agent-lightning/docs/assets/sql-agent-val-reward-curve.png",
      "bytes": 240347
    },
    {
      "path": "benchmarks/out/memory_retrieval_ab_live_2026_02_12_relaxed_report.json",
      "bytes": 213212
    },
    {
      "path": "tmp/agent-lightning/docs/assets/opentelemetry-trace.jpg",
      "bytes": 206614
    },
    {
      "path": "benchmarks/out/memory_retrieval_ab_real_user_canary_strict_v1_report.json",
      "bytes": 190194
    },
    {
      "path": "benchmarks/out/memory_retrieval_ab_canary_retrieval_v2_report.json",
      "bytes": 190177
    }
  ],
  "questions": [
    {
      "id": "build.deps",
      "text": "Do we have heavy or duplicate dependencies that can be removed or replaced with lighter ones?",
      "tags": [
        "build",
        "deps",
        "general"
      ],
      "intents": [
        "build_time",
        "cost",
        "disk"
      ]
    },
    {
      "id": "disk.logs",
      "text": "Are logs/JSONL/trace outputs bounded (rotation, sampling, caps) and are caps append-only?",
      "tags": [
        "disk",
        "general",
        "observability"
      ],
      "intents": [
        "cost",
        "disk",
        "reliability"
      ]
    },
    {
      "id": "mem.leaks",
      "text": "Do we have memory growth over hours/days (leaks, caches without TTL/LRU, unbounded queues)?",
      "tags": [
        "general",
        "memory"
      ],
      "intents": [
        "cost",
        "memory",
        "reliability"
      ]
    },
    {
      "id": "node.bundle",
      "text": "Node: are we shipping minimal bundles (tree-shaking, code splitting) and avoiding huge transitive deps?",
      "tags": [
        "node"
      ],
      "intents": [
        "disk",
        "latency",
        "startup_time"
      ]
    },
    {
      "id": "perf.allocations",
      "text": "Are we creating large intermediate objects/strings that can be streamed/chunked?",
      "tags": [
        "general",
        "memory",
        "perf"
      ],
      "intents": [
        "latency",
        "memory"
      ]
    },
    {
      "id": "perf.concurrency",
      "text": "Do we have lock contention or single-thread bottlenecks, and can we bound critical sections?",
      "tags": [
        "concurrency",
        "general",
        "perf"
      ],
      "intents": [
        "latency",
        "throughput"
      ]
    },
    {
      "id": "perf.hot_path",
      "text": "What is the top hot-path (p95/p99) and do we have a profiler/trace proving it?",
      "tags": [
        "general",
        "perf"
      ],
      "intents": [
        "latency",
        "throughput"
      ]
    },
    {
      "id": "perf.io",
      "text": "Are we doing unnecessary disk/network I/O on the hot path (full-file reads, chatty calls, unbounded logs)?",
      "tags": [
        "general",
        "io",
        "perf"
      ],
      "intents": [
        "disk",
        "latency",
        "throughput"
      ]
    },
    {
      "id": "py.logging",
      "text": "Python: are debug logs guarded and structured logging sampling/batching used where high volume?",
      "tags": [
        "python"
      ],
      "intents": [
        "disk",
        "latency"
      ]
    },
    {
      "id": "reliability.fallbacks",
      "text": "Do we have safe fallbacks when optional subsystems fail (cache miss, telemetry failure, slow dependency)?",
      "tags": [
        "general",
        "reliability"
      ],
      "intents": [
        "reliability"
      ]
    },
    {
      "id": "reliability.timeouts",
      "text": "Are external calls protected with timeouts, retries (bounded), and circuit breakers?",
      "tags": [
        "general",
        "reliability"
      ],
      "intents": [
        "latency",
        "reliability"
      ]
    },
    {
      "id": "safety.flags",
      "text": "Can the change be gated behind a flag/knob so it can be turned off without reverting?",
      "tags": [
        "general",
        "safety"
      ],
      "intents": [
        "reliability"
      ]
    },
    {
      "id": "safety.measure_before_after",
      "text": "Do we have before/after snapshots for runtime, size, and health probes?",
      "tags": [
        "general",
        "measurement"
      ],
      "intents": [
        "cost",
        "reliability"
      ]
    },
    {
      "id": "safety.one_change",
      "text": "Are we doing one optimization per commit, with a clear rollback path (git revert)?",
      "tags": [
        "general",
        "safety"
      ],
      "intents": [
        "reliability"
      ]
    },
    {
      "id": "startup.lazy",
      "text": "Can we lazy-load non-critical subsystems so first response is fast?",
      "tags": [
        "general",
        "startup"
      ],
      "intents": [
        "latency",
        "startup_time"
      ]
    }
  ],
  "python_unused_dep_hints": {
    "dependency_count": 2,
    "scanned_py_files": 619,
    "import_roots_count": 191,
    "maybe_unused": [],
    "note": "Heuristic only. False positives expected (optional deps, dynamic imports, plugins)."
  }
}
```
