"""Explicitly scoped personal facts. This is storage, not authentication."""

import hashlib
import sqlite3
import time
from contextlib import closing
from pathlib import Path


class IdentityMemory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript("""PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS personal_facts(platform TEXT,user_id TEXT,origin_scope TEXT,id TEXT,text TEXT,source TEXT,visibility TEXT,sensitive INTEGER,created REAL,PRIMARY KEY(platform,user_id,origin_scope,id));
CREATE INDEX IF NOT EXISTS facts_identity ON personal_facts(platform,user_id);""")

    def remember(
        self,
        platform,
        user_id,
        origin_scope,
        text,
        *,
        source,
        visibility="private",
        sensitive=False,
    ):
        if not all(
            isinstance(x, str) and x.strip()
            for x in (platform, user_id, origin_scope, text, source)
        ):
            raise ValueError("Identity, scope, text and provenance are required")
        if visibility not in ("private", "shared"):
            raise ValueError("Visibility must be private or shared")
        if sensitive and visibility == "shared":
            raise ValueError("Sensitive facts cannot be shared")
        if len(text) > 4000:
            raise ValueError("A personal fact must be at most 4000 characters")
        ident = hashlib.sha256(text.encode("utf8")).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO personal_facts VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(platform,user_id,origin_scope,id) DO UPDATE SET source=excluded.source,visibility=excluded.visibility,sensitive=excluded.sensitive",
                (
                    platform,
                    user_id,
                    origin_scope,
                    ident,
                    text,
                    source,
                    visibility,
                    int(sensitive),
                    time.time(),
                ),
            )
        return ident

    def recall(self, platform, user_id, scope, limit=20):
        if not all(
            isinstance(x, str) and x.strip() for x in (platform, user_id, scope)
        ):
            raise ValueError("Trusted platform identity and current scope are required")
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,text,source,origin_scope,visibility FROM personal_facts WHERE platform=? AND user_id=? AND (origin_scope=? OR (visibility='shared' AND sensitive=0)) ORDER BY created DESC LIMIT ?",
                    (platform, user_id, scope, min(100, max(1, int(limit)))),
                )
            ]

    def delete_person(self, platform, user_id):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "DELETE FROM personal_facts WHERE platform=? AND user_id=?",
                (platform, user_id),
            )
