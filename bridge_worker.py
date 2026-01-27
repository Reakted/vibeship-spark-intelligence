#!/usr/bin/env python3
"""bridge_worker — keep SPARK_CONTEXT.md fresh

This is the practical mechanism that makes Spark affect behavior in Clawdbot.
Clawdbot's spark-context hook injects SPARK_CONTEXT.md; this worker keeps it
updated automatically.

Design:
- small TTL loop
- task-aware (infers focus from recent events)
- safe: best-effort, never crashes the host

Usage:
  python3 bridge_worker.py --interval 60

Optional:
  python3 bridge_worker.py --interval 60 --query "current task here"
"""

import argparse
import time

from lib.bridge import update_spark_context
from lib.memory_capture import process_recent_memory_events
from lib.tastebank import parse_like_message, add_item
from lib.queue import read_recent_events, EventType


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60, help="seconds between updates")
    ap.add_argument("--query", default=None, help="optional fixed query to tailor context")
    args = ap.parse_args()

    while True:
        try:
            # 1) Keep active context fresh
            update_spark_context(query=args.query)
        except Exception:
            pass

        try:
            # 2) Lightweight memory capture (portable across environments)
            process_recent_memory_events(limit=60)
        except Exception:
            pass

        try:
            # 3) TasteBank capture (natural language: "I like this post/UI/art: ...")
            events = read_recent_events(40)
            # best-effort: only look at newest few user messages
            for e in reversed(events[-10:]):
                if e.event_type != EventType.USER_PROMPT:
                    continue
                payload = (e.data or {}).get("payload") or {}
                if payload.get("role") != "user":
                    continue
                txt = str(payload.get("text") or "").strip()
                parsed = parse_like_message(txt)
                if parsed:
                    add_item(**parsed)
                    break
        except Exception:
            pass

        time.sleep(max(10, int(args.interval)))


if __name__ == "__main__":
    main()
