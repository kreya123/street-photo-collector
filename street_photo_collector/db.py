from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Article


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_urls (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
"""


class SeenDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def is_seen(self, url: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM seen_urls WHERE url = ?", (url,)).fetchone()
        return row is not None

    def mark_seen(self, article: Article) -> None:
        self.conn.execute(
            """
            INSERT INTO seen_urls (url, title, source, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                source = excluded.source,
                last_seen_at = excluded.last_seen_at
            """,
            (article.url, article.title, article.source, article.fetched_at, article.fetched_at),
        )

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SeenDatabase":
        return self

    def __exit__(self, *_args: object) -> None:
        self.commit()
        self.close()
