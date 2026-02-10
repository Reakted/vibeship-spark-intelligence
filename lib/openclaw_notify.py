"""OpenClaw notification bridge: push Spark findings into the agent session."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from .diagnostics import log_debug


def _read_openclaw_config() -> dict:
    """Read OpenClaw config from ~/.openclaw/openclaw.json."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_gateway_url() -> str:
    cfg = _read_openclaw_config()
    port = cfg.get("gateway", {}).get("port", 18789)
    return f"http://127.0.0.1:{port}"


def _get_gateway_token() -> Optional[str]:
    cfg = _read_openclaw_config()
    return cfg.get("gateway", {}).get("auth", {}).get("token")


def _workspace_path() -> Path:
    explicit = os.environ.get("SPARK_OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".openclaw" / "workspace"


def notify_agent(message: str, priority: str = "normal") -> bool:
    """Write a notification file and update SPARK_NOTIFICATIONS.md.

    This is the passive channel — files are visible even without wake events.
    Returns True if notification was written successfully.
    """
    try:
        # Write individual notification file
        notif_dir = _workspace_path() / "spark_notifications"
        notif_dir.mkdir(parents=True, exist_ok=True)

        ts = time.time()
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        filename = f"notif_{int(ts * 1000)}.json"

        payload = {
            "timestamp": ts_str,
            "epoch": ts,
            "message": message,
            "priority": priority,
            "source": "spark_bridge",
        }
        (notif_dir / filename).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

        # Update SPARK_NOTIFICATIONS.md (keep last 5)
        _update_notifications_md(ts_str, message)

        # Cleanup old notification files (keep last 20)
        _cleanup_notification_files(notif_dir, keep=20)

        return True
    except Exception as e:
        log_debug("openclaw_notify", "notify_agent failed", e)
        return False


def _update_notifications_md(ts_str: str, message: str) -> None:
    """Append to SPARK_NOTIFICATIONS.md, keeping only last 5 entries."""
    md_path = _workspace_path() / "SPARK_NOTIFICATIONS.md"
    header = "# Spark Notifications\n\nLatest findings pushed by Spark Intelligence.\n\n"

    entries: list[str] = []
    if md_path.exists():
        try:
            content = md_path.read_text(encoding="utf-8")
            # Parse existing entries (lines starting with "- **")
            for line in content.splitlines():
                if line.startswith("- **"):
                    entries.append(line)
        except Exception:
            pass

    entries.append(f"- **{ts_str}** — {message}")
    entries = entries[-5:]  # keep last 5

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        header + "\n".join(entries) + "\n", encoding="utf-8"
    )


def _cleanup_notification_files(notif_dir: Path, keep: int = 20) -> None:
    """Remove old notification JSON files, keeping the most recent ones."""
    try:
        files = sorted(notif_dir.glob("notif_*.json"))
        for f in files[:-keep]:
            f.unlink(missing_ok=True)
    except Exception:
        pass


def wake_agent(text: str) -> bool:
    """Call OpenClaw's cron wake API to inject a message into the agent session.

    POST /api/cron/wake with Bearer token auth.
    Returns True if the wake call succeeded.
    """
    token = _get_gateway_token()
    if not token:
        log_debug("openclaw_notify", "no gateway token found, skipping wake", None)
        return False

    url = f"{_get_gateway_url()}/api/cron/wake"

    try:
        import urllib.request
        import urllib.error

        body = json.dumps({"text": text, "mode": "now"}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        log_debug("openclaw_notify", f"wake_agent failed: {e}", None)
        return False
