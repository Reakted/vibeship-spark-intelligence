#!/usr/bin/env python3
import urllib.request
import json

with urllib.request.urlopen('http://localhost:8777/api/data') as r:
    data = json.loads(r.read())
    print('KPIs:', data['kpis'])
    print()
    print('Active traces with categories:')
    for t in data['active'][:10]:
        print(f"  [{t['phase']:10}] cat={t['category'] or 'none':20} intent={t['intent'][:50]}...")
    print()
    print('Sources from store stats:', data.get('store_stats', {}))
