from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import Article, SelectionStats
from .scoring import is_low_quality_page, is_valid_photographer_name


GOOD_TYPES = {
    "Photographer Feature",
    "Interview",
    "Portfolio or Series",
    "Exhibition",
    "Photobook",
    "Award or Contest Result",
}


@dataclass(slots=True)
class SelectionResult:
    candidates: list[Article]
    quality_articles: list[Article]
    final_articles: list[Article]
    stats: SelectionStats


def select_articles(
    articles: list[Article],
    candidate_limit: int,
    final_limit: int,
    min_score: float,
    max_per_source_final: int,
    max_per_article_type_final: int,
) -> SelectionResult:
    sorted_articles = sorted(articles, key=lambda item: item.relevance_score, reverse=True)
    candidates = sorted_articles[:candidate_limit]
    quality_articles = [article for article in candidates if passes_quality_filter(article, min_score)]
    final_articles = diversify_articles(
        quality_articles,
        final_limit=final_limit,
        max_per_source=max_per_source_final,
        max_per_article_type=max_per_article_type_final,
    )
    stats = SelectionStats(
        candidate_count=len(candidates),
        quality_pass_count=len(quality_articles),
        final_count=len(final_articles),
        min_score=min_score,
        max_per_source_final=max_per_source_final,
        max_per_article_type_final=max_per_article_type_final,
    )
    return SelectionResult(candidates, quality_articles, final_articles, stats)


def passes_quality_filter(article: Article, min_score: float) -> bool:
    if article.relevance_score < min_score:
        return False
    if article.article_type not in GOOD_TYPES:
        return False
    if is_low_quality_page(article):
        return False
    if not is_valid_photographer_name(article.photographer_name):
        return False
    if article.project_name == "Unknown":
        return False
    if _weak_context(article):
        return False
    return True


def diversify_articles(
    articles: list[Article],
    final_limit: int,
    max_per_source: int,
    max_per_article_type: int,
) -> list[Article]:
    selected: list[Article] = []
    source_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()

    for article in articles:
        if len(selected) >= final_limit:
            break
        if source_counts[article.source] >= max_per_source:
            continue
        if type_counts[article.article_type] >= max_per_article_type:
            continue
        selected.append(article)
        source_counts[article.source] += 1
        type_counts[article.article_type] += 1

    return selected[:final_limit]


def _weak_context(article: Article) -> bool:
    text = f"{article.title} {article.summary} {article.url} {' '.join(article.matched_keywords)}".lower()
    context_terms = (
        "street photography",
        "documentary",
        "photobook",
        "photo book",
        "exhibition",
        "award",
        "photographer",
        "portfolio",
        "series",
        "project",
        "candid",
        "urban",
        "public space",
        "human presence",
        "trace",
        "memory",
        "light and shadow",
        "decisive moment",
        "composition",
        "color",
    )
    return not any(term in text for term in context_terms)
