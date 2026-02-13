#!/usr/bin/env python3
from trace_hud import TraceCollector

collector = TraceCollector()

# Clear processed IDs to force re-parse
collector._processed_ids.clear()

events = collector.poll_all_sources()

# Check advisory events
advisory = [e for e in events if e.source.value == 'spark_advisory']
print(f"Advisory events: {len(advisory)}")
print()

for e in advisory[:5]:
    print(f"intent='{e.intent[:50]}...'")
    print(f"  category='{e.intent_category}'")
    print()
