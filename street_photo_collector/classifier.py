from __future__ import annotations

import re
from datetime import date, datetime

from .models import Article


WORD_CACHE: dict[str, re.Pattern[str]] = {}


class GenreClassifier:
    def __init__(self, genre_config: dict[str, object]) -> None:
        self.config = genre_config
        self.genres: dict[str, dict[str, object]] = genre_config["genres"]  # type: ignore[assignment]
        self.priority_order: list[str] = list(genre_config.get("priority_order", self.genres.keys()))  # type: ignore[arg-type]
        self.generic_keywords: dict[str, float] = {
            str(key): float(value)
            for key, value in dict(genre_config.get("generic_positive_keywords", {})).items()
        }

    def classify(self, article: Article, source_score: float = 0.0) -> Article:
        text = f"{article.title}\n{article.summary}\n{article.url}".lower()
        genre_scores: dict[str, float] = {}

        for genre_name, genre_data in self.genres.items():
            keywords = dict(genre_data.get("keywords", {}))  # type: ignore[union-attr]
            score = self._priority_bias(genre_name)
            for keyword, weight in keywords.items():
                count = _keyword_count(text, str(keyword).lower())
                if count:
                    title_multiplier = 1.8 if str(keyword).lower() in article.title.lower() else 1.0
                    score += count * float(weight) * title_multiplier
            genre_scores[genre_name] = round(score, 3)

        best_genre = max(genre_scores, key=genre_scores.get)
        generic_score = sum(_keyword_count(text, keyword.lower()) * weight for keyword, weight in self.generic_keywords.items())
        recency_score = _recency_score(article.published_at)

        article.genre = best_genre
        article.genre_scores = genre_scores
        article.relevance_score = round(genre_scores[best_genre] + generic_score + source_score + recency_score, 3)
        return article

    def _priority_bias(self, genre_name: str) -> float:
        if genre_name not in self.priority_order:
            return 0.0
        rank = self.priority_order.index(genre_name)
        return max(len(self.priority_order) - rank, 0) * 0.75


def _keyword_count(text: str, keyword: str) -> int:
    if " " in keyword or "/" in keyword:
        return text.count(keyword)
    pattern = WORD_CACHE.get(keyword)
    if not pattern:
        pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        WORD_CACHE[keyword] = pattern
    return len(pattern.findall(text))


def _recency_score(value: str) -> float:
    if not value:
        return 0.0
    try:
        published = datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return 0.0
    days = (date.today() - published).days
    if days < 0:
        return 0.5
    if days <= 14:
        return 2.0
    if days <= 60:
        return 1.0
    if days <= 180:
        return 0.4
    return 0.0
