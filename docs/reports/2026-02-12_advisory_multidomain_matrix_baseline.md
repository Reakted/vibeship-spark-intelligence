# Advisory Multidomain Matrix Baseline (2026-02-12)

## What was added

- New multidomain case pack: `benchmarks/data/advisory_realism_eval_multidomain_v1.json`
  - 22 cases
  - 11 domains (`coding`, `debugging`, `testing`, `ui_design`, `marketing`, `social`, `strategy`, `conversation`, `prompting`, `research`, `memory`)
- New matrix runner: `scripts/run_advisory_realism_domain_matrix.py`
  - Executes per-domain realism benches in one command
  - Emits weighted summary and domain gap ordering

## Commands run

```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --dry-run
```

```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --repeats 1 \
  --out-prefix advisory_realism_domain_matrix_baseline
```

```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --domains memory,research \
  --repeats 1 \
  --out-prefix advisory_realism_domain_matrix_memory_research
```

## Baseline observations

From `benchmarks/out/advisory_realism_domain_matrix_baseline_report.json`:
- weighted objective: `0.5875`
- weighted base score: `0.7912`
- weighted high-value rate: `22.22%`
- weighted harmful-emit rate: `11.11%`
- weighted critical-miss rate: `11.11%`
- weighted source-alignment rate: `45.37%`
- weighted theory-discrimination rate: `50.00%`
- weighted trace-bound rate: `100.00%`

Strongest domains in this baseline run:
- `strategy` objective `0.9227`
- `prompting` objective `0.7887`
- `testing` objective `0.7727`

Largest gaps in this baseline run:
- `coding` objective `0.3580`
- `conversation` objective `0.3950`
- `marketing` objective `0.4350`

Memory/research validation run (`benchmarks/out/advisory_realism_domain_matrix_memory_research_report.json`):
- weighted objective: `0.7044`
- weighted high-value rate: `25.00%`
- weighted harmful-emit rate: `0.00%`

## Next tuning targets

1. Raise high-value and source-alignment in `coding`, `conversation`, `marketing` domains first.
2. Reduce repeated noisy advice text that appears across many domain slices.
3. Keep trace-bound coverage at current level while pushing harmful emit below `10%` across all domain runs.
