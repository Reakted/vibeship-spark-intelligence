import json
from pathlib import Path
files = [
 'benchmarks/out/advisory_quality_smoke_report.json',
 'benchmarks/out/advisory_quality_ab_report.json',
 'benchmarks/out/advisory_profile_sweeper_smoke_report.json',
 'benchmarks/out/advisory_profile_sweeper_smoke_winner_profile.json',
 'benchmarks/out/advisory_realism_baseline_v2labels_v5_report.json',
 'benchmarks/out/advisory_realism_tuning_v1_report.json',
 'benchmarks/out/advisory_realism_primary_contract_report.json',
 'benchmarks/out/advisory_realism_shadow_contract_report.json',
 'benchmarks/out/advisory_realism_domain_matrix_baseline_v3_report.json',
 'benchmarks/out/advisory_realism_domain_matrix_candidate_v4_report.json',
]
for fp in files:
    p=Path(fp)
    if not p.exists():
        continue
    j=json.loads(p.read_text(encoding='utf-8'))
    print('\n==',p.name,'==')
    for key in ['status','decision','winner','winner_profile','pass','passed','blocking_passed']:
        if key in j:
            print(key,':',j[key])
    # common metric bundles
    for key in ['overall','summary','metrics','kpis']:
        v=j.get(key)
        if isinstance(v,dict):
            keep={k:v.get(k) for k in ['objective','objective_score','score','pass_rate','high_value_rate','harmful_rate','fallback_ratio','duplicate_rate','trace_coverage_pct','source_alignment','quality','latency_p95_ms'] if k in v}
            if keep:
                print(key,':',keep)
    # domain matrix style
    if isinstance(j.get('overall'),dict):
        ov=j['overall']
        if 'objective' in ov:
            print('objective:',ov.get('objective'))
    if isinstance(j.get('domains'),list):
        print('domains:',len(j['domains']))
    if isinstance(j.get('profiles'),list):
        # print top profile-like row if present
        for r in j['profiles'][:3]:
            if isinstance(r,dict):
                print(' profile',r.get('id') or r.get('name'), 'obj=',r.get('objective') or r.get('score'), 'hv=',r.get('high_value_rate'), 'harm=',r.get('harmful_rate'))
