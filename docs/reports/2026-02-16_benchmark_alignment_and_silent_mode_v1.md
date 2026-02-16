# Benchmark Alignment + Silent Mode v1 (2026-02-16)

## Scope
- Align memory retrieval benchmarks with live runtime retrieval policy/domain profiles.
- Silence advisory stdout emissions during benchmark runs to reduce noise and speed sweeps.

## Changes

### Runtime-policy benchmark alignment
- `benchmarks/memory_retrieval_ab.py`
  - Added runtime policy resolution for each case via advisor policy.
  - Added `--use-runtime-policy/--no-use-runtime-policy` (default: on).
  - Added `--runtime-tool-name` (default: `Bash`).
  - CLI knobs now optional overrides; runtime policy drives defaults when enabled.
  - Report now records per-case `resolved_knobs` and runtime domain/profile.
- `benchmarks/memory_retrieval_domain_matrix.py`
  - Added the same runtime policy options and per-case knob resolution path.

### Silent advisory benchmark mode
- `benchmarks/advisory_quality_ab.py`
  - Added `--suppress-emit-output/--no-suppress-emit-output` (default: on).
  - `run_profile(...)` now suppresses advisory emitter stdout in benchmark mode.
- `benchmarks/advisory_profile_sweeper.py`
  - Threads same suppression flag into quality runner.

### Docs/tests
- Updated `benchmarks/README.md` with new flags and defaults.
- Added/updated tests:
  - `tests/test_memory_retrieval_ab.py`
  - `tests/test_advisory_quality_ab.py`
  - `tests/test_advisory_profile_sweeper.py`

## Validation
- Targeted tests:
```bash
python -m pytest tests/test_memory_retrieval_ab.py tests/test_memory_retrieval_domain_matrix.py tests/test_advisory_quality_ab.py tests/test_advisory_profile_sweeper.py -q
```
- Result: `24 passed`

- Silent-mode check:
```bash
python benchmarks/advisory_profile_sweeper.py \
  --cases benchmarks/data/advisory_quality_eval_seed.json \
  --repeats 1 \
  --force-live \
  --max-candidates 1 \
  --out-prefix advisory_profile_sweeper_silent_check_2026_02_16
```
- Output is now concise (no `(spark: ...)` flood).

- Runtime-policy alignment check:
```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_live_2026_02_12.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 3 \
  --case-limit 3 \
  --out-prefix memory_retrieval_ab_runtime_policy_check_2026_02_16
```
- Report confirms runtime policy active and memory-domain knobs applied per case.
