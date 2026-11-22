"""Durable, session-scoped original request frames for long-conversation recovery."""

import hashlib
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path


class ContextArchive:
    """Preserve exact frames independently of summary and history retention."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS frames(scope TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(scope,id))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS entries(scope TEXT NOT NULL, frame TEXT NOT NULL, position INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(scope,frame,position))"
            )
            db.execute("CREATE INDEX IF NOT EXISTS entries_scope ON entries(scope)")

    def save(self, scope, messages):
        """Commit originals atomically before the caller discards any context."""
        if not scope:
            raise ValueError("Archive scope is required")
        body = json.dumps(
            messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        frame = hashlib.sha256(body.encode("utf8")).hexdigest()
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            inserted = db.execute(
                "INSERT OR IGNORE INTO frames VALUES(?,?,?,?)",
                (scope, frame, body, time.time()),
            ).rowcount
            if inserted:
                db.executemany(
                    "INSERT INTO entries VALUES(?,?,?,?)",
                    [
                        (scope, frame, i, json.dumps(m, ensure_ascii=False))
                        for i, m in enumerate(messages)
                    ],
                )
        return frame

    def read(self, scope, frame, start=0, limit=None):
        """Read a frame only within the caller's current platform session."""
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT body FROM frames WHERE scope=? AND id=?", (scope, frame)
            ).fetchone()
        if not row:
            return []
        messages = json.loads(row[0])
        start = max(0, int(start))
        return (
            messages[start:]
            if limit is None
            else messages[start : start + min(20, max(0, int(limit)))]
        )

    def search(self, scope, query, limit=3, max_chars=2400):
        """Find literal cues without accepting SQL wildcards or other scopes."""
        query = str(query).strip()
        if len(query) < 2:
            return []
        pattern = (
            "%"
            + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "SELECT frame,position,body FROM entries WHERE scope=? AND body LIKE ? ESCAPE '\\' ORDER BY rowid DESC LIMIT ?",
                (scope, pattern, min(10, max(1, int(limit)))),
            ).fetchall()
        result = []
        remaining = min(8000, max(0, int(max_chars)))
        for frame, position, body in rows:
            if remaining <= 0:
                break
            preview = body[:remaining]
            result.append(
                {
                    "frame": frame,
                    "position": position,
                    "original": preview,
                    "truncated": len(preview) < len(body),
                }
            )
            remaining -= len(preview)
        return result

    def read_page(self, scope, frame, position=0, offset=0, max_chars=2400):
        """Return one bounded original-message page, with a continuation cursor."""
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT body FROM entries WHERE scope=? AND frame=? AND position=?",
                (scope, frame, max(0, int(position))),
            ).fetchone()
        if not row:
            return {}
        body = row[0]
        offset = max(0, int(offset))
        end = min(len(body), offset + min(8000, max(1, int(max_chars))))
        return {
            "frame": frame,
            "position": position,
            "offset": offset,
            "text": body[offset:end],
            "next_offset": end if end < len(body) else None,
            "total_chars": len(body),
        }

    def delete_scope(self, scope):
        """Remove this archive scope only; derived state is managed separately."""
        if not scope:
            raise ValueError("Archive scope is required")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM entries WHERE scope=?", (scope,))
            db.execute("DELETE FROM frames WHERE scope=?", (scope,))

    def backup(self, destination):
        """Use SQLite online backup, including committed WAL contents."""
        destination = Path(destination)
        if destination.resolve() == self.path.resolve():
            raise ValueError("Backup must use a different path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with (
            closing(sqlite3.connect(self.path)) as source,
            closing(sqlite3.connect(destination)) as target,
        ):
            source.backup(target)
