#!/usr/bin/env python3
"""Mind Lite+ (minimal) server for Spark

This is a lightweight, dependency-free implementation of the Mind API expected by
Spark's MindBridge.

Endpoints:
  GET  /health
  POST /v1/memories/          (create memory)
  POST /v1/memories/retrieve  (simple keyword retrieval)

Storage:
  SQLite at ~/.spark/mind_lite.sqlite

Note: Retrieval is intentionally simple (keyword scoring) to keep this
server zero-dependency. We can upgrade to embeddings later.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

PORT = 8080
DB_PATH = Path.home() / ".spark" / "mind_lite.sqlite"
TOKEN = os.environ.get("MIND_TOKEN")
MAX_BODY_BYTES = int(os.environ.get("MIND_MAX_BODY_BYTES", "262144"))
MAX_CONTENT_CHARS = int(os.environ.get("MIND_MAX_CONTENT_CHARS", "4000"))
MAX_QUERY_CHARS = int(os.environ.get("MIND_MAX_QUERY_CHARS", "1000"))


def _ensure_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
          memory_id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          content TEXT NOT NULL,
          content_type TEXT,
          temporal_level INTEGER,
          salience REAL,
          created_at TEXT NOT NULL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);")
    conn.commit()


def _tokenize(q: str):
    return [t for t in (q or "").lower().replace("\n", " ").split() if t]


def _score(content: str, tokens):
    if not tokens:
        return 0
    c = (content or "").lower()
    return sum(c.count(t) for t in tokens)


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _text(self, code: int, body: str):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        # quiet
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._text(200, "ok")
        return self._text(404, "not found")

    def do_POST(self):
        path = urlparse(self.path).path

        # Optional auth: if MIND_TOKEN is set, require Authorization: Bearer <token>
        if TOKEN:
            auth = (self.headers.get("Authorization") or "").strip()
            if auth != f"Bearer {TOKEN}":
                return self._json(401, {"error": "unauthorized"})

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY_BYTES:
            return self._json(413, {"error": "payload_too_large"})
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            return self._json(400, {"error": "invalid_json"})

        if path == "/v1/memories/":
            return self._create_memory(data)
        if path == "/v1/memories/retrieve":
            return self._retrieve(data)

        return self._text(404, "not found")

    def _db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _ensure_db(conn)
        return conn

    def _create_memory(self, data):
        user_id = data.get("user_id")
        content = data.get("content")
        if not user_id or not content:
            return self._json(400, {"error": "missing_user_id_or_content"})
        if len(str(content)) > MAX_CONTENT_CHARS:
            return self._json(413, {"error": "content_too_large"})

        memory_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + "Z"

        content_type = data.get("content_type")
        temporal_level = data.get("temporal_level")
        salience = data.get("salience")

        conn = self._db()
        try:
            conn.execute(
                "INSERT INTO memories (memory_id, user_id, content, content_type, temporal_level, salience, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (memory_id, user_id, content, content_type, temporal_level, salience, created_at),
            )
            conn.commit()
        finally:
            conn.close()

        return self._json(201, {"memory_id": memory_id})

    def _retrieve(self, data):
        user_id = data.get("user_id")
        query = data.get("query", "")
        limit = int(data.get("limit") or 5)
        limit = max(1, min(limit, 50))

        if not user_id:
            return self._json(400, {"error": "missing_user_id"})

        query = str(query)[:MAX_QUERY_CHARS]
        tokens = _tokenize(query)

        conn = self._db()
        try:
            rows = conn.execute(
                "SELECT memory_id, user_id, content, content_type, temporal_level, salience, created_at FROM memories WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

        scored = []
        for r in rows:
            s = _score(r["content"], tokens)
            if tokens and s == 0:
                continue
            # small boost for salience
            sal = r["salience"] if r["salience"] is not None else 0.5
            scored.append((s + (sal * 0.1), r))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [
            {
                "memory_id": r["memory_id"],
                "content": r["content"],
                "content_type": r["content_type"],
                "temporal_level": r["temporal_level"],
                "salience": r["salience"],
                "created_at": r["created_at"],
                "score": float(score),
            }
            for score, r in scored[:limit]
        ]

        return self._json(200, {"memories": top})


def main():
    print(f"Mind Lite+ listening on http://127.0.0.1:{PORT}")
    print(f"DB: {DB_PATH}")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
