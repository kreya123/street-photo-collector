from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class Article:
    title: str
    url: str
    source: str
    published_at: str = ""
    summary: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    genre: str = ""
    genre_scores: dict[str, float] = field(default_factory=dict)
    article_type: str = "Other"
    photographer_name: str = "Unknown"
    project_name: str = "Unknown"
    matched_keywords: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    why: str = ""
    photography_use: str = ""
