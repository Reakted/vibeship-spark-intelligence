#!/usr/bin/env python3
import json
from pathlib import Path

adv_file = Path.home() / '.spark' / 'advisory_engine.jsonl'
if adv_file.exists():
    with open(adv_file, encoding='utf-8') as f:
        lines = f.readlines()[-5:]
        for i, line in enumerate(lines):
            event = json.loads(line)
            print(f"=== Event {i} ===")
            print(f"  intent_family: {event.get('intent_family')}")
            print(f"  event: {event.get('event')}")
            print(f"  tool: {event.get('tool')}")
            print(f"  task_plane: {event.get('task_plane')}")
            print(f"  route: {event.get('route')}")
            print()
