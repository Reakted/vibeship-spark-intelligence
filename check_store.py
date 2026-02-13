#!/usr/bin/env python3
import json

# Check what's in the store
with open(r'C:/Users/USER/.spark/tracer/trace_store.jsonl', encoding='utf-8') as f:
    lines = f.readlines()[-10:]
    for i, line in enumerate(lines):
        event = json.loads(line)
        src = event.get('source')
        intent = event.get('intent', 'N/A')[:50]
        cat = event.get('intent_category')
        print(f"{i}: source={src}, intent={intent}...")
        print(f"   category={cat}")
        print()
