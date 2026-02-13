import json
from pathlib import Path
files = [
 'benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_report.json',
 'benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_relaxed_report.json',
 'benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_live_report.json',
 'benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_relaxed_live_report.json',
 'benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_after_rescue_report.json',
 'benchmarks/out/memory_retrieval_ab_tuning_tfidf.json',
 'benchmarks/out/memory_retrieval_ab_tuning_fastembed_quick.json',
]
for fp in files:
    p=Path(fp)
    if not p.exists():
        continue
    j=json.loads(p.read_text(encoding='utf-8'))
    print('\n==',p.name,'==')
    # generic winner fields
    for key in ['winner','winner_system','winner_profile','decision']:
        if key in j:
            print(key,':',j[key])
    # memory AB shape: systems table maybe under 'systems' or 'results'
    rows=[]
    for k in ['systems','results','rows','scores']:
        v=j.get(k)
        if isinstance(v,list) and v and isinstance(v[0],dict):
            rows=v
            break
    if rows:
        for r in rows:
            name = r.get('system') or r.get('name') or r.get('id')
            if not name:
                continue
            print(' ',name,
                  'P@5=',r.get('precision_at_5',r.get('p_at_5',r.get('p5'))),
                  'Recall@5=',r.get('recall_at_5',r.get('r_at_5',r.get('r5'))),
                  'MRR=',r.get('mrr'),
                  'Top1=',r.get('top1_hit_rate',r.get('top1')),
                  'NonEmpty=',r.get('non_empty_rate'),
                  'p95=',r.get('latency_p95_ms',r.get('p95_ms')),
                  'Err=',r.get('error_rate'))
    # tuning shape maybe includes best params
    for key in ['best_params','best','backend','summary']:
        if key in j:
            val=j[key]
            if isinstance(val,(dict,list,str,int,float,bool)):
                print(key,':',val)
