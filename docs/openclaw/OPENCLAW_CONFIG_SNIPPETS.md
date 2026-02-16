# OpenClaw Config Snippets

Use these snippets in local `C:\Users\USER\.openclaw\openclaw.json` (not in repo).

## 1) Subagent depth policy

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxConcurrent": 8,
        "maxSpawnDepth": 2,
        "maxChildrenPerAgent": 3
      }
    }
  }
}
```

Notes:

- `maxSpawnDepth: 2` enables orchestrator pattern.
- Keep `maxChildrenPerAgent` conservative to avoid fan-out instability.

## 2) Cron finished-run webhook auth

```json
{
  "cron": {
    "webhook": "https://<your-private-endpoint>/openclaw/cron-finished",
    "webhookToken": "${OPENCLAW_CRON_WEBHOOK_TOKEN}"
  }
}
```

Notes:

- Use a dedicated token.
- Do not reuse gateway auth token.

## 3) Hook telemetry enablement (llm_input / llm_output)

Use plugin-based hook capture + tailer ingestion:

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

Run tailer with hook spool ingestion enabled:

```powershell
python adapters\openclaw_tailer.py --agent main --hook-events-file C:\Users\USER\.spark\openclaw_hook_events.jsonl
```

Join fields emitted by plugin rows:

- `run_id`
- `session_id` / `session_key`
- `agent_id`
- `provider` / `model`
- prompt/output shape and hashes (redacted by default)

## 4) Secret hygiene policy

- Keep secrets in env or secret store, not raw JSON.
- Rotate existing exposed tokens immediately.
- Store only redacted operational artifacts in docs/reports.
