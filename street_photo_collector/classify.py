from __future__ import annotations

import re

from .models import Article
from .text import clean_text


NAME_STOPWORDS = {
    "Street Photography",
    "LensCulture Street",
    "World Street",
    "Paris Photo",
    "Photo London",
    "British Journal",
    "The Independent",
    "Street Photo",
    "Street Photography Awards",
    "New York",
    "Los Angeles",
    "United States",
    "United Kingdom",
}


class ArticleClassifier:
    def __init__(self, genre_config: dict[str, object], article_type_config: dict[str, object]) -> None:
        self.genre_config = genre_config
        self.article_type_config = article_type_config
        self.genres: dict[str, dict[str, object]] = genre_config["genres"]  # type: ignore[assignment]
        self.genre_priority: list[str] = list(genre_config.get("priority_order", self.genres.keys()))  # type: ignore[arg-type]
        self.article_types: dict[str, dict[str, object]] = article_type_config["types"]  # type: ignore[assignment]
        self.article_type_priority: list[str] = list(article_type_config.get("priority_order", self.article_types.keys()))  # type: ignore[arg-type]

    def classify(self, article: Article) -> Article:
        text = _article_text(article)
        matched_keywords: list[str] = []

        article.article_type, type_keywords = self._detect_article_type(text)
        matched_keywords.extend(type_keywords)

        article.genre, genre_scores, genre_keywords = self._detect_genre(text)
        article.genre_scores = genre_scores
        matched_keywords.extend(genre_keywords)

        article.photographer_name = self._detect_photographer_name(article)
        article.project_name = self._detect_project_name(article)

        for keyword in self.article_type_config.get("street_visual_keywords", []):  # type: ignore[union-attr]
            keyword_text = str(keyword)
            if _contains_keyword(text, keyword_text):
                matched_keywords.append(keyword_text)

        for keywords in dict(self.article_type_config.get("negative_keywords", {})).values():
            for keyword in keywords:
                keyword_text = str(keyword)
                if _contains_keyword(text, keyword_text):
                    matched_keywords.append(keyword_text)

        article.matched_keywords = sorted(set(matched_keywords), key=str.lower)
        return article

    def _detect_article_type(self, text: str) -> tuple[str, list[str]]:
        scores: dict[str, int] = {}
        matches_by_type: dict[str, list[str]] = {}
        title_text = text.split("\n", 1)[0]
        for type_name, type_data in self.article_types.items():
            matches = []
            for keyword in type_data.get("keywords", []):  # type: ignore[union-attr]
                keyword_text = str(keyword)
                if _contains_keyword(title_text, keyword_text):
                    scores[type_name] = scores.get(type_name, 0) + 3
                    matches.append(keyword_text)
                elif _contains_keyword(text, keyword_text):
                    scores[type_name] = scores.get(type_name, 0) + 1
                    matches.append(keyword_text)
            matches_by_type[type_name] = matches
            scores[type_name] = scores.get(type_name, 0)

        if max(scores.values() or [0]) == 0:
            return "Other", []

        def rank(type_name: str) -> tuple[int, int]:
            priority = self.article_type_priority.index(type_name) if type_name in self.article_type_priority else len(self.article_type_priority)
            return scores[type_name], -priority

        best_type = max(scores, key=rank)
        return best_type, matches_by_type[best_type]

    def _detect_genre(self, text: str) -> tuple[str, dict[str, float], list[str]]:
        genre_scores: dict[str, float] = {}
        matched: list[str] = []
        for genre_name, genre_data in self.genres.items():
            score = self._genre_priority_bias(genre_name)
            for keyword, weight in dict(genre_data.get("keywords", {})).items():  # type: ignore[union-attr]
                if _contains_keyword(text, str(keyword)):
                    score += float(weight)
                    matched.append(str(keyword))
            genre_scores[genre_name] = round(score, 3)
        best_genre = max(genre_scores, key=genre_scores.get)
        return best_genre, genre_scores, matched

    def _genre_priority_bias(self, genre_name: str) -> float:
        if genre_name not in self.genre_priority:
            return 0.0
        rank = self.genre_priority.index(genre_name)
        return max(len(self.genre_priority) - rank, 0) * 0.3

    def _detect_photographer_name(self, article: Article) -> str:
        title = article.title
        dash_name = _split_dash_title(title)[0]
        if dash_name:
            name = _clean_name(dash_name)
            if name:
                return name
        patterns = [
            r":\s+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s+(?:on|On)\b",
            r"^([A-Z][A-Za-z'’.-]+(?:\s+(?:&|and)?\s*[A-Z][A-Za-z'’.-]+){1,6})\s+[–-]\s+",
            r"\bwith\s+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})",
            r"\bby\s+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})",
            r"\binterview[:\s]+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})",
            r"\bprofile[:\s]+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})",
        ]
        for pattern in patterns:
            match = re.search(pattern, title, flags=re.IGNORECASE)
            if match:
                name = _clean_name(match.group(1))
                if name:
                    return name

        candidates = re.findall(r"\b([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,2})\b", title)
        for candidate in reversed(candidates):
            name = _clean_name(candidate)
            if name and name not in NAME_STOPWORDS:
                return name
        return "Unknown"

    def _detect_project_name(self, article: Article) -> str:
        title = article.title
        quoted = re.search(r"[\"“']([^\"”']{3,80})[\"”']", title)
        if quoted:
            return clean_text(quoted.group(1), 120)

        on_match = re.search(r":\s+[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3}\s+(?:on|On)\s+(.{3,80})$", title)
        if on_match and not _looks_like_generic_label(on_match.group(1)):
            return _clean_project_name(on_match.group(1))

        dash_project = _split_dash_title(title)[1]
        if dash_project and not _looks_like_generic_label(dash_project):
            return _clean_project_name(dash_project)

        if ":" in title:
            before, after = [part.strip() for part in title.split(":", 1)]
            candidate = after if len(after) <= 80 else before
            if candidate and not _looks_like_generic_label(candidate):
                return _clean_project_name(candidate)

        return "Unknown"


def _article_text(article: Article) -> str:
    return f"{article.title}\n{article.summary}\n{article.url}".lower()


def _contains_keyword(text: str, keyword: str) -> bool:
    lowered = keyword.lower()
    if re.search(r"[^a-z0-9 ]", lowered) or " " in lowered:
        return lowered in text
    return re.search(rf"\b{re.escape(lowered)}\b", text) is not None


def _clean_name(value: str) -> str:
    name = clean_text(value, 80).strip(" -:|")
    name = re.sub(r"^(by|with)\s+", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\b(published|updated|news|opinion|feature|interview)\b.*$", "", name, flags=re.IGNORECASE).strip()
    if not name or name in NAME_STOPWORDS or len(name.split()) < 2:
        return ""
    return name


def _clean_project_name(value: str) -> str:
    project = clean_text(value, 120).strip(" -:|")
    project = re.sub(r"\s+\bby\s+[A-Z][^\d,;:|]{2,80}$", "", project, flags=re.IGNORECASE).strip()
    return project or "Unknown"


def _split_dash_title(title: str) -> tuple[str, str]:
    for separator in (" – ", " - "):
        if separator in title:
            before, after = title.split(separator, 1)
            return before.strip(), after.strip()
    return "", ""


def _looks_like_generic_label(value: str) -> bool:
    lowered = value.lower()
    generic = [
        "street photography",
        "photography",
        "award",
        "awards",
        "news",
        "events",
        "magazine",
        "home",
        "best camera",
        "best lens",
        "camera review",
        "lens review",
        "gear",
        "specs",
        "settings",
        "how to",
        "tips",
        "beginner",
    ]
    return any(item == lowered or lowered.startswith(item + " ") for item in generic)
