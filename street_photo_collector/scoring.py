from __future__ import annotations

import re

from .models import Article


FEATURE_TYPES = {"Photographer Feature", "Interview", "Portfolio or Series"}
EXHIBITION_KEYWORDS = {"exhibition", "gallery", "museum", "solo show", "group show", "exhibition review"}
PHOTOBOOK_KEYWORDS = {"photobook", "photo book", "monograph", "zine", "book launch"}
AWARD_KEYWORDS = {"award", "awards", "winner", "winners", "finalist", "finalists", "shortlist", "contest results", "competition results"}
FEATURE_KEYWORDS = {"interview", "profile", "feature", "portfolio", "series", "project"}


class ArticleScorer:
    def __init__(self, article_type_config: dict[str, object]) -> None:
        self.config = article_type_config
        self.rules: dict[str, float] = {
            str(key): float(value)
            for key, value in dict(article_type_config.get("score_rules", {})).items()
        }
        self.negative_keywords: dict[str, list[str]] = {
            str(key): [str(item) for item in value]
            for key, value in dict(article_type_config.get("negative_keywords", {})).items()
        }
        self.street_visual_keywords = [str(item) for item in article_type_config.get("street_visual_keywords", [])]  # type: ignore[arg-type]

    def score(self, article: Article, source_score: float = 0.0) -> Article:
        text = f"{article.title}\n{article.summary}\n{article.url}".lower()
        score = 0.0

        if article.photographer_name != "Unknown":
            score += self.rules.get("named_photographer", 5)
        if article.project_name != "Unknown":
            score += self.rules.get("named_project", 5)
        if article.article_type == "Exhibition" or _contains_any(text, EXHIBITION_KEYWORDS):
            score += self.rules.get("exhibition", 4)
        if article.article_type == "Photobook" or _contains_any(text, PHOTOBOOK_KEYWORDS):
            score += self.rules.get("photobook", 4)
        if article.article_type == "Award or Contest Result" or _contains_any(text, AWARD_KEYWORDS):
            score += self.rules.get("award", 4)
        if article.article_type in FEATURE_TYPES or _contains_any(text, FEATURE_KEYWORDS):
            score += self.rules.get("feature_or_project", 4)
        if _contains_any(text, self.street_visual_keywords):
            score += self.rules.get("street_visual_language", 3)

        if _contains_negative(text, self.negative_keywords.get("gear_or_commerce", [])):
            score += self.rules.get("gear_or_commerce", -8)
        if _contains_negative(text, self.negative_keywords.get("tips_or_beginner", [])):
            score += self.rules.get("tips_or_beginner", -5)
        if _contains_negative(text, self.negative_keywords.get("ai_phone_software", [])):
            score += self.rules.get("ai_phone_software", -5)
        if not self.has_strong_relationship(article):
            score += self.rules.get("weak_title_relationship", -3)

        genre_bonus = max(article.genre_scores.values() or [0.0]) * 0.5
        article.relevance_score = round(score + genre_bonus, 3)
        return article

    @staticmethod
    def has_strong_relationship(article: Article) -> bool:
        title = article.title.lower()
        title_keywords = (
            "profile",
            "feature",
            "interview",
            "portfolio",
            "series",
            "project",
            "exhibition",
            "solo show",
            "group show",
            "gallery",
            "museum",
            "photobook",
            "photo book",
            "monograph",
            "zine",
            "book launch",
            "award",
            "winner",
            "finalist",
            "shortlist",
            "contest results",
        )
        return (
            any(keyword in title for keyword in title_keywords)
            or article.photographer_name != "Unknown"
            or article.project_name != "Unknown"
            or re.search(r"\b[A-Z][A-Za-z'’.-]+\s+[A-Z][A-Za-z'’.-]+\b", article.title) is not None
        )


def explain_selection(article: Article, article_type_config: dict[str, object]) -> Article:
    type_data = dict(article_type_config["types"]).get(article.article_type, {})  # type: ignore[index]
    article.why = str(type_data.get("selection_reason", "This matched the configured street-photography collection rules."))
    article.photography_use = str(type_data.get("photography_use", "Use it to translate observed work into shooting constraints and editing ideas."))
    article.photography_use += _keyword_based_use(article.matched_keywords)

    if article.genre == "Silent Stories":
        article.photography_use += " Pay special attention to absence, trace, memory, and quiet human presence."
    elif article.genre == "Urban Landscape":
        article.photography_use += " Look for public space, signage, geometry, and how people activate the city frame."
    elif article.genre == "Fine Art Street":
        article.photography_use += " Note how composition, color, sequencing, and exhibition context raise ordinary street material into a body of work."
    elif article.genre == "Humor or Decisive Moment":
        article.photography_use += " Study timing, gesture, juxtaposition, and the position where the moment becomes legible."
    return article


def _keyword_based_use(matched_keywords: list[str]) -> str:
    keywords = {keyword.lower() for keyword in matched_keywords}
    notes: list[str] = []
    if matched_keywords:
        notes.append(f" Use the matched keywords ({', '.join(matched_keywords)}) as reading prompts when reviewing the article.")
    if keywords.intersection({"light and shadow", "geometry", "composition", "color", "signage"}):
        notes.append(" Translate the matched visual keywords into a concrete shooting constraint such as light/shadow, geometry, color, composition, or signage.")
    if keywords.intersection({"candid", "everyday life", "human presence", "public space"}):
        notes.append(" Watch how ordinary public-space behavior creates structure before chasing dramatic moments.")
    if keywords.intersection({"absence", "trace", "memory", "silent story", "silent stories"}):
        notes.append(" Look for what remains after people leave: traces, absences, memory, and quiet evidence of use.")
    if keywords.intersection({"decisive moment", "humor", "humour", "gesture", "juxtaposition"}):
        notes.append(" Revisit the frame for timing, gesture, and juxtaposition rather than treating the first shot as final.")
    return "".join(notes)


def _contains_any(text: str, keywords: set[str] | list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _contains_negative(text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        lowered = keyword.lower()
        if lowered == "review":
            if "exhibition review" in text:
                continue
            if any(context in text for context in ("camera review", "lens review", "gear review", "equipment review")):
                return True
            continue
        if lowered in text:
            return True
    return False
