#!/usr/bin/env python3
"""sparkd - Spark daemon (platform-agnostic ingest)

Minimal HTTP server:
  GET  /health
  GET  /status
  POST /ingest  (SparkEventV1 JSON)

Stores events into the existing Spark queue (events.jsonl) so the rest of Spark
can process them.

This is intentionally dependency-free.
"""

import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import sys
sys.path.insert(0, str(Path(__file__).parent))

from lib.events import SparkEventV1
from lib.queue import quick_capture, EventType, read_recent_events
from lib.cognitive_learner import get_cognitive_learner
from lib.orchestration import (
    get_orchestrator,
    Agent,
    Goal,
    Handoff,
    GoalStatus,
    HandoffType,
    register_agent,
    create_goal,
    record_handoff,
    complete_handoff,
    recommend_next,
    get_orchestration_stats,
)

PORT = 8787
TOKEN = os.environ.get("SPARKD_TOKEN")
MAX_BODY_BYTES = int(os.environ.get("SPARKD_MAX_BODY_BYTES", "262144"))


def _json(handler: BaseHTTPRequestHandler, code: int, payload):
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _text(handler: BaseHTTPRequestHandler, code: int, body: str):
    raw = body.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return _text(self, 200, "ok")
        if path == "/status":
            return _json(self, 200, {
                "ok": True,
                "now": time.time(),
                "port": PORT,
            })
        if path == "/learnings":
            # Return cognitive learnings for skill integration
            try:
                cognitive = get_cognitive_learner()
                learnings = []
                for insight in cognitive.insights.values():
                    learnings.append({
                        "category": insight.category.value,
                        "insight": insight.insight,
                        "reliability": insight.reliability,
                        "times_validated": insight.times_validated,
                        "context": insight.context,
                        "skill": insight.context if "skill" in str(insight.context).lower() else None,
                        "success": insight.reliability >= 0.7,
                    })
                return _json(self, 200, {"ok": True, "learnings": learnings})
            except Exception as e:
                return _json(self, 500, {"ok": False, "error": str(e)[:200]})
        if path == "/errors":
            # Return recent errors for skill matching
            try:
                events = read_recent_events(50)
                errors = []
                for evt in events:
                    if evt.error:
                        errors.append({
                            "tool": evt.tool_name,
                            "error": evt.error[:500] if evt.error else None,
                            "timestamp": evt.timestamp,
                        })
                return _json(self, 200, {"ok": True, "errors": errors})
            except Exception as e:
                return _json(self, 500, {"ok": False, "error": str(e)[:200]})

        # ============= ORCHESTRATION ENDPOINTS =============
        if path == "/agents":
            # List all registered agents
            try:
                orch = get_orchestrator()
                agents = [
                    {
                        "agent_id": a.agent_id,
                        "name": a.name,
                        "capabilities": a.capabilities,
                        "specialization": a.specialization,
                        "success_rate": a.success_rate,
                        "total_tasks": a.total_tasks,
                    }
                    for a in orch.agents.values()
                ]
                return _json(self, 200, {"ok": True, "agents": agents})
            except Exception as e:
                return _json(self, 500, {"ok": False, "error": str(e)[:200]})

        if path == "/goals":
            # List active goals
            try:
                orch = get_orchestrator()
                goals = [
                    {
                        "goal_id": g.goal_id,
                        "title": g.title,
                        "level": g.level,
                        "status": g.status.value,
                        "parent_goal_id": g.parent_goal_id,
                        "assigned_agents": g.assigned_agents,
                    }
                    for g in orch.get_active_goals()
                ]
                return _json(self, 200, {"ok": True, "goals": goals})
            except Exception as e:
                return _json(self, 500, {"ok": False, "error": str(e)[:200]})

        if path == "/orchestration/stats":
            # Get orchestration statistics
            try:
                stats = get_orchestration_stats()
                return _json(self, 200, {"ok": True, **stats})
            except Exception as e:
                return _json(self, 500, {"ok": False, "error": str(e)[:200]})

        if path == "/orchestration/patterns":
            # Get learned team patterns
            try:
                orch = get_orchestrator()
                patterns = [
                    {
                        "pattern_id": p.pattern_id,
                        "sequence": p.sequence,
                        "success_rate": p.success_rate,
                        "times_observed": p.times_observed,
                        "context": p.context,
                    }
                    for p in sorted(orch.patterns.values(), key=lambda x: x.success_rate, reverse=True)
                ]
                return _json(self, 200, {"ok": True, "patterns": patterns})
            except Exception as e:
                return _json(self, 500, {"ok": False, "error": str(e)[:200]})

        return _text(self, 404, "not found")

    def do_POST(self):
        path = urlparse(self.path).path

        # ============= ORCHESTRATION POST ENDPOINTS =============
        if path == "/agent":
            # Register a new agent
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                success = register_agent(
                    agent_id=data.get("agent_id", data.get("name", "").lower().replace(" ", "-")),
                    name=data.get("name", "Unknown Agent"),
                    capabilities=data.get("capabilities", []),
                    specialization=data.get("specialization", "general"),
                )
                return _json(self, 201 if success else 400, {"ok": success})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/goal":
            # Create a new goal
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                goal_id = create_goal(
                    title=data.get("title", "Untitled Goal"),
                    description=data.get("description", ""),
                    level=data.get("level", "task"),
                    parent_goal_id=data.get("parent_goal_id"),
                )
                return _json(self, 201, {"ok": True, "goal_id": goal_id})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/goal/status":
            # Update goal status
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                orch = get_orchestrator()
                success = orch.update_goal_status(
                    goal_id=data.get("goal_id"),
                    status=GoalStatus(data.get("status", "pending")),
                    learning=data.get("learning"),
                )
                return _json(self, 200 if success else 404, {"ok": success})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/handoff":
            # Record a handoff between agents
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                handoff_id = record_handoff(
                    from_agent=data.get("from_agent"),
                    to_agent=data.get("to_agent"),
                    context=data.get("context", {}),
                    handoff_type=data.get("handoff_type", "sequential"),
                    goal_id=data.get("goal_id"),
                )
                return _json(self, 201, {"ok": True, "handoff_id": handoff_id})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/handoff/complete":
            # Complete a handoff with outcome
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                success = complete_handoff(
                    handoff_id=data.get("handoff_id"),
                    success=data.get("success", False),
                    notes=data.get("notes", ""),
                )
                return _json(self, 200 if success else 404, {"ok": success})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/orchestration/recommend":
            # Get recommendation for next agent
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                next_agent, reasoning = recommend_next(
                    current_agent=data.get("current_agent", ""),
                    task_type=data.get("task_type", ""),
                )
                return _json(self, 200, {
                    "ok": True,
                    "recommended_agent": next_agent,
                    "reasoning": reasoning,
                })
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/orchestration/team-effectiveness":
            # Get team effectiveness metrics
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                orch = get_orchestrator()
                metrics = orch.get_team_effectiveness(data.get("agent_ids", []))
                return _json(self, 200, {"ok": True, **metrics})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path != "/ingest":
            return _text(self, 404, "not found")

        # Optional auth: if SPARKD_TOKEN is set, require Authorization: Bearer <token>
        if TOKEN:
            auth = self.headers.get("Authorization") or ""
            expected = f"Bearer {TOKEN}"
            if auth.strip() != expected:
                return _json(self, 401, {"ok": False, "error": "unauthorized"})

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY_BYTES:
            return _json(self, 413, {"ok": False, "error": "payload_too_large"})
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8") or "{}")
            evt = SparkEventV1.from_dict(data)
        except Exception as e:
            return _json(self, 400, {"ok": False, "error": "invalid_event", "detail": str(e)[:200]})

        # Store as a Spark queue event (POST_TOOL/USER_PROMPT mapping is adapter-defined)
        # Here we just record it as a generic USER_PROMPT or POST_TOOL depending on kind.
        if evt.kind.value == "message":
            et = EventType.USER_PROMPT
        elif evt.kind.value == "tool":
            et = EventType.POST_TOOL
        else:
            et = EventType.LEARNING

        # Try to propagate working-directory hints for project inference.
        meta = (evt.payload or {}).get("meta") or {}
        cwd_hint = meta.get("cwd") or meta.get("workdir") or meta.get("workspace")

        ok = quick_capture(
            event_type=et,
            session_id=evt.session_id,
            data={
                "source": evt.source,
                "kind": evt.kind.value,
                "payload": evt.payload,
                "trace_id": evt.trace_id,
                "v": evt.v,
                "ts": evt.ts,
                "cwd": cwd_hint,
            },
            tool_name=evt.payload.get("tool_name"),
            tool_input=evt.payload.get("tool_input"),
            error=evt.payload.get("error"),
        )

        return _json(self, 200, {"ok": bool(ok)})


def main():
    print(f"sparkd listening on http://127.0.0.1:{PORT}")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
