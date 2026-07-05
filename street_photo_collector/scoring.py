from __future__ import annotations

import re

from .models import Article


FEATURE_TYPES = {"Photographer Feature", "Interview", "Portfolio or Series"}
EXHIBITION_KEYWORDS = {"exhibition", "gallery", "museum", "solo show", "group show", "exhibition review"}
PHOTOBOOK_KEYWORDS = {"photobook", "photo book", "monograph", "zine", "book launch"}
AWARD_KEYWORDS = {"award", "awards", "winner", "winners", "finalist", "finalists", "shortlist", "contest results", "competition results"}
FEATURE_KEYWORDS = {"interview", "profile", "feature", "portfolio", "series", "project"}
STREET_CONTEXT_KEYWORDS = {
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
}
LOW_QUALITY_PAGE_KEYWORDS = {
    "our whole catalogue",
    "whole catalogue",
    "photography books",
    "all books",
    "store",
    "shop",
    "catalogue",
    "catalog",
    "cart",
    "checkout",
    "collections",
    "products",
    "home",
    "tickets now available",
    "nicer tuesdays",
    "event tickets",
}
NON_PHOTO_SUBJECT_KEYWORDS = {
    "illustration",
    "graphic design",
    "ai image",
    "ai-generated",
    "generative ai",
    "smartphone",
    "software update",
    "firmware",
    "app update",
}
INVALID_NAME_PHRASES = {
    "photography books",
    "our whole catalogue",
    "night juxtaposition",
    "the axe will",
    "magnum book club",
    "nicer tuesdays",
    "july’s nicer tuesdays",
    "street photography",
    "world street",
}


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

        if article.photographer_name == "Unknown":
            score -= 4
        elif is_valid_photographer_name(article.photographer_name):
            score += self.rules.get("named_photographer", 5)
        else:
            score -= 6
        if article.project_name != "Unknown":
            score += self.rules.get("named_project", 5)
        else:
            score -= 3
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

        if is_low_quality_page(article):
            score -= 10
        if article.photographer_name != "Unknown" and not is_valid_photographer_name(article.photographer_name):
            score -= 6
        if not article.published_at:
            score -= 2
        if not _contains_any(text, STREET_CONTEXT_KEYWORDS):
            score -= 6

        if _contains_negative(text, self.negative_keywords.get("gear_or_commerce", [])):
            score += self.rules.get("gear_or_commerce", -8)
        if _contains_negative(text, self.negative_keywords.get("tips_or_beginner", [])):
            score += self.rules.get("tips_or_beginner", -5)
        if _contains_negative(text, self.negative_keywords.get("ai_phone_software", [])):
            score += self.rules.get("ai_phone_software", -5)
        if _contains_any(text, NON_PHOTO_SUBJECT_KEYWORDS):
            score -= 6
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
    article.why = str(type_data.get("selection_reason", "設定したストリート写真収集ルールに一致したため選びました。"))
    article.photography_use = str(type_data.get("photography_use", "記事から観察ポイントを拾い、撮影時の制約や編集方針に置き換える材料になります。"))
    article.photography_use += _keyword_based_use(article.matched_keywords)

    if article.genre == "Silent Stories":
        article.photography_use += " 特に、不在、痕跡、記憶、静かな人の気配に注目すると撮影へ転用しやすいです。"
    elif article.genre == "Urban Landscape":
        article.photography_use += " 公共空間、サイン、幾何学的な構成、人が都市の画面をどう動かすかを見ると応用しやすいです。"
    elif article.genre == "Fine Art Street":
        article.photography_use += " 構図、色、写真の並び、展示文脈によって日常の街の素材が作品になる過程を見ると参考になります。"
    elif article.genre == "Humor or Decisive Moment":
        article.photography_use += " タイミング、身振り、並置、瞬間が読み取れる立ち位置を観察すると撮影に活かせます。"
    return article


def _keyword_based_use(matched_keywords: list[str]) -> str:
    keywords = {keyword.lower() for keyword in matched_keywords}
    notes: list[str] = []
    if matched_keywords:
        notes.append(f" 一致キーワード（{', '.join(matched_keywords)}）を、記事を読むときの観察メモとして使えます。")
    if keywords.intersection({"light and shadow", "geometry", "composition", "color", "signage"}):
        notes.append(" 光と影、幾何学、色、構図、サインなどを撮影時の具体的な制約に置き換えて試せます。")
    if keywords.intersection({"candid", "everyday life", "human presence", "public space"}):
        notes.append(" 劇的な瞬間だけでなく、公共空間での日常的な振る舞いが画面の構造を作る様子を見ると役立ちます。")
    if keywords.intersection({"absence", "trace", "memory", "silent story", "silent stories"}):
        notes.append(" 人が去った後に残る痕跡、不在、記憶、使われた気配を探す視点に転用できます。")
    if keywords.intersection({"decisive moment", "humor", "humour", "gesture", "juxtaposition"}):
        notes.append(" すぐに撮って終わりにせず、タイミング、身振り、並置が揃う位置を探す練習になります。")
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


def is_low_quality_page(article: Article) -> bool:
    title = article.title.lower().strip()
    url_path = re.sub(r"/+", "/", re.sub(r"https?://[^/]+", "", article.url.lower())).strip("/")
    if not url_path:
        return True
    if title in LOW_QUALITY_PAGE_KEYWORDS or any(keyword in title for keyword in LOW_QUALITY_PAGE_KEYWORDS):
        return True
    path_parts = [part for part in url_path.split("/") if part]
    if len(path_parts) == 1 and path_parts[0] in LOW_QUALITY_PAGE_KEYWORDS:
        return True
    if any(part in LOW_QUALITY_PAGE_KEYWORDS for part in path_parts):
        return True
    return False


def is_valid_photographer_name(name: str) -> bool:
    if not name or name == "Unknown":
        return False
    normalized = name.lower().strip()
    if normalized in INVALID_NAME_PHRASES:
        return False
    if any(phrase in normalized for phrase in INVALID_NAME_PHRASES):
        return False
    words = [word for word in re.split(r"\s+|&|and", name) if word]
    if len(words) < 2:
        return False
    capitalized_words = [word for word in words if re.match(r"^[A-ZÀ-ÖØ-Þ]", word)]
    return len(capitalized_words) >= 2
