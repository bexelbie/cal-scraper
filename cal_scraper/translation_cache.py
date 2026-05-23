# ABOUTME: SQLite-backed translation cache to avoid re-translating unchanged events.
# ABOUTME: Keyed on SHA-256 hash of (site + title + description) content.

"""Persistent translation cache backed by SQLite.

Stores translated event text keyed by content hash so that unchanged events
are never re-translated on subsequent runs.

Public API:
    TranslationCache(db_path)  — open or create the cache database
    cache.get(site, event)     — returns (title_en, desc_en) or None
    cache.put(site, event, title_en, desc_en) — stores a translation
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cal_scraper.models import Event


def _content_hash(site: str, event: Event) -> str:
    """Compute SHA-256 hash of the translatable content."""
    payload = f"{site}\n{event.title}\n{event.description}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TranslationCache:
    """SQLite-backed cache for event translations."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS translations (
                content_hash TEXT PRIMARY KEY,
                site TEXT NOT NULL,
                title_cs TEXT NOT NULL,
                desc_cs TEXT NOT NULL,
                title_en TEXT NOT NULL,
                desc_en TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, site: str, event: Event) -> tuple[str, str] | None:
        """Look up a cached translation. Returns (title_en, desc_en) or None."""
        h = _content_hash(site, event)
        row = self._conn.execute(
            "SELECT title_en, desc_en FROM translations WHERE content_hash = ?",
            (h,),
        ).fetchone()
        if row is None:
            return None
        return row[0], row[1]

    def put(self, site: str, event: Event, title_en: str, desc_en: str) -> None:
        """Store a translation in the cache."""
        h = _content_hash(site, event)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO translations
                (content_hash, site, title_cs, desc_cs, title_en, desc_en, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (h, site, event.title, event.description, title_en, desc_en, now),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
