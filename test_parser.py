#!/usr/bin/env python3
from trace_hud import TraceCollector
import json
from pathlib import Path

collector = TraceCollector()

# Read advisory events directly
adv_file = Path.home() / '.spark' / 'advisory_engine.jsonl'
if adv_file.exists():
    with open(adv_file, encoding='utf-8') as f:
        lines = f.readlines()[-3:]
        for line in lines:
            raw = json.loads(line)
            print("Raw event:")
            print(f"  intent_family: {raw.get('intent_family')}")
            print(f"  event: {raw.get('event')}")
            print(f"  tool: {raw.get('tool')}")
            print()
            
            # Parse it
            parsed = collector._parse_advisory_event(raw)
            if parsed:
                print(f"Parsed: intent='{parsed.intent}', category='{parsed.intent_category}'")
            print()
