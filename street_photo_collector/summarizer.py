from __future__ import annotations

from .models import Article


class RuleBasedSummarizer:
    """Small interface that can later be replaced by an AI-backed summarizer."""

    def __init__(self, genre_config: dict[str, object]) -> None:
        self.genres: dict[str, dict[str, object]] = genre_config["genres"]  # type: ignore[assignment]

    def enrich(self, article: Article) -> Article:
        genre_data = self.genres.get(article.genre, {})
        summary_hint = f"概要: {article.summary}" if article.summary else "概要は短いため、タイトルと掲載元から優先判定しています。"
        article.why = str(genre_data.get("why", "撮影テーマに転用できる観察点が含まれています。"))
        article.photography_use = str(genre_data.get("shooting", "構図、距離、時間帯、人物と背景の関係を観察する。"))

        if article.relevance_score >= 14:
            article.why += " スコアが高く、優先ジャンルとの一致も強めです。"
        elif article.relevance_score <= 7:
            article.why += f" {summary_hint}"
        return article
