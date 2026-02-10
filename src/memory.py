"""CleanApp Agent001 — Engagement Memory (SQLite)."""

from __future__ import annotations

import json
import sqlite3
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Memory:
    """SQLite-backed engagement log."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS engagements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                action TEXT NOT NULL,  -- 'post' or 'comment'
                mode TEXT NOT NULL,    -- 'intake', 'analysis', 'distribution'
                our_content TEXT NOT NULL,
                thread_title TEXT,
                thread_submolt TEXT,
                relevance_score REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_counts (
                date TEXT PRIMARY KEY,
                posts_count INTEGER NOT NULL DEFAULT 0,
                comments_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                post_id TEXT NOT NULL,
                title TEXT,
                submolt TEXT,
                author TEXT,
                relevance_score REAL,
                action_taken TEXT,  -- 'engaged', 'skipped', 'queued'
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_engagements_post_id ON engagements(post_id);
            CREATE INDEX IF NOT EXISTS idx_opportunities_mode ON opportunities(mode);
        """)
        self._conn.commit()

    def already_engaged(self, post_id: str) -> bool:
        """Check if we've already engaged with a thread."""
        cur = self._conn.execute(
            "SELECT 1 FROM engagements WHERE post_id = ? LIMIT 1",
            (post_id,),
        )
        return cur.fetchone() is not None

    def content_already_used(self, content: str) -> bool:
        """Check if we've used very similar content before (exact match)."""
        cur = self._conn.execute(
            "SELECT 1 FROM engagements WHERE our_content = ? LIMIT 1",
            (content,),
        )
        return cur.fetchone() is not None

    def get_daily_counts(self, target_date: date | None = None) -> tuple[int, int]:
        """Get (posts, comments) count for a date."""
        d = (target_date or date.today()).isoformat()
        cur = self._conn.execute(
            "SELECT posts_count, comments_count FROM daily_counts WHERE date = ?",
            (d,),
        )
        row = cur.fetchone()
        if row:
            return row["posts_count"], row["comments_count"]
        return 0, 0

    def record_engagement(
        self,
        post_id: str,
        action: str,
        mode: str,
        content: str,
        thread_title: str = "",
        thread_submolt: str = "",
        relevance_score: float = 0.0,
    ):
        """Record an engagement."""
        self._conn.execute(
            """INSERT INTO engagements
               (post_id, action, mode, our_content, thread_title, thread_submolt, relevance_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (post_id, action, mode, content, thread_title, thread_submolt, relevance_score),
        )

        # Update daily counts
        d = date.today().isoformat()
        col = "posts_count" if action == "post" else "comments_count"
        self._conn.execute(
            f"""INSERT INTO daily_counts (date, {col})
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET {col} = {col} + 1""",
            (d,),
        )
        self._conn.commit()

    def record_opportunity(
        self,
        mode: str,
        post_id: str,
        title: str,
        submolt: str,
        author: str,
        relevance_score: float,
        action_taken: str,
        reason: str = "",
    ):
        """Record a discovered opportunity."""
        self._conn.execute(
            """INSERT INTO opportunities
               (mode, post_id, title, submolt, author, relevance_score, action_taken, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (mode, post_id, title, submolt, author, relevance_score, action_taken, reason),
        )
        self._conn.commit()

    def get_recent_engagements(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent engagements."""
        cur = self._conn.execute(
            "SELECT * FROM engagements ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_opportunities_summary(self) -> dict[str, int]:
        """Get opportunity counts by mode."""
        cur = self._conn.execute(
            "SELECT mode, COUNT(*) as count FROM opportunities GROUP BY mode"
        )
        return {row["mode"]: row["count"] for row in cur.fetchall()}

    def close(self):
        """Close the database connection."""
        self._conn.close()
