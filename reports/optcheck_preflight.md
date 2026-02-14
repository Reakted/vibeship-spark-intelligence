# Optimization Preflight Report

Generated: `2026-02-14T18:41:53Z`

Worst level: **warn**

## Git

- branch: `main`
- describe: `d473c56-dirty`
- dirty: `True` (10)

## Findings

- **WARN** `GIT_DIRTY` - Working tree is dirty (10 changed files).
  - hint: Commit or stash before snapshotting so before/after is attributable.
- **WARN** `TIMINGS_NO_CMDS` - Timings entries exist but all cmds are empty.
  - hint: Add at least one: tests/build/lint command you care about (e.g., pytest, npm test).
- **INFO** `HTTP_PROBES_EMPTY` - No http_probes configured.
  - hint: Optional: add a /health endpoint probe for services.
- **INFO** `NO_SNAPSHOTS` - No snapshots found yet.
  - hint: Run: optcheck snapshot --label before
- **INFO** `BLOAT_DIR_PRESENT` - Directory present: node_modules (154743546 bytes).
  - hint: Consider excluding from size_paths if it's not part of shipped artifact, or measure it separately.
- **INFO** `BLOAT_DIR_PRESENT` - Directory present: build (418070 bytes).
  - hint: Consider excluding from size_paths if it's not part of shipped artifact, or measure it separately.

## Analyze (high level)

- `.`: 693951845 bytes
- `node_modules`: 154743546 bytes
- `lib`: 5812631 bytes
- `tests`: 2128893 bytes
- `docs`: 1332222 bytes
- `scripts`: 849956 bytes
- `build`: 418070 bytes

---

Raw JSON:

```json
{
  "schema": "optcheck.preflight.v1",
  "generated_at": "2026-02-14T18:41:53Z",
  "project_root": "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence",
  "worst_level": "warn",
  "git": {
    "is_git": true,
    "git_root": "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence",
    "branch": "main",
    "commit": "d473c5610303500fb16f8a182142350a112065db",
    "describe": "d473c56-dirty",
    "dirty": true,
    "dirty_count": 10,
    "diff_stat": "docs/DOCS_INDEX.md |  1 +\n lib/x_research.py  | 56 ++++++++++++++++++++++++++++++++++++------------------\n spark_scheduler.py |  2 +-\n 3 files changed, 39 insertions(+), 20 deletions(-)"
  },
  "config_path": "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence\\.optcheck\\config.yml",
  "findings": [
    {
      "level": "warn",
      "code": "GIT_DIRTY",
      "message": "Working tree is dirty (10 changed files).",
      "hint": "Commit or stash before snapshotting so before/after is attributable."
    },
    {
      "level": "warn",
      "code": "TIMINGS_NO_CMDS",
      "message": "Timings entries exist but all cmds are empty.",
      "hint": "Add at least one: tests/build/lint command you care about (e.g., pytest, npm test)."
    },
    {
      "level": "info",
      "code": "HTTP_PROBES_EMPTY",
      "message": "No http_probes configured.",
      "hint": "Optional: add a /health endpoint probe for services."
    },
    {
      "level": "info",
      "code": "NO_SNAPSHOTS",
      "message": "No snapshots found yet.",
      "hint": "Run: optcheck snapshot --label before"
    },
    {
      "level": "info",
      "code": "BLOAT_DIR_PRESENT",
      "message": "Directory present: node_modules (154743546 bytes).",
      "hint": "Consider excluding from size_paths if it's not part of shipped artifact, or measure it separately."
    },
    {
      "level": "info",
      "code": "BLOAT_DIR_PRESENT",
      "message": "Directory present: build (418070 bytes).",
      "hint": "Consider excluding from size_paths if it's not part of shipped artifact, or measure it separately."
    }
  ],
  "analysis": {
    "schema": "optcheck.analyze.v1",
    "generated_at": "2026-02-14T18:41:47Z",
    "project_root": "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence",
    "languages_detected": [
      "node",
      "python"
    ],
    "intents": [],
    "dir_sizes": [
      {
        "path": ".",
        "bytes": 693951845
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
        "id": "build.incremental",
        "text": "Are builds/tests incremental and cached (compiler cache, test selection, dependency caching)?",
        "tags": [
          "build",
          "general"
        ],
        "intents": [
          "build_time",
          "developer_experience",
          "test_time"
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
        "id": "py.import_time",
        "text": "Python: have we measured import time and eliminated expensive import side-effects?",
        "tags": [
          "python"
        ],
        "intents": [
          "startup_time"
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
        "id": "startup.imports",
        "text": "What is contributing to startup time (imports/init, migrations, model loads, cache warmup)?",
        "tags": [
          "general",
          "startup"
        ],
        "intents": [
          "startup_time"
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
}
```
