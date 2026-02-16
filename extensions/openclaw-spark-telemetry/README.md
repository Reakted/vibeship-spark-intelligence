# Spark Telemetry Hooks Plugin

This OpenClaw plugin captures `llm_input` and `llm_output` lifecycle hooks and writes
redacted telemetry to a local JSONL spool file consumed by `adapters/openclaw_tailer.py`.

## Config

OpenClaw `openclaw.json` snippet:

```json
{
  "plugins": {
    "load": {
      "paths": [
        "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence\\extensions\\openclaw-spark-telemetry"
      ]
    },
    "entries": {
      "spark-telemetry-hooks": {
        "enabled": true,
        "config": {
          "spoolFile": "C:\\Users\\USER\\.spark\\openclaw_hook_events.jsonl",
          "includePromptPreview": false,
          "includeOutputPreview": false,
          "previewChars": 240
        }
      }
    }
  }
}
```

## Runtime contract

- Hook rows are written to JSONL with `hook` = `llm_input` or `llm_output`.
- Prompt/output previews are off by default.
- `adapters/openclaw_tailer.py` ingests the spool with `--hook-events-file`.
