# Decision Trace HUD (CLI)

A terminal dashboard that proves Spark is doing real intelligence work:
**Intent → Action → Evidence → Outcome → Lesson** in one visible stream.

## Purpose

Without this, you can't tell if Spark is genuinely learning vs just generating activity. This is your **observability layer for intelligence loops**.

## Quick Start

```bash
# Start the interactive HUD
python trace_hud/trace_hud.py

# Single snapshot and exit
python trace_hud/trace_hud.py --snapshot

# Replay last hour of traces
python trace_hud/trace_hud.py --replay --since-hours 1

# Export to JSON
python trace_hud/trace_hud.py --export trace_dump.json
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION TRACE HUD                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ trace_collector │───▶│ trace_state     │───▶│ trace_tui   │ │
│  │                 │    │                 │    │             │ │
│  │ Normalizes      │    │ State machine   │    │ Rich        │ │
│  │ events from     │    │ per trace       │    │ terminal UI │ │
│  │ multiple sources│    │                 │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           │                    │                          ▲    │
│           ▼                    ▼                          │    │
│  ┌─────────────────┐    ┌─────────────────┐               │    │
│  │ Spark sources:  │    │ trace_store     │───────────────┘    │
│  │ • Queue events  │    │                 │                    │
│  │ • Advisory      │    │ Persistent      │                    │
│  │ • Feedback      │    │ append-only log │                    │
│  │ • Patterns      │    │ with replay     │                    │
│  │ • Insights      │    │                 │                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### trace_collector.py
Normalizes events from multiple Spark sources into a common schema:
- OpenClaw/session events (user prompts, tool calls, results)
- Spark advisory events
- Agent feedback reports
- Bridge heartbeat/status snapshots

**Output:** `TraceEvent` objects with standardized fields:
- `trace_id`, `event_id`, `timestamp`
- `intent`, `action`, `evidence`
- `status`, `outcome`, `lesson`

### trace_state.py
Maintains in-memory state machine per task:
- Current phase (intent → action → evidence → outcome → lesson)
- Status transitions
- Blockers and deferrals
- Success/failure history for KPIs

**Key classes:**
- `ActiveTrace` - Represents one decision trace
- `TraceState` - Manages all traces and computes KPIs
- `TracePhase` - Lifecycle phases (IDLE → INTENT → ACTION → EXECUTING → EVIDENCE → OUTCOME → LESSON → COMPLETE)

### trace_store.py
Persistent append-only storage with replay:
- Append-only JSONL log
- Automatic rotation and compression
- Query and filter capabilities
- Replay from any point in time

**Location:** `~/.spark/trace_hud/trace_store.jsonl`

### trace_tui.py
Rich terminal dashboard rendering:
- Top bar KPIs
- Active traces table
- Recent history
- Real-time updates

### trace_hud.py
Main orchestrator coordinating all components.

## Display

### Top Bar KPIs
```
┌ Active: 5 (recent: 3) │ Success: 87% │ Blocked: 1 │ Advice Acted: 67% │ Lessons: 42 ┐
└─ Phases: intent:2 action:1 executing:1 outcome:1 blocked:1 ┘
```

### Active Traces Table
```
┌──────────┬──────────┬─────────────────────────┬────────────────────┬───────────────┬────────────────────┐
│  Phase   │  Status  │         Intent          │       Action       │    Outcome    │       Lesson       │
├──────────┼──────────┼─────────────────────────┼────────────────────┼───────────────┼────────────────────┤
│ intent   │ pending  │ Fix authentication bug… │ —                  │ —             │ —                  │
│ executing│ running  │ Refactor DB pool        │ Edit src/db.py     │ —             │ —                  │
│ outcome  │ success  │ Add unit tests          │ Run pytest         │ ✓ 12 passed   │ Mock external APIs │
│ blocked  │ blocked  │ Deploy to production    │ —                  │ Needs approval│ —                  │
└──────────┴──────────┴─────────────────────────┴────────────────────┴───────────────┴────────────────────┘
```

### Recent History
```
┌────────┬────────────────────────────────┬────────────┬──────────┐
│  Time  │             Intent             │   Result   │ Duration │
├────────┼────────────────────────────────┼────────────┼──────────┤
│ 2m ago │ Fix authentication bug         │ ✓ success  │ 45s      │
│ 5m ago │ Refactor database connection   │ ✓ success  │ 120s     │
│ 8m ago │ Add error handling             │ ✗ fail     │ 30s      │
└────────┴────────────────────────────────┴────────────┴──────────┘
```

## Keyboard Shortcuts (Interactive Mode)

| Key | Action |
|-----|--------|
| `q` / Ctrl+C | Quit |
| `r` | Force refresh |
| `p` | Pause/unpause updates |
| `s` | Save snapshot |
| `h` | Show help |

## Configuration

Environment variables:
```bash
SPARK_DIR=/path/to/.spark      # Spark data directory
TRACE_HUD_REFRESH=1.0          # Refresh rate in seconds
```

## Data Storage

All data stored locally in `~/.spark/trace_hud/`:
- `trace_store.jsonl` - Current events
- `archive/trace_store_YYYYMMDD_HHMMSS.jsonl.gz` - Rotated archives
- Configurable retention (default: 30 days)

## Testing

```bash
# Run tests
python -m pytest tests/test_trace_hud.py -v

# Run individual component demos
python trace_hud/trace_collector.py  # Demo collector
python trace_hud/trace_state.py      # Demo state machine
python trace_hud/trace_store.py      # Demo store
python trace_hud/trace_tui.py        # Demo TUI (static)
```

## API Usage

```python
from trace_hud import DecisionTraceHUD, TraceState, TraceCollector

# Create HUD
hud = DecisionTraceHUD(refresh_rate=1.0)

# Get snapshot
snapshot = hud.snapshot()
print(f"Active tasks: {snapshot['kpis']['active_tasks']}")

# Start interactive mode
hud.start()

# Or use components directly
collector = TraceCollector()
events = collector.poll_all_sources()

state = TraceState()
state.ingest_events(events)

for trace in state.get_active_traces():
    print(f"{trace.trace_id}: {trace.intent} → {trace.status.value}")
```

## Why This Matters

| Without HUD | With HUD |
|-------------|----------|
| "Is Spark learning?" | "Spark learned 5 lessons in the last hour" |
| "Why did that fail?" | "Blocked: missing test fixtures" |
| "Is advice helping?" | "67% of advice is acted upon" |
| "What just happened?" | Full trace: intent → action → evidence → outcome → lesson |

## Troubleshooting

**No events showing:**
- Check Spark is running: `spark status`
- Verify queue has events: `ls ~/.spark/queue/events.jsonl`
- Check permissions on `~/.spark/`

**Slow updates:**
- Increase refresh rate: `--refresh-rate 2.0`
- Reduce max rows in config

**Store growing too large:**
- Run compaction: `python trace_hud/trace_hud.py --compact`
- Adjust retention: modify `max_age_days` in code
