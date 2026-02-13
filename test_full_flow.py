#!/usr/bin/env python3
import sys
sys.path.insert(0, r'C:\Users\USER\Desktop\vibeship-spark-intelligence')

from tracer_dashboard import get_tracer_components, poll_once

# Get fresh components
collector, state, store = get_tracer_components()

# Clear processed IDs to force fresh parse
collector._processed_ids.clear()
state._traces.clear()

print(f"Processed IDs count: {len(collector._processed_ids)}")
print(f"Traces in state: {len(state._traces)}")
print()

# Poll once
poll_once()

print(f"After poll - Processed IDs: {len(collector._processed_ids)}")
print(f"After poll - Traces: {len(state._traces)}")
print()

# Check some traces
for trace_id, trace in list(state._traces.items())[:5]:
    print(f"Trace {trace_id[:20]}...")
    print(f"  intent: {trace.intent[:50]}...")
    print(f"  category: {trace.intent_category}")
    print(f"  source: {trace.events[0].source.value if trace.events else 'N/A'}")
    print()
