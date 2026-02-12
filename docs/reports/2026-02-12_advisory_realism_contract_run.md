# Advisory Realism Contract Run (2026-02-12)

## Command

```bash
python scripts/run_advisory_realism_contract.py --run-timeout-s 1200
```

## Output Artifacts

- `benchmarks/out/advisory_realism_primary_contract_report.json`
- `benchmarks/out/advisory_realism_primary_contract_report.md`
- `benchmarks/out/advisory_realism_shadow_contract_report.json`
- `benchmarks/out/advisory_realism_shadow_contract_report.md`

## Result

- Primary (`v2`) status: **PASS**
- Shadow (`v1`) status: **FAIL** (non-blocking telemetry by contract design)

Primary winner:
- profile: `balanced`
- objective: `0.8271`
- score: `0.8898`
- high_value_rate: `66.67%`
- harmful_emit_rate: `0.00%`
- critical_miss_rate: `6.67%`
- source_alignment_rate: `66.67%`
- theory_discrimination_rate: `94.44%`
- trace_bound_rate: `100.00%`

Shadow winner:
- profile: `baseline`
- objective: `0.6927`
- score: `0.8148`
- high_value_rate: `44.44%`
- harmful_emit_rate: `27.78%`
- critical_miss_rate: `7.69%`
- source_alignment_rate: `66.67%`
- theory_discrimination_rate: `66.67%`
- trace_bound_rate: `100.00%`

Delta (primary - shadow):
- objective: `+0.1344`
- score: `+0.0750`
- high_value_rate: `+22.23pp`
- harmful_emit_rate: `-27.78pp`
- critical_miss_rate: `-1.02pp`
- source_alignment_rate: `+0.00pp`
- theory_discrimination_rate: `+27.77pp`
- trace_bound_rate: `+0.00pp`

## Decision

Contract health remains consistent with the locked policy:
- Keep `v2` as blocking primary contract.
- Keep `v1` as shadow telemetry only.
- Do not rollback while primary remains green and trace/source gates stay stable.
