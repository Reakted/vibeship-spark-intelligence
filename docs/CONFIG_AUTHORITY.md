# Config Authority

Canonical config resolution model for Spark runtime behavior.

## Purpose
- Eliminate config drift from multiple competing sources.
- Make precedence deterministic and observable.
- Keep auto-tuner scoped and safe.

## Precedence (highest wins last)
1. `schema defaults` from `lib/tuneables_schema.py`
2. `versioned baseline` from `config/tuneables.json`
3. `runtime overrides` from `~/.spark/tuneables.json`
4. `explicit env overrides` (allowlisted per key, per module)

Notes:
- Env overrides are opt-in and explicit, not implicit global shadowing.
- Invalid env values are ignored with warnings.

## Current Adoption
- `lib/bridge_cycle.py` (`bridge_worker.*`)
- `lib/advisory_engine.py` (`advisory_engine.*`)
- `lib/advisor.py` (`advisor.*`, `auto_tuner.*`, `values.advice_cache_ttl`)
- `lib/advisory_gate.py` (`advisory_gate.*`, including agreement gate knobs)
- `lib/advisory_state.py` (`advisory_gate.shown_advice_ttl_s`)
- `lib/meta_ralph.py` (`meta_ralph.*`)
- `lib/pipeline.py` (`values.queue_batch_size`, `pipeline.*`)
- `lib/advisory_synthesizer.py` (`synthesizer.*`)
- `lib/semantic_retriever.py` (`semantic.*`, `triggers.*`)
- `lib/memory_store.py` (`memory_emotion.*`, `memory_learning.*`, `memory_retrieval_guard.*`)
- `lib/promoter.py` / `lib/auto_promote.py` (`promotion.*`)
- `lib/eidos/models.py` (`eidos.*`, inherited `values.*` budget keys)
- `lib/advisory_packet_store.py` (`advisory_packet_store.*`)
- `lib/advisory_prefetch_worker.py` (`advisory_prefetch.*`)
- `lib/queue.py` (`queue.*`)
- `lib/context_sync.py` (`sync.*`)
- `lib/production_gates.py` (`production_gates.*`)
- `lib/chip_merger.py` (`chip_merge.*`)
- `lib/memory_capture.py` (`memory_capture.*`)
- `lib/memory_banks.py` (`memory_emotion.write_capture_enabled`)
- `lib/pattern_detection/request_tracker.py` (`request_tracker.*`)
- `lib/advisory_preferences.py` (read path for `advisor.*`)
- `lib/observatory/config.py` (`observatory.*`)

Resolver implementation:
- `lib/config_authority.py`

## Operational Rules
- All tuneables writes must be lock-protected and schema-validated.
- Auto-tuner cross-section writes are disabled by default.
- Queue limits are first-class tuneables (`queue.*`) in schema + config.
- Observatory analytics readers that intentionally compare runtime vs baseline
  (for drift/reporting) may read both files directly; runtime behavior modules
  should still resolve through `ConfigAuthority`.

## Migration Standard
- New modules should load runtime knobs via `resolve_section(...)`.
- Env overrides should use explicit mappings (`env_bool/env_int/env_float/env_str`).
- Reload callbacks should re-resolve through `ConfigAuthority` rather than raw section payloads.

## Verification
- `tests/test_config_authority.py`
- `tests/test_tuneables_alignment.py`
- `tests/test_advisory_engine_evidence.py::test_load_engine_config_env_override_wins`
- `tests/test_advisory_gate_config.py::test_load_gate_config_env_overrides`
- `tests/test_advisory_state.py::test_load_state_gate_config_env_override`
- `tests/test_pipeline_config_authority.py`
- `tests/test_advisory_synthesizer_env.py::test_load_synth_config_respects_env_override`
- `tests/test_semantic_retriever.py::test_load_config_reads_sections_and_env_overrides`
- `tests/test_memory_store_config_authority.py`
- `tests/test_promotion_config_authority.py`
- `tests/test_eidos_config_authority.py`
- `tests/test_packet_prefetch_config_authority.py`
- `tests/test_context_sync_policy.py`
- `tests/test_production_gates_config_authority.py`
- `tests/test_remaining_config_authority.py`
- `tests/test_runtime_tuneable_sections.py`
