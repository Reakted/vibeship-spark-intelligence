# META_RALPH_TELEMETRY.md

Purpose
- Track where telemetry/primitive tool-sequence insights originate.
- Keep telemetry separate from feedback loops.
- Provide manual, step-by-step review before any automation.

Telemetry vs Feedback (Do Not Mix)
- Telemetry: tool usage counts, tool sequences, success-rate stats, and other operational traces.
- Feedback: user- or system-marked helpfulness on advice/insights.
- Feedback is stored in advice feedback files and should never be treated as telemetry.

Known Telemetry Sources (as of 2026-02-03)
- Pattern distillation tool heuristics in lib/pattern_detection/distiller.py.
  - Previously emitted statements like "{tool} is reliable (X/Y success rate)".
  - Now requires explicit reasoning and skips success-rate-only output.
- Any legacy memories persisted before the filters were added.
  - Examples: "Heavy Bash usage (42 calls)", "Sequence 'Bash -> Edit' worked well".
  - No direct generator found in current runtime code; likely historical or external.

Telemetry Blockers Now Active
- lib/pattern_detection/distiller.py: rejects operational/primitive distillations at the memory gate.
- Tool-pattern distillation is disabled by default.
  - Set `SPARK_ENABLE_TOOL_DISTILLATION=1` to re-enable.
- lib/promoter.py: filters operational insights on promotion.
- lib/importance_scorer.py: ignores telemetry signals at ingestion.
- lib/cognitive_learner.py, lib/memory_banks.py, lib/memory_store.py: telemetry/sequence filters and purge helpers.

Manual Review Steps (Non-Automatic)
1. Search for telemetry generators
   - rg -n "success rate|Sequence|tool sequence|Heavy .* usage" -S lib hooks chips
2. Inspect distillations for telemetry
   - Use a sqlite viewer on ~/.spark/eidos.db and search distillations.statement for "success rate" or "Sequence".
   - Or run: python -m spark.cli eidos-purge-telemetry --dry-run
3. Inspect memory banks and store
   - Run spark memory-purge-telemetry --dry-run
   - Review ~/.spark/banks/*.jsonl for tool sequences or usage counts.
4. Run Meta-Ralph tuneable analysis after enough samples
   - python -c "from lib.meta_ralph import get_meta_ralph; import json; print(json.dumps(get_meta_ralph().analyze_tuneables(), indent=2))"

If We Decide to Automate Later
- Add an opt-in flag to disable tool-pattern distillation entirely.
- Add a scheduled telemetry purge with clear logging and dry-run support.
- Add an EIDOS distillation purge for operational patterns.
